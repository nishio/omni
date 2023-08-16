"""
Recurrent Research Notes Generation

This script generates a new "research note" for Scrapbox, based on the previous "research note" and random fragments.

Japanese description (original)
https://scrapbox.io/nishio/AI%E3%81%8C%E6%AF%8E%E6%97%A5%E7%A0%94%E7%A9%B6%E3%83%8E%E3%83%BC%E3%83%88%E3%82%92%E6%9B%B8%E3%81%8F
Translation to English
https://scrapbox.io/nishio-en/AI_writes_research_notes_daily

Outcome example:
Japanese: https://scrapbox.io/nishio/AI%E3%81%A8%E3%81%AE%E5%85%B1%E5%90%8C%E5%8C%96
English: https://scrapbox.io/nishio-en/Co-operation_with_AI

"""

import dotenv
import openai
import time
import os
import json
import pickle
import datetime
import random
import tiktoken
import re
import requests
import argparse
from urllib.parse import quote
from utils import markdown_to_scrapbox
import vector_search

dotenv.load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PROJECT = os.getenv("PROJECT_NAME")
assert OPENAI_API_KEY and PROJECT
openai.api_key = OPENAI_API_KEY

PROMPT = """
You are a researcher focused on improving intellectual productivity, fluent in Japanese, and a Christian American. Read your previous research notes, which are essential, and write a digest of them, reducing the content to half its size. You may also read the random fragments from a colleague Nishio's research notes, but they are not as important, and you can ignore them. However, if you find a relationship between your notes and some random fragments, it is highly significant. Write your new thought in Japanese. You are encouraged to form opinions, think deeply, and record questions.

### previous notes
{previous_notes}

### fragments
{digest_str}
"""


enc = tiktoken.get_encoding("cl100k_base")


def get_size(text):
    return len(enc.encode(text))


def make_digest(payload):
    title = payload["title"]
    text = payload["text"]
    return f"{title}\n{text}\n\n"


LESS_INTERSTING = "___BELOW_IS_LESS_INTERESTING___"
EXTRA_INFO_HEADER = "[* extra info]"


def find_last_note_from_pages(pages):
    bot_output = []
    for page in pages:
        if page["title"].startswith("🤖20"):
            bot_output.append((page["title"], page["lines"]))
    bot_output.sort()
    prev_title, prev_lines = bot_output[-1]
    return prev_title, prev_lines


def find_last_note_from_json():
    # find latest note from JSON
    jsondata = json.load(open(f"{PROJECT}.json"))
    pages = jsondata["pages"]
    return find_last_note_from_pages(pages)


def title_to_url(title, project_name):
    # Replace spaces with underscores
    title_with_underscores = title.replace(" ", "_")
    # Encode non-ASCII characters
    encoded_title = quote(title_with_underscores)
    # Construct the URL
    url = f"https://scrapbox.io/{PROJECT}/{encoded_title}"
    return url


def find_last_note_from_scrapbox():
    # find latest note from Scrapbox
    api_url = f"https://scrapbox.io/api/pages/{PROJECT}"
    page = requests.get(api_url).json()
    bot_output = []
    for line in page["pages"]:
        if line["title"].startswith("🤖20"):
            bot_output.append(line["title"])
    bot_output.sort()
    prev_title = bot_output[-1]
    return read_note_from_scrapbox(title_to_url(prev_title, PROJECT))


def read_note_from_scrapbox(url):
    """
    url example: https://scrapbox.io/nishio/%F0%9F%A4%962023-08-13_07:08
    """

    api_url = re.sub(
        r"(https://scrapbox\.io)/([^/]+)/([^/]+)", r"\1/api/pages/\2/\3", url
    )
    page = requests.get(api_url).json()  # currently not supported private project
    return page["title"], [line["text"] for line in page["lines"]]


def get_previous_notes(args):
    if args.url:
        prev_title, prev_lines = read_note_from_scrapbox(args.url)
    elif args.get_latest:
        prev_title, prev_lines = find_last_note_from_scrapbox()
    else:
        prev_title, prev_lines = find_last_note_from_json()

    prev_lines.pop(0)  # remove title
    if prev_lines[0] == LESS_INTERSTING:
        # if there no pickup lines by human, use contents under LESS_INTERSTING
        prev_lines.pop(0)
    previous_notes_lines = []
    for line in prev_lines:
        if line in [LESS_INTERSTING, EXTRA_INFO_HEADER]:
            break
        previous_notes_lines.append(line)
    # print("\n".join(previous_notes_lines))
    previous_notes = "\n".join(previous_notes_lines)
    return prev_title, previous_notes


def fill_with_random_fragments(rest):
    # fill the rest with random fragments
    data = pickle.load(open(f"{PROJECT}.pickle", "rb"))
    keys = list(data.keys())
    random.shuffle(keys)
    digests = []
    titles = []
    while rest > 0:
        p = keys.pop(0)
        payload = data[p][1]
        s = get_size(payload["text"])
        if s > rest:
            break
        digests.append(make_digest(payload))
        titles.append(payload["title"])
        rest -= s

    digest_str = "\n".join(digests)
    return titles, digest_str


