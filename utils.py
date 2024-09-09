import os
import markdown
from bs4 import BeautifulSoup
import requests
from constants import *
from whoosh import highlight
from whoosh.searching import Results


def markdown_to_plaintext(markdown_str):
    # type: (str) -> str
    """
    Converts Markdown text to plain text
    """
    html = markdown.markdown(markdown_str)
    return BeautifulSoup(html, features='html.parser').get_text()


def get_lessons_by_languages(languages):
    # type: (str) -> set[str]
    """
    Iterates through all courses and gets all lesson UUIDs of the chosen
    languages by using the Boot.Dev API
    """
    # Make sure languages is iterable and not a single string
    languages = [] if not languages else languages
    if not hasattr(languages, '__iter__') or isinstance(languages, str):
        languages = [languages]

    language_lessons = {}
    res = requests.get(BOOTDEV_API_COURSES)
    courses = res.json()
    for course in courses:
        # Skip courses that haven't been published yet
        if course.get('Draft'):
            continue

        # Skip courses that don't match the requested languages
        language = course.get('Language', "")
        if languages and language not in languages:
            continue

        for chapter in course.get('Chapters', []):
            lessons = []
            lessons += chapter.get('RequiredLessons', [])
            lessons += chapter.get('OptionalLessons', [])
            for lesson in lessons:
                lesson_uuids = language_lessons.get(language, set())
                lesson_uuids.add(lesson.get('UUID'))
                language_lessons[language] = lesson_uuids

    return language_lessons


def get_lesson_and_content(api_url):
    # type: (str) -> tuple[dict, str]
    """
    Fetches lesson content from Boot.Dev API url
    """
    response = requests.get(api_url)
    lesson = response.json().get('Lesson', {})
    if not lesson:
        print('no lesson:', api_url)
        return

    # Get lesson data
    data_ls = []
    for data_key in lesson.keys():
        if not data_key.startswith('LessonData'):
            continue
        data_ls.append(lesson.get(data_key, {}))
    data_ls = filter(lambda x: x, data_ls)

    # Get content from lesson data
    content = ''
    for data_key in data_ls:
        content += f"{data_key.get('Readme', '')}\n"

    return lesson, markdown_to_plaintext(content)


def get_indexed_languages():
    """
    Get languages that have been indexed at least once
    """
    langs_dict = {}
    if not os.path.exists('indexdir'):
        return langs_dict

    langs = os.listdir('indexdir')
    for lang in langs:
        langs_dict[lang] = os.path.getmtime(os.path.join('indexdir', lang))

    return langs_dict


def pretty_print_result(query, language, result, lesson, content):
    # type: (str, str, Results, dict[str, str], str) -> None
    """
    Prints a result hit nicely to the console with colors
    """
    # Language and Title
    print(text.BOLD, text.GREEN, sep='', end='')
    print(f"{language.upper()}: {lesson.get('Title', '')}")
    print(text.DEFAULT, end='')

    # Link
    print(text.UNDERLINE, text.BLUE, sep='', end='')
    highlight_query = '&text='.join(query.split(' '))
    print(f'{BOOTDEV_LESSONS}/{result["uuid"]}#:~:text={highlight_query}')
    print(text.DEFAULT, end='')

    # Content extract
    print(result.highlights('content', text=content), end='\n\n\n')


class RedFormatter(highlight.Formatter):
    """
    Highlights matched terms in red.
    """
    between = "... \n"

    def format_token(self, txt, token, replace=False):
        token_text = highlight.get_text(txt, token, replace)
        return f'{text.RED}{text.BOLD}{token_text}{text.DEFAULT}'
