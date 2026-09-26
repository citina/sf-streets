#!/usr/bin/env python3
"""Download what SF Streets is built from: data.sf.gov (Socrata) -> data/raw/ (not committed).

Each dataset is saved whole as data/raw/<name>.json, a list of rows as the SODA API returns them, fetched in pages.
analyze_sf.py turns them into the page's data. Run with dataset names to fetch only those, e.g.
./fetch_sf.py streets.

So far: the street centerlines (the blocks on the map), what the walking side shows (pedestrian crashes, the High
Injury Network, police reports, calls to police) and the speed and red-light cameras. Dated data is fetched from a little over two years
back (FROM); analyze_sf.py keeps the two years up to each dataset's latest date. `trends` is different: citywide totals
per year for the walking summary, counted by data.sf.gov itself, so only a few rows come back.
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

# calls to police from the public (not officers' own stops), by the call type dispatch closed it as: the kinds about
# harm to people on the street. Left out: calls marked domestic violence, elder or child abuse (DV, EA, CA: mostly at
# home), thefts (mostly shoplifting), suspicious persons, trespassers, noise, alarms, traffic, people in crisis, and
# complaints about homeless people. analyze_sf.py counts each group per corner.
CALL_GROUPS = [("Fights and assaults", ["418", "419", "240", "245", "219"]),
               ("Someone with a gun or knife", ["221", "222", "216", "216S", "217"]),
               ("Robbery", ["211", "212", "213"]),
               ("Threats and harassment", ["650", "646", "311"])]
CALL_TYPES = ",".join(f"'{c}'" for _, cs in CALL_GROUPS for c in cs)

# name -> (dataset id, SoQL filter, columns or None for all)
PED = "(type_of_collision='Vehicle/Pedestrian' OR mviw='Pedestrian') AND ped_action != 'No Pedestrian Involved'"
DATASETS = {
    # Streets – Active and Retired: one row per centerline segment (CNN)
    "streets": ("3psu-pn9h", "active=true", None),
    # Traffic Crashes Resulting in Injury, pedestrians only (the collision type or the other party says so)
    "crashes": ("ubvf-ztfx", f"collision_date >= '{FROM}' AND {PED}",
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
    # Law Enforcement Dispatched Calls for Service: Closed; each call is placed at a nearby intersection (intersection_id)
    "calls": ("2zdj-bwza", f"received_datetime >= '{FROM}' AND onview_flag = 'N' AND call_type_final in ({CALL_TYPES})",
              "cad_number,received_datetime,call_type_final,intersection_id,sensitive_call"),
}

# citywide totals per year -> (dataset id, SoQL select, filter). The police kinds match analyze_sf.py's: reports about
# people (robbery, violence, pickpocketing, weapons) and about drugs (drug offenses, naloxone given); a report counts once.
PER_YEAR = "date_extract_y({}) as y, count(distinct incident_number) as n"
TRENDS = {
    "hit": ("ubvf-ztfx", "date_extract_y(collision_date) as y, count(*) as n, sum(number_killed) as killed", PED),
    "people": ("wg3w-h783", PER_YEAR.format("incident_date"),
               "incident_category in ('Robbery','Assault','Homicide','Rape','Sex Offense')"
               " OR starts_with(incident_category, 'Human Trafficking') OR starts_with(incident_category, 'Weapons')"
               " OR incident_subcategory in ('Larceny Theft - Pickpocket','Larceny Theft - Purse Snatch')"),
    "drugs": ("wg3w-h783", PER_YEAR.format("incident_date"), "starts_with(incident_category, 'Drug') OR incident_code='51050'"),
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


def save(name, rows):
    RAW.mkdir(parents=True, exist_ok=True)
    part = RAW / f"{name}.json.part"
    part.write_text(json.dumps(rows, separators=(",", ":")))
    part.replace(RAW / f"{name}.json")   # only replace the old copy once the new one is complete


def fetch_trends():
    out = {}
    for k, (ds, sel, where) in TRENDS.items():
        q = {"$select": sel, "$where": where, "$group": "y", "$order": "y"}
        out[k] = get(API.format(id=ds) + "?" + urllib.parse.urlencode(q))
        print(f"  trends: {k}, {len(out[k])} years")
    save("trends", out)


def fetch(name):
    if name == "trends":
        return fetch_trends()
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
    save(name, rows)


if __name__ == "__main__":
    for name in sys.argv[1:] or [*DATASETS, "trends"]:
        fetch(name)
