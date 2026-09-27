#!/usr/bin/env python3
"""Download what SF Streets is built from: data.sf.gov (Socrata) -> data/raw/ (not committed).

Each dataset is saved whole as data/raw/<name>.json, a list of rows as the SODA API returns them, fetched in pages.
analyze_sf.py turns them into the page's data. Run with dataset names to fetch only those, e.g.
./fetch_sf.py streets.

So far: the street centerlines (the blocks on the map), what the walking side shows (pedestrian crashes, the High
Injury Network, police reports, calls to police), the speed and red-light cameras, and the driving side's parking rules
(street cleaning, time limits and permit areas, meters and their hours) and tickets. Dated data is fetched from a little
over two years back (FROM); analyze_sf.py keeps the two years up to each dataset's latest date. `trends` is different:
citywide totals per year for the walking summary, counted by data.sf.gov itself, so only a few rows come back.

The two big tables come as CSV: `policies` (each meter's hours and rates, data/raw/policies.csv) and `tickets` (SFMTA
parking citations, data/raw/tickets/YYYY-MM.csv, a month at a time, about 105k rows and 40 seconds each). A month already
on disk is kept unless it's one of the last two, which the city is still filling in, or its copy is over four weeks old,
so each month is checked again about once a month. The weekly run keeps the months between runs (weekly.yml's cache).
"""
import csv
import io
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path

RAW = Path(__file__).resolve().parent / "data" / "raw"
API = "https://data.sf.gov/resource/{id}.json"
PAGE = 50000
_m = date.today().year * 12 + date.today().month - 1 - 28   # 2 years and 4 months back: crash data runs ~2 months late
FROM = date(_m // 12, _m % 12 + 1, 1).isoformat()
TICKET_MONTHS = 24   # months back to the one the two-year window starts in (tickets run up to the day before)

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
    # Street Sweeping Schedule: one row per block side (CNN, left or right of the centerline's direction) and weekday;
    # its line places the rows whose CNN has since been retired (two segments merged into one)
    "sweeping": ("yhqp-riqs", "", "cnn,cnnrightleft,blockside,weekday,fromhour,tohour,week1,week2,week3,week4,week5,holidays,line"),
    # Parking regulations (except non-metered color curb): time limits, permit areas, no parking; lines along the curb,
    # with no CNN, so analyze_sf.py places them by geometry
    "regs": ("hi6h-neyh", "", "regulation,days,hrs_begin,hrs_end,hrlimit,rpparea1,rpparea2,rpparea3,exceptions,shape"),
    # Parking Meters, on the street: the post ID ties each to its hours and rates in `policies`
    "meters": ("8vzz-qzz9", "on_offstreet_type = 'ON'",
               "post_id,street_seg_ctrln_id,active_meter_flag,cap_color,street_num,longitude,latitude"),
    # SFMTA Managed Off-street Parking: the garages and lots the city runs (SFMTA, the Port, Rec and Park); privately run
    # ones aren't in the city's open data
    "garages": ("vqzx-t7c4", "", "facility_name,street_address,facility_type,owner,capacity,services,web_site,location,"
                                 "main_entrance_lat,main_entrance_long,street_seg_ctrln_id"),
}
TODAY = date.today().isoformat()
# name -> (dataset id, SoQL filter, columns), saved as data/raw/<name>.csv
CSVS = {
    # Meter Policies: each meter's day in pieces (paid, tow-away, pay ahead, or open to all), with rate and time limit;
    # only what's in effect now, and not the free pieces (free is whatever isn't listed)
    "policies": ("qq7v-hds4", f"startdate <= '{TODAY}' AND enddate > '{TODAY}' AND scheduletype != 'FREE'",
                 "postid,dayofweek,starttime,endtime,scheduletype,hourlyrate,timelimitminutes"),
}
# SFMTA Parking Citations & Fines, a month at a time. The feed has some rows dated years ahead (typos): anything after
# today is left out.
TICKETS = ("ab4h-6ztd", "citation_issued_datetime,violation_desc,citation_location,fine_amount,latitude,longitude")

# citywide totals per year -> (dataset id, SoQL select, filter). The police kinds match analyze_sf.py's: reports about
# people (robbery, violence, pickpocketing, weapons) and drug offenses; a report counts once.
PER_YEAR = "date_extract_y({}) as y, count(distinct incident_number) as n"
TRENDS = {
    "hit": ("ubvf-ztfx", "date_extract_y(collision_date) as y, count(*) as n, sum(number_killed) as killed", PED),
    "people": ("wg3w-h783", PER_YEAR.format("incident_date"),
               "incident_category in ('Robbery','Assault','Homicide','Rape','Sex Offense')"
               " OR starts_with(incident_category, 'Human Trafficking') OR starts_with(incident_category, 'Weapons')"
               " OR incident_subcategory in ('Larceny Theft - Pickpocket','Larceny Theft - Purse Snatch')"),
    "drugs": ("wg3w-h783", PER_YEAR.format("incident_date"), "starts_with(incident_category, 'Drug')"),
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


def get_csv(ds, where, cols, what):
    """Every row of a query as CSV text (the header once), a page at a time."""
    out, n = [], 0
    while True:
        q = {"$select": cols, "$where": where, "$order": ":id", "$limit": PAGE, "$offset": n}
        for k in range(4):
            try:
                with urllib.request.urlopen(API.replace(".json", ".csv").format(id=ds) + "?" + urllib.parse.urlencode(q),
                                            timeout=300) as r:
                    body = r.read().decode()
                break
            except Exception as e:
                if k == 3:
                    raise
                print(f"  retrying after {e}")
                time.sleep(5 * (k + 1))
        rows = list(csv.reader(io.StringIO(body)))
        if not out:
            out.append(rows[0])
        out += rows[1:]
        n += len(rows) - 1
        print(f"  {what}: {n:,} rows")
        if len(rows) - 1 < PAGE:
            return out


def save_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_suffix(".part")
    with part.open("w", newline="") as f:
        csv.writer(f).writerows(rows)
    part.replace(path)


def fetch_tickets():
    today = date.today()
    first = today.year * 12 + today.month - 1 - TICKET_MONTHS
    months = [date(m // 12, m % 12 + 1, 1) for m in range(first, today.year * 12 + today.month)]
    keep = {f"{m:%Y-%m}.csv" for m in months}
    for old in (RAW / "tickets").glob("*.csv"):
        if old.name not in keep:
            old.unlink()
    ds, cols = TICKETS
    for i, m in enumerate(months):
        path = RAW / "tickets" / f"{m:%Y-%m}.csv"
        if path.exists() and i < len(months) - 2 and time.time() - path.stat().st_mtime < 28 * 86400:
            continue
        nxt = min((m + timedelta(days=32)).replace(day=1), today + timedelta(days=1))
        save_csv(path, get_csv(ds, f"citation_issued_datetime >= '{m}' AND citation_issued_datetime < '{nxt}'", cols,
                               f"tickets {m:%Y-%m}"))


def fetch(name):
    if name == "trends":
        return fetch_trends()
    if name == "tickets":
        return fetch_tickets()
    if name in CSVS:
        return save_csv(RAW / f"{name}.csv", get_csv(*CSVS[name], name))
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
    for name in sys.argv[1:] or [*DATASETS, *CSVS, "tickets", "trends"]:
        fetch(name)
