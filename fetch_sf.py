#!/usr/bin/env python3
"""Download what SF Streets is built from: data.sf.gov (Socrata) -> data/raw/ (not committed).

Each dataset is saved whole as data/raw/<name>.json, a list of rows as the SODA API returns them, fetched in pages.
analyze_sf.py turns them into the page's data. Run with dataset names to fetch only those, e.g.
./fetch_sf.py streets.

So far: the street centerlines (the blocks on the map), what the walking side shows (pedestrian crashes, the High
Injury Network, police reports) and the speed and red-light cameras. Dated data is fetched from a little over two years
back (FROM); analyze_sf.py keeps the two years up to each dataset's latest date.
"""
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

RAW = Path(__file__).resolve().parent / "data" / "raw"
API = "https://data.sf.gov/resource/{id}.json"
PAGE = 50000
_m = date.today().year * 12 + date.today().month - 1 - 28   # 2 years and 4 months back: crash data runs ~2 months late
FROM = date(_m // 12, _m % 12 + 1, 1).isoformat()

# name -> (dataset id, SoQL filter, columns or None for all)
DATASETS = {
    # Streets – Active and Retired: one row per centerline segment (CNN)
    "streets": ("3psu-pn9h", "active=true", None),
    # Traffic Crashes Resulting in Injury, pedestrians only (the collision type or the other party says so)
    "crashes": ("ubvf-ztfx", f"collision_date >= '{FROM}' AND (type_of_collision='Vehicle/Pedestrian' OR mviw='Pedestrian')"
                " AND ped_action != 'No Pedestrian Involved'",
                "unique_id,collision_datetime,collision_severity,number_killed,number_injured,lighting,ped_action,"
                "vz_pcf_description,intersection,cnn_intrsctn_fkey,cnn_sgmt_fkey,tb_latitude,tb_longitude"),
    # 2024 High Injury Network: the segments (CNN) on it
    "hin": ("enwt-3u8m", "", "cnn_sgmt_pkey"),
    # Police Department Incident Reports: 2018 to Present; each place is snapped to a nearby intersection (cnn)
    "police": ("wg3w-h783", f"incident_date >= '{FROM}'",
               "incident_number,incident_datetime,incident_category,incident_subcategory,incident_code,cnn,latitude,longitude"),
    # Automated Speed Enforcement Citations: daily counts per camera (since April 2025)
    "speedcams": ("d5uh-bk84", f"date >= '{FROM}'", None),
    # Red Light Camera Citations: monthly counts per intersection and direction
    "redlight": ("uzmr-g2uc", f"month >= '{FROM}'", None),
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
    ds, where, cols = DATASETS[name]
    rows = []
    while True:
        q = {"$limit": PAGE, "$offset": len(rows), "$order": ":id"}
        if where:
            q["$where"] = where
        if cols:
            q["$select"] = cols
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
