import os
import sys
import time
import markdown
import argparse
import requests
from whoosh import index, highlight
from whoosh.fields import Schema, TEXT, ID
from whoosh.qparser import QueryParser
from bs4 import BeautifulSoup
import constants as k


class BracketFormatter(highlight.Formatter):
    """
    Highlights matched terms in red.
    """

    def format_token(self, text, token, replace=False):
        tokentext = highlight.get_text(text, token, replace)
        return f'{k.RED}{k.BOLD}{tokentext}{k.DEFAULT}'


def get_all_lesson_uuids():
    lesson_uuids = set()
    res = requests.get(k.BOOTDEV_API_COURSES)
    courses = res.json()
    for course in courses:
        if course.get('Draft'):
            continue
        for chapter in course.get('Chapters', []):
            lessons = []
            lessons += chapter.get('RequiredLessons', [])
            lessons += chapter.get('OptionalLessons', [])
            for lesson in lessons:
                lesson_uuids.add(lesson.get('UUID'))

    return lesson_uuids


def scrape_and_index_lessons(lesson_uuids, schema):
    # type: (list[str], Schema) -> None

    if not index.exists_in('indexdir'):
        ix = index.create_in('indexdir', schema)
    else:
        ix = index.open_dir('indexdir')

    writer = ix.writer()
    len_lessons = len(lesson_uuids)
    dt = []
    tick = time.time()
    for i, lesson_uuid in enumerate(lesson_uuids, start=1):
        url = f'{k.BOOTDEV_API_LESSONS}/{lesson_uuid}'
        res = requests.get(url)
        lesson = res.json()
        lesson = lesson.get('Lesson')
        if not lesson:
            tick = time.time()
            print('no lesson:', url)
            continue

        data_ls = [lesson.get(k) for k in lesson.keys()
                   if k.startswith('LessonData')]
        content = ''
        data_ls = filter(lambda x: x, data_ls)
        for data in data_ls:
            content += f"{data.get('Readme', '')}\n"
        if not content:
            print('no content:', url, end='\n\n')
            tick = time.time()
            continue

        content = md_to_text(content)
        writer.update_document(uuid=lesson_uuid, url=url, content=content)

        # indexing feedback to user
        done = i / len_lessons * 100
        dt.append(time.time() - tick)
        eta = sum(dt)/len(dt) * (len_lessons - i)
        m = eta // 60
        s = (eta / 60 - m) * 60
        print(k.BACK, end='')
        print(f'Indexing: {done:.1f} % (ETA: {m:.0f} min {s:.0f} sec)', end='')

        tick = time.time()

    writer.commit()
    print('\nDone!')


def index_search(query):
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
        results.formatter = BracketFormatter()
        results.fragmenter = highlight.SentenceFragmenter()
        for hit in results:
            # Get content form api
            res = requests.get(hit['url'])
            res_json = res.json()
            lesson = res_json['Lesson']
            data_ls = [lesson.get(k) for k in lesson.keys()
                       if k.startswith('LessonData')]
            content = ''
            data_ls = filter(lambda x: x, data_ls)
            for data in data_ls:
                content += f"{data.get('Readme', '')}\n"
            content = md_to_text(content)

            # Title
            print(k.BOLD, lesson.get('Title'), sep='')

            # Link
            print(k.UNDERLINE, k.BLUE, sep='', end='')
            print(f'{k.BOOTDEV_LESSONS}/{hit["uuid"]}#:~:text={query}')
            print(k.DEFAULT, end='')

            # highlight
            print(hit.highlights('content', text=content), end='\n\n\n')


def md_to_text(md):
    html = markdown.markdown(md)
    return BeautifulSoup(html, features='html.parser').get_text()


def parse_args():
    parser = argparse.ArgumentParser(description='Boot.Dev searcher')

    parser.add_argument(
        'query',
        type=str,
        help='a string to query'
    )
    parser.add_argument(
        '--index',
        '-i',
        action='store_true',
        required=False,
        help='scrape and index boot.dev lessons, takes a while'
    )

    return parser.parse_args()


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
        lesson_uuids = get_all_lesson_uuids()
        scrape_and_index_lessons(lesson_uuids=lesson_uuids, schema=schema)

    index_search(args.query)
