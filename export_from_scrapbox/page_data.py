"""
Port from TypeScript
https://github.com/takker99/scrapbox-userscript-std/blob/main/rest/page-data.ts
"""
from typing import Any, Dict, Union, Optional, TypeVar, Generic
import requests
import dotenv
import os

hostName = "scrapbox.io"
dotenv.load_dotenv()
SID = os.getenv("SID")
PROJECT = os.getenv("PROJECT_NAME")


def export_pages(project=PROJECT, metadata="false"):
    if isinstance(metadata, bool):
        metadata = str(metadata).lower()
    assert metadata in ["true", "false"]

    url = f"https://{hostName}/api/page-data/export/{project}.json?metadata={metadata}"

    cookie = "connect.sid=" + SID
    r = requests.get(url, headers={"Cookie": cookie})
    r.raise_for_status()
    return r.json()
