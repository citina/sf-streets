#!/usr/bin/env python3
"""Download what SF Streets is built from: data.sf.gov (Socrata) -> data/raw/ (not committed).

Each dataset is saved whole as data/raw/<name>.json, a list of rows as the SODA API returns them, fetched in pages.
analyze_sf.py turns them into the page's data. Run with dataset names to fetch only those, e.g.
./fetch_sf.py streets.

So far: the street centerlines (the blocks on the map). The rest of PLAN.md §2 comes with milestones 2 and 4.
"""
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

RAW = Path(__file__).resolve().parent / "data" / "raw"
API = "https://data.sf.gov/resource/{id}.json"
PAGE = 50000

# name -> (dataset id, SoQL filter)
DATASETS = {
    "streets": ("3psu-pn9h", "active=true"),   # Streets – Active and Retired: one row per centerline segment (CNN)
}


def get(url, tries=4):
    for k in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=180) as r:
                return json.load(r)
        except Exception as e:   # the portal times out now and then; wait and try again
            if k == tries - 1:
                raise
            print(f"  retrying after {e}")
            time.sleep(5 * (k + 1))


def fetch(name):
    ds, where = DATASETS[name]
    rows = []
    while True:
        q = {"$limit": PAGE, "$offset": len(rows), "$order": ":id"}
        if where:
            q["$where"] = where
        page = get(API.format(id=ds) + "?" + urllib.parse.urlencode(q))
        rows += page
        print(f"  {name}: {len(rows):,} rows")
        if len(page) < PAGE:
            break
    RAW.mkdir(parents=True, exist_ok=True)
    part = RAW / f"{name}.json.part"
    part.write_text(json.dumps(rows, separators=(",", ":")))
    part.replace(RAW / f"{name}.json")   # only replace the old copy once the new one is complete


if __name__ == "__main__":
    for name in sys.argv[1:] or DATASETS:
        fetch(name)
