import markdown
from bs4 import BeautifulSoup
import requests
from constants import *
from whoosh import highlight


def markdown_to_plaintext(markdown_str):
    # type: (str) -> str
    """
    Converts Markdown text to plain text
    """
    html = markdown.markdown(markdown_str)
    return BeautifulSoup(html, features='html.parser').get_text()


def get_all_lesson_uuids():
    # type: () -> set[str]
    """
    Iterates through all courses and gets all lesson UUIDs by using the
    Boot.Dev API
    """
    lesson_uuids = set()
    res = requests.get(BOOTDEV_API_COURSES)
    courses = res.json()
    for course in courses:
        # Skip courses that haven't been published yet
        if course.get('Draft'):
            continue

        for chapter in course.get('Chapters', []):
            lessons = []
            lessons += chapter.get('RequiredLessons', [])
            lessons += chapter.get('OptionalLessons', [])
            for lesson in lessons:
                lesson_uuids.add(lesson.get('UUID'))

    return lesson_uuids


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


class RedFormatter(highlight.Formatter):
    """
    Highlights matched terms in red.
    """
    between = "... \n"

    def format_token(self, txt, token, replace=False):
        token_text = highlight.get_text(txt, token, replace)
        return f'{text.RED}{text.BOLD}{token_text}{text.DEFAULT}'
