#/bin/bash -e

python download_latest_release/main.py --repo omni

python write_to_scrapbox/iterative_commenter.py --pioneer-loop