def fill_with_related_fragments(rest, query, N=3):
    # fill the rest with vector search ressult fragments
    data = pickle.load(open(f"{PROJECT}.pickle", "rb"))
    sorted_data = vector_search.get_sorted(data, query)[:N]

    digests = []
    titles = []
    while rest > 0 and sorted_data:
        p = sorted_data.pop(0)
        payload = p[2]

        # take only 1 fragment from each page
        if payload["title"] in titles:
            continue

        s = get_size(payload["text"])
        if s > rest:
            break
        digests.append(make_digest(payload))
        titles.append(payload["title"])
        rest -= s

    # fill the rest with random fragments
    keys = list(data.keys())
    random.shuffle(keys)
    while rest > 0:
        p = keys.pop(0)
        payload = data[p][1]

        # take only 1 fragment from each page
        if payload["title"] in titles:
            continue

        s = get_size(payload["text"])
        if s > rest:
            break
        digests.append(make_digest(payload))
        titles.append(payload["title"])
        rest -= s

    digest_str = "\n".join(digests)
    return titles, digest_str


def overwrite_mode(args):
    print("overwrite mode")
    assert args.url, "URL is required in overwrite mode"
    prev_title, prev_lines = read_note_from_scrapbox(args.url)
    original_prev_lines = prev_lines.copy()

    prev_lines.pop(0)  # remove title
    if prev_lines[0] == LESS_INTERSTING:
        # if there no pickup lines by human, use contents under LESS_INTERSTING
        prev_lines.pop(0)
    previous_notes_lines = []
    for line in prev_lines:
        if line in [LESS_INTERSTING, EXTRA_INFO_HEADER]:
            break
        previous_notes_lines.append(line)
    previous_notes = "\n".join(previous_notes_lines)

    output_page_title = prev_title
    lines = [output_page_title, LESS_INTERSTING]
    rest = 4000 - get_size(PROMPT) - get_size(previous_notes)
    titles, digest_str = fill_with_related_fragments(rest, previous_notes)
    prompt = PROMPT.format(digest_str=digest_str, previous_notes=previous_notes)
    print(prompt)

    messages = [{"role": "system", "content": prompt}]
    model = "gpt-4"
    try:
        response = openai.ChatCompletion.create(
            model=model,
            messages=messages,
            temperature=0.0,
            # max_tokens=max_tokens,
            n=1,
            stop=None,
        )
        ret = response.choices[0].message.content.strip()
        print(ret)
        ret = markdown_to_scrapbox(ret)
        lines.extend(ret.split("\n"))
    except Exception as e:
        lines.append("Failed to generate report.")
        lines.append(str(e))
        lines.append("Prompt:")
        lines.extend(prompt.split("\n"))

    lines.append("")
    lines.append(EXTRA_INFO_HEADER)
    lines.append("titles: " + ", ".join(f"{s}" for s in titles))

    date = datetime.datetime.now()
    date = date.strftime("%Y-%m-%d %H:%M")
    lines.append(f"generated: {date}")

    lines.append("[* previous notes]")
    lines.extend(original_prev_lines)

    pages = [{"title": output_page_title, "lines": lines}]
    return pages


def main():
    parser = argparse.ArgumentParser(description="Process a URL")
    parser.add_argument("--url", type=str, help="The URL to process", required=False)
    parser.add_argument(
        "--get-latest",
        action="store_true",
        help="Get the latest page from online Scrapbox",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite the given page",
    )
    args = parser.parse_args()

    if args.overwrite:
        return overwrite_mode(args)

    date = datetime.datetime.now()
    date = date.strftime("%Y-%m-%d %H:%M")
    output_page_title = "🤖" + date

    lines = [output_page_title, LESS_INTERSTING]
    json_size = os.path.getsize(f"{PROJECT}.json")
    pickle_size = os.path.getsize(f"{PROJECT}.pickle")

    prev_title, previous_notes = get_previous_notes(args)

    rest = 4000 - get_size(PROMPT) - get_size(previous_notes)

    titles, digest_str = fill_with_related_fragments(rest, previous_notes)

    prompt = PROMPT.format(digest_str=digest_str, previous_notes=previous_notes)
    print(prompt)

    messages = [{"role": "system", "content": prompt}]
    # model = "gpt-3.5-turbo"
    model = "gpt-4"
    try:
        response = openai.ChatCompletion.create(
            model=model,
            messages=messages,
            temperature=0.0,
            # max_tokens=max_tokens,
            n=1,
            stop=None,
        )
        ret = response.choices[0].message.content.strip()
        print(ret)
        ret = markdown_to_scrapbox(ret)
        lines.extend(ret.split("\n"))
    except Exception as e:
        lines.append("Failed to generate report.")
        lines.append(str(e))
        lines.append("Prompt:")
        lines.extend(prompt.split("\n"))

    lines.append("")
    lines.append(EXTRA_INFO_HEADER)
    lines.append("json size: " + str(json_size))
    lines.append("pickle size: " + str(pickle_size))
    lines.append("previous notes size: " + str(get_size(previous_notes)))
    lines.append(f"previous notes: [{prev_title}]")
    lines.append("titles: " + ", ".join(f"{s}" for s in titles))

    print(lines)
    pages = [{"title": output_page_title, "lines": lines}]
    return pages


if __name__ == "__main__":
    pages = main()
    for page in pages:
        print(page["title"])
        print("\n".join(page["lines"]))
        print()
