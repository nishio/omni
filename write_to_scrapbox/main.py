"""
entrypoint from github actions
"""

import scrapbox_io
import recurrent_notes


def main(dry=False):
    pages = recurrent_notes.main()
    scrapbox_io.write_pages(pages)
    print("write ok")


if __name__ == "__main__":
    main()
