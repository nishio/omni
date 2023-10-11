#/bin/bash -e

# make embedding from private project
python export_from_scrapbox/main.py --project nishio-llm2023
python make_vecs_from_json/main.py --project nishio-llm2023 --is-private

python export_from_scrapbox/main.py --project nishio-books-tmp
python make_vecs_from_json/main.py --project nishio-books-tmp --is-private

python export_from_scrapbox/main.py --project omni-private
python make_vecs_from_json/main.py --project omni-private --is-private

# download other public embedded project
python download_latest_release/main.py --repo omoikane-embed-unnamed-project
python download_latest_release/main.py --repo omoikane-embed
python download_latest_release/main.py --repo omni


python write_to_scrapbox/iterative_commenter.py --pickles all --pioneer-loop-private
