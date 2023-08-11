import dotenv
import openai
import time
import os
import json
import pickle
import datetime
import random
import tiktoken

dotenv.load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PROJECT = os.getenv("PROJECT_NAME")
assert OPENAI_API_KEY and PROJECT
openai.api_key = OPENAI_API_KEY

PROMPT = """You are a researcher focused on improving intellectual productivity who can fluently read and write in Japanese, and you are a Christian American. Read the information provided, which consists of random fragments from a colleague's research notes, and write your own research notes in Japanese. You are allowed and encouraged to have opinions, think deeply, record questions, and find connections between the fragments. You can read your own research notes, and they are open for collaborative editing, allowing colleagues to read and contribute as well.

## previous notes
{previous_notes}

## fragments
{digest_str}
"""


enc = tiktoken.get_encoding("cl100k_base")


def get_size(text):
    return len(enc.encode(text))


def make_digest(payload):
    title = payload["title"]
    text = payload["text"]
    return f"### {title}\n{text}\n"


LESS_INTERSTING = "___BELOW_IS_LESS_INTERESTING___"


def main():
    date = datetime.datetime.now()
    date = date.strftime("%Y-%m-%d %H:%M")
    output_page_title = "🤖" + date
    lines = [output_page_title, LESS_INTERSTING]
    json_size = os.path.getsize(f"{PROJECT}.json")
    pickle_size = os.path.getsize(f"{PROJECT}.pickle")

    jsondata = json.load(open(f"{PROJECT}.json"))
    pages = jsondata["pages"]
    bot_output = []
    for page in pages:
        if page["title"].startswith("🤖20"):
            bot_output.append((page["title"], page["lines"]))
    bot_output.sort()
    prev_title, prev_lines = bot_output[-1]
    previous_notes_lines = []
    for line in prev_lines:
        if line.startswith(LESS_INTERSTING):
            break
        previous_notes_lines.append(line)
    print("\n".join(previous_notes_lines))
    previous_notes = "\n".join(previous_notes_lines)

    data = pickle.load(open(f"{PROJECT}.pickle", "rb"))
    # take 2000 tokens digests
    keys = list(data.keys())
    random.shuffle(keys)
    rest = 2000 - get_size(previous_notes)
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
        lines.extend(ret.split("\n"))
    except Exception as e:
        lines.append("Failed to generate report.")
        lines.append(str(e))
        lines.append("Prompt:")
        lines.extend(prompt.split("\n"))

    lines.append("")
    lines.append("[* extra info]")
    lines.append("json size: " + str(json_size))
    lines.append("pickle size: " + str(pickle_size))
    lines.append("previous notes size: " + str(get_size(previous_notes)))
    lines.append(f"previous notes: [{prev_title}]")
    lines.append("titles: " + ", ".join(f"[{s}]" for s in titles))

    print(lines)
    pages = [{"title": output_page_title, "lines": lines}]
    return pages


if __name__ == "__main__":
    pages = main()
    for page in pages:
        print(page["title"])
        print("\n".join(page["lines"]))
        print()
