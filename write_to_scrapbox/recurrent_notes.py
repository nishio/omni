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
from utils import (
    markdown_to_scrapbox,
    LESS_INTERESTING,
    EXTRA_INFO_HEADER,
    extract_previous_notes,
    parse_titles,
)
import vector_search

dotenv.load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PROJECT = os.getenv("PROJECT_NAME")
assert OPENAI_API_KEY and PROJECT
openai.api_key = OPENAI_API_KEY


# main prompt, including chadacter settings
PROMPT = "".join(
    [
        "You are Omni, ",
        "a researcher focused on improving intellectual productivity, ",
        "fluent in Japanese, ",
        "and a Christian American. ",
        "Read your previous research notes, ",
        "which are essential, ",
        "and write a digest of them, ",
        "reducing the content to half its size. ",
        "You may also read the random fragments from a colleague Nishio's research notes, ",
        "but they are not as important, ",
        "and you can ignore them. ",
        "However, if you find a relationship between your notes and some random fragments, it is highly significant. ",
        "Use title of fragment to refer them. ",
        "You are encouraged to form opinions, think deeply, and record questions. ",
        "You should use Japanese.",
    ]
)

PROMPT += """

### previous notes
{previous_notes}

### fragments
{digest_str}
"""

CHARACTOR_ICON = "[omni.icon]"


enc = tiktoken.get_encoding("cl100k_base")


def get_size(text):
    return len(enc.encode(text))


def make_digest(payload):
    title = payload["title"]
    text = payload["text"]
    return f"{title}\n{text}\n\n"


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
    if url == "input":
        import urllib.parse

        url = input("url> ")
        print("url:", urllib.parse.unquote(url))
    api_url = re.sub(
        r"(https://scrapbox\.io)/([^/]+)/([^/]+)", r"\1/api/pages/\2/\3", url
    )
    page = requests.get(api_url).json()  # currently not supported private project
    return page["title"], [line["text"] for line in page["lines"]]


def get_previous_notes():
    print("## Get Previous Notes")
    if args.url:
        print("get_previous_notes: from URL")
        prev_title, prev_lines = read_note_from_scrapbox(args.url)
    elif args.get_latest:
        print("get_previous_notes: from Scrapbox API")
        prev_title, prev_lines = find_last_note_from_scrapbox()
    else:
        print("get_previous_notes: from exported JSON")
        prev_title, prev_lines = find_last_note_from_json()

    previous_notes = extract_previous_notes(prev_lines)
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
        title = payload["title"]

        # take only 1 fragment from each page
        if title in titles:
            continue

        # omit AI-generated pages
        if title.startswith("🤖"):
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


def get_used_titles(lines):
    all_titles = []
    for line in lines:
        if line.startswith("titles: "):
            titles = parse_titles(line)
            all_titles.extend(titles)
    return list(set(all_titles))


def overwrite_mode(prev_title, prev_lines):
    print("overwrite:", prev_title)
    original_prev_lines = prev_lines.copy()

    used_pages = get_used_titles(prev_lines)
    print("used pages:", used_pages)

    previous_notes = extract_previous_notes(prev_lines)

    output_page_title = prev_title
    date = datetime.datetime.now()
    date = date.strftime("%Y-%m-%d %H:%M")

    section_title = f"[*** {output_page_title}] {date} {CHARACTOR_ICON}"
    lines = [output_page_title, LESS_INTERESTING, section_title]
    rest = 4000 - get_size(PROMPT) - get_size(previous_notes)
    titles, digest_str = fill_with_related_fragments(rest, previous_notes)
    prompt = PROMPT.format(digest_str=digest_str, previous_notes=previous_notes)
    print(prompt)
    lines.extend(call_gpt(prompt))

    lines.append("")
    lines.append(EXTRA_INFO_HEADER)
    # lines.append("titles: " + ", ".join(f"{s}" for s in titles))
    lines.append("titles: `{0}`".format(json.dumps(titles, ensure_ascii=False)))

    lines.append(f"generated: {date}")

    lines.append("[* previous notes]")
    lines.extend(original_prev_lines)

    pages = [{"title": output_page_title, "lines": lines}]
    return pages


def call_gpt(prompt, model="gpt-4"):
    print("# Call GPT")
    print("## Prompt")
    print(prompt)
    if args.skip_gpt:
        print("## Skipped")
        return ["GPT Skipped"]

    messages = [{"role": "system", "content": prompt}]
    lines = []
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
    return lines


def main_branch():
    """find latest AI-note (title: "🤖" + date), read it, and create new one"""
    print("# Main branch")
    date = datetime.datetime.now()
    date = date.strftime("%Y-%m-%d %H:%M")
    output_page_title = "🤖" + date
    lines = [output_page_title, LESS_INTERESTING, CHARACTOR_ICON]

    previous_note_title, previous_notes = get_previous_notes()

    rest = 4000 - get_size(PROMPT) - get_size(previous_notes)

    print("## Fill with related fragments")
    titles, digest_str = fill_with_related_fragments(rest, previous_notes)

    prompt = PROMPT.format(digest_str=digest_str, previous_notes=previous_notes)
    lines.extend(call_gpt(prompt))
    lines.extend(make_embedding_report(previous_note_title, previous_notes, titles))

    pages = [{"title": output_page_title, "lines": lines}]
    return pages


def make_embedding_report(previous_note_title, previous_notes, titles):
    lines = []
    json_size = os.path.getsize(f"{PROJECT}.json")
    pickle_size = os.path.getsize(f"{PROJECT}.pickle")

    lines.append("")
    lines.append(EXTRA_INFO_HEADER)
    lines.append("json size: " + str(json_size))
    lines.append("pickle size: " + str(pickle_size))
    lines.append("previous notes size: " + str(get_size(previous_notes)))
    lines.append(f"previous notes: [{previous_note_title}]")
    lines.append("fragment titles: " + ", ".join(f"{s}" for s in titles))
    return lines


def multiheads():
    print("# Multi-heads")
    heads = []
    jsondata = json.load(open(f"{PROJECT}.json"))
    pages = jsondata["pages"]
    for page in pages:
        if page["title"].startswith("🤖🔁"):
            heads.append((page["title"], page["lines"]))

    pages_to_update = []
    for head in heads:
        pages_to_update.extend(overwrite_mode(*head))

    return pages_to_update


def main():
    global args
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
    parser.add_argument(
        "--skip-gpt",
        action="store_true",
        help="skip GPT API call for tests",
    )
    args = parser.parse_args()

    if args.overwrite and args.url:
        # URL-specific overwrite, usually triggered by human
        prev_title, prev_lines = read_note_from_scrapbox(args.url)
        return overwrite_mode(prev_title, prev_lines)

    pages_to_update = main_branch()

    if not args.url:
        # when url is specified, user want to update the page only
        pages_to_update.extend(multiheads())

    return pages_to_update


if __name__ == "__main__":
    pages = main()
    for page in pages:
        print(page["title"])
        print("\n".join(page["lines"]))
        print()
