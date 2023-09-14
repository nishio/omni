import os
import json
from page_data import export_pages
import dotenv
import argparse

dotenv.load_dotenv()

# Getting environment variables
SID = os.getenv("SID")
PROJECT_NAME = os.getenv("PROJECT_NAME")
assert SID

parser = argparse.ArgumentParser(description="Export project data.")
parser.add_argument(
    "--project",
    type=str,
    default=PROJECT_NAME,
    help="The name of the project to export.",
)
args = parser.parse_args()
PROJECT_NAME = args.project

print(f'Exporting a json file from "/{PROJECT_NAME}"...')
result = export_pages(PROJECT_NAME)
with open(f"{PROJECT_NAME}.json", "w") as file:
    json.dump(result, file, indent=2)

print(f'OK, wrote "{PROJECT_NAME}.json"')
