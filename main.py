import os
import time
import argparse
import utils
from whoosh import index, highlight
from whoosh.fields import Schema, TEXT, ID
from whoosh.qparser import QueryParser
from constants import *


def scrape_and_index_lessons(lesson_uuids, schema):
    # type: (list[str], Schema) -> None
    """
    Scrapes lesson data from the Boot.Dev API and indexes it using the provided
    schema.
    """

    if not index.exists_in('indexdir'):
        ix = index.create_in('indexdir', schema)
    else:
        ix = index.open_dir('indexdir')

    writer = ix.writer()
    len_lessons = len(lesson_uuids)
    dt = []
    tick = time.time()
    for i, lesson_uuid in enumerate(lesson_uuids, start=1):
        api_url = f'{BOOTDEV_API_LESSONS}/{lesson_uuid}'
        _, content = utils.get_lesson_and_content(api_url=api_url)
        if not content:
            print('no content:', api_url, end='\n\n')
            tick = time.time()
            continue

        writer.update_document(uuid=lesson_uuid, url=api_url, content=content)

        # Provide indexing feedback to user
        done = i / len_lessons * 100
        dt.append(time.time() - tick)
        eta = sum(dt)/len(dt) * (len_lessons - i)
        m = eta // 60
        s = (eta / 60 - m) * 60
        print(text.ERASE, end='')
        print(f'Indexing: {done:.1f} % (ETA: {m:.0f} min {s:.0f} sec)', end='')

        tick = time.time()

    writer.commit()
    print('\nDone!')


def index_search(query):
    # type: (str) -> None
    """
    Search the indexed lessons for the requested query and prints the results
    to the console
    """
    # Initialize a searcher
    ix = index.open_dir('indexdir')
    with ix.searcher() as searcher:
        parser = QueryParser('content', ix.schema)
        q = parser.parse(query)

        # Perform the search
        corrected = searcher.correct_query(q, query)
        if corrected.query != q:
            print(f"Could not find results for '{query}'.")
            print(f"Showing results for '{corrected.string}' instead...")
            query = corrected.string
            q = corrected.query

        results = searcher.search(q)
        results.formatter = utils.RedFormatter()
        results.fragmenter = highlight.SentenceFragmenter()
        results.fragmenter.sentencechars = frozenset(['.', '!', '?', '\n'])
        for hit in results:
            # Get content form api
            api_url = hit['url']
            lesson, content = utils.get_lesson_and_content(api_url=api_url)
            if not content:
                print('no content:', api_url, end='\n\n')
                continue

            # Title
            print(text.BOLD, text.GREEN, sep='', end='')
            print(lesson.get('Title', ''))
            print(text.DEFAULT, end='')

            # Link
            print(text.UNDERLINE, text.BLUE, sep='', end='')
            print(f'{BOOTDEV_LESSONS}/{hit["uuid"]}#:~:text={query}')
            print(text.DEFAULT, end='')

            # highlight
            print(hit.highlights('content', text=content), end='\n\n\n')


def parse_args():
    parser = argparse.ArgumentParser(description='Boot.Dev search')

    parser.add_argument(
        'search',
        type=str,
        nargs='?',
        help='a string to search'
    )
    parser.add_argument(
        '--index',
        '-i',
        action='store_true',
        required=False,
        help='scrape and index boot.dev lessons, takes a while'
    )
    args = parser.parse_args()

    if args.search is None and args.index is False:
        parser.error('provide either the --index optional arg or a search')

    return args


if __name__ == '__main__':
    args = parse_args()

    schema = Schema(
        uuid=ID(stored=True),
        url=TEXT(stored=True),
        title=TEXT,
        content=TEXT
    )

    if not os.path.exists('indexdir'):
        os.mkdir('indexdir')
        args.index = True

    if args.index:
        lesson_uuids = utils.get_all_lesson_uuids()
        scrape_and_index_lessons(lesson_uuids=lesson_uuids, schema=schema)

    if args.search:
        index_search(args.search)
