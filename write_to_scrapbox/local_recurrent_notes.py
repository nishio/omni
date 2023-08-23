"""
Local Recurrent Research Notes Generation

This script generates a new "research note", based on the previous "research note" and random fragments.
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

### book fragment
{book_fragment_str}
"""

CHARACTOR_ICON = "[omni.icon]"


enc = tiktoken.get_encoding("cl100k_base")


def get_size(text):
    return len(enc.encode(text))


def make_digest(payload):
    title = payload["title"]
    text = payload["text"]
    return f"{title}\n{text}\n\n"


def fill_with_lines(rest, lines, start=0):
    index = start
    chosen = []
    while rest > 0 and index < len(lines):
        line = lines[index]
        s = get_size(line)
        if s > rest:
            break
        rest -= s
        chosen.append(line)
        index += 1
    return chosen, index


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
        # lines.append("Failed to generate report.")
        # lines.append(str(e))
        # lines.append("Prompt:")
        # lines.extend(prompt.split("\n"))
        raise
    return lines


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


def main():
    global args
    parser = argparse.ArgumentParser(description="Process a URL")
    parser.add_argument(
        "--skip-gpt",
        action="store_true",
        help="skip GPT API call for tests",
    )
    parser.add_argument(
        "--start",
        type=int,
        default=None,
        help="start from a specific line",
    )
    args = parser.parse_args()

    book_lines = open("data.txt").read().split("\n")
    title = book_lines[0]
    print(repr(title))

    try:
        prev_lines = open("note.md").read().split("\n")
    except FileNotFoundError:
        prev_lines = []

    if args.start is None:
        for line in prev_lines:
            if line.startswith("end line: "):
                start = int(line.split(":")[1].strip())
                break
        else:
            start = 0
    else:
        start = args.start

    original_prev_lines = prev_lines.copy()

    previous_notes = extract_previous_notes(prev_lines)

    date = datetime.datetime.now()
    date = date.strftime("%Y-%m-%d %H:%M")

    # output_page_title = prev_title
    section_header = f"# {title} {date}"
    lines = [section_header, LESS_INTERESTING, CHARACTOR_ICON]
    rest = 4000 - get_size(PROMPT) - get_size(previous_notes)
    chosen, index = fill_with_lines(rest, book_lines, start)
    book_fragment_str = "\n".join(chosen)
    prompt = PROMPT.format(
        book_fragment_str=book_fragment_str, previous_notes=previous_notes
    )
    print(prompt)
    lines.extend(call_gpt(prompt))

    lines.append("")
    lines.append(EXTRA_INFO_HEADER)
    # lines.append("titles: " + ", ".join(f"{s}" for s in titles))
    lines.append(f"size of previous note: {len(previous_notes)}")
    lines.append(f"size of book fragment: {len(book_fragment_str)}")
    lines.append(f"start line: {start}")
    lines.append(f"end line: {index}")

    lines.extend(original_prev_lines)

    with open("note.md", "w") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    main()
