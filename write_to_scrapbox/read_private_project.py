import dotenv
from utils import get_api_url
import requests
import dotenv
import os
import unittest

dotenv.load_dotenv()
SID = os.getenv("SID")  # required when reading from private Scrapbox project


API_ME = "https://scrapbox.io/api/users/me"


def read_private_pages(url):
    cookie = "connect.sid=" + SID
    r = requests.get(API_ME, headers={"Cookie": cookie})
    r.raise_for_status()
    csrfToken = r.json()["csrfToken"]

    api_url = get_api_url(url)
    r = requests.get(
        api_url,
        headers={
            "Cookie": cookie,
            "Accept": "application/json, text/plain, */*",
            "X-CSRF-TOKEN": csrfToken,
        },
    )
    r.raise_for_status()
    return r.json()


class TestExtractPreviousNotes(unittest.TestCase):
    def test_1(self):
        data = read_private_pages("https://scrapbox.io/enchi/favicon")
        self.assertEqual(data["title"], "favicon")


if __name__ == "__main__":
    unittest.main()
