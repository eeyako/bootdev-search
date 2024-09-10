import argparse
import os
import sys
import time
from datetime import datetime

import utils
from constants import BOOTDEV_API_LESSONS, text
from whoosh import highlight, index
from whoosh.fields import ID, TEXT, Schema
from whoosh.qparser import QueryParser


def scrape_and_index_lessons(lang_lessons, schema):
    # type: (list[str], Schema) -> None
    """
    Scrapes lesson data from the Boot.Dev API and indexes it using the provided
    schema.
    """
    for lang in lang_lessons:
        indexdir = os.path.join("indexdir", lang)
        os.makedirs(indexdir, exist_ok=True)

        if not index.exists_in(indexdir):
            ix = index.create_in(indexdir, schema)
        else:
            ix = index.open_dir(indexdir)

        lesson_uuids = lang_lessons[lang]
        writer = ix.writer()
        len_lessons = len(lesson_uuids)
        dt = []
        tick = time.time()
        for i, lesson_uuid in enumerate(lesson_uuids, start=1):
            api_url = f"{BOOTDEV_API_LESSONS}/{lesson_uuid}"
            _, content = utils.get_lesson_and_content(api_url=api_url)
            if not content:
                print("no content:", api_url, end="\n\n")
                tick = time.time()
                continue

            writer.update_document(uuid=lesson_uuid, url=api_url, content=content)

            # Provide indexing feedback to user
            done = i / len_lessons * 100
            dt.append(time.time() - tick)
            eta = sum(dt) / len(dt) * (len_lessons - i)
            m = eta // 60
            s = (eta / 60 - m) * 60
            print(text.ERASE, end="")
            print(
                f"Indexing {lang}: {done:.1f} % (ETA: {m:.0f} min {s:.0f} sec)",
                end="",
                flush=True,
            )

            tick = time.time()

        writer.commit()
        print(f"{text.ERASE}Done indexing {lang}!", flush=True)


def index_search(query, langs):
    # type: (str, str) -> None
    """
    Search the indexed lessons for the requested query and prints the results
    to the console
    """
    # Make sure languages is iterable and not a single string
    langs = [] if not langs else langs
    if not hasattr(langs, "__iter__") or isinstance(langs, str):
        langs = [langs]

    # Get languages via directory name extraction if not provided
    if not langs:
        langs = utils.get_indexed_languages().keys()

    if not langs:
        print("Nothing indexed yet, check --indexed-languages")
        return

    for lang in langs:
        indexdir = os.path.join("indexdir", lang)
        # Skip if language has not been indexed yet
        if not index.exists_in(indexdir):
            print(f'Language "{lang}" has not been indexed yet!')
            continue

        # Initialize a searcher
        ix = index.open_dir(indexdir)
        with ix.searcher() as searcher:
            parser = QueryParser("content", ix.schema)
            q = parser.parse(query)

            # Perform the search
            corrected = searcher.correct_query(q, query)
            results = searcher.search(q)

            # Use query closest match if no results were returned
            if not results:
                if corrected.query != q:
                    print(f"Could not find results for '{query}'.")
                    print(f"Showing results for '{corrected.string}' instead...")
                    results = searcher.search(corrected.query)
                    query = corrected.string

            # Setup results formatting
            results.formatter = utils.RedFormatter()
            results.fragmenter = highlight.SentenceFragmenter()
            results.fragmenter.sentencechars = frozenset([".", "!", "?", "\n"])

            for result in results:
                # Get content form api
                api_url = result["url"]
                lesson, content = utils.get_lesson_and_content(api_url=api_url)
                if not content:
                    print("no content:", api_url, end="\n\n")
                    continue

                utils.pretty_print_result(
                    query=query,
                    language=lang,
                    result=result,
                    lesson=lesson,
                    content=content,
                )


def parse_args():
    parser = argparse.ArgumentParser(description="Boot.Dev search")

    parser.add_argument(
        "--index",
        "-i",
        action="store_true",
        required=False,
        help="scrape and index boot.dev lessons, takes a while",
    )
    parser.add_argument(
        "--indexed-languages",
        "-il",
        action="store_true",
        required=False,
        help="prints the currently indexed languages and their last index date",
    )
    parser.add_argument(
        "--languages",
        "-l",
        required=False,
        default=[],
        type=str,
        nargs="+",
        help="which programming languages to limit the search or indexing to",
    )
    parser.add_argument("search", type=str, nargs="?", help="a string to search")
    args = parser.parse_args()

    if not any([args.search, args.index, args.indexed_languages]):
        parser.error("either --index, --indexed-languages optional args or a search is required")

    return args


if __name__ == "__main__":
    args = parse_args()

    schema = Schema(uuid=ID(stored=True), url=TEXT(stored=True), content=TEXT)

    if args.indexed_languages:
        lang_mtimes = list(utils.get_indexed_languages().items())
        lang_mtimes.sort(key=lambda lang_mtime: lang_mtime[1])
        if lang_mtimes:
            print("Indexed programming languages:")
            for lang, mtime in lang_mtimes:
                index_date = datetime.fromtimestamp(mtime)
                index_date = index_date.strftime("%d/%m/%Y %H:%M:%S")
                print(f"- {lang} (indexed on: {index_date})")
        else:
            print("Nothing has been indexed yet! Check --help")
        sys.exit()

    langs = []
    if args.languages:
        langs = args.languages

    if args.index:
        language_lessons = utils.get_lessons_by_languages(languages=langs)
        if not language_lessons:
            print("Could not find lessons for the languages:\n- ", end="")
            print(*langs, sep="\n- ")
        scrape_and_index_lessons(lang_lessons=language_lessons, schema=schema)

    if args.search:
        index_search(query=args.search, langs=langs)
