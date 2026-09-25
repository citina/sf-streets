#!/usr/bin/env python3
"""The page's data: data/raw/ (from fetch_sf.py) -> docs/data/ (not committed).

A block is one centerline segment, keyed by its CNN (centerline network number), the key the city's parking, sweeping
and crash data all share. Its name is the street and its hundred block, from the segment's address ranges, and it runs
between the cross streets at its two ends. Its corners are the intersections (node CNNs) at those ends.

Dated data covers the two years up to each dataset's latest date (WINDOW). Every crash and police report is also marked
daylight or after dark, from the sun's times in San Francisco on its date.

The map is split into cells of about 1 km (as on LA Street Rules), so the page only loads the few cells it's showing:
  cells/{x}_{y}.json  one cell: {b: blocks, c: corners, x: crashes}. Positions are zoom-17 pixels from the cell's corner.
                      block  {id: CNN, s: street name, h: hundred block (none without addresses), g: lines,
                              x: cross streets, sd: 1 or 2 when it carries only the odd or even house numbers,
                              nh: neighborhood, nd: its two corners' CNNs, hin: 1 on the High Injury Network,
                              pr: {kind: percentile}, how its corners' police reports rank among all blocks}
                      corner {id: node CNN, p: [x, y], k: police reports per kind, daylight and after dark in turn}
                      crash  [x, y, hour, severity, after dark, cause, where (the block's or the corner's CNN)]
  index.json          loads with the page: names, neighborhoods (with their km of street, police reports about people
                      and about drugs, and pedestrians hit), which cells exist, the time windows, the kinds of police
                      report and crash causes (by number), and the speed and red-light cameras
  streets.json        loads on the first search: for each street name, its blocks as
                      [CNN, hundred, cell, from street, to street, odd/even side]
"""
import collections
import json
import math
import re
import shutil
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "docs" / "data"
N17 = 2 ** 17 * 256
CELL = 1024   # map cell edge in zoom-17 Web Mercator pixels
PX_M = 156543.03392 * math.cos(math.radians(37.76)) / 2 ** 17   # metres per zoom-17 pixel in SF (about 0.95)
WINDOW = timedelta(days=730)   # two years
PT = ZoneInfo("America/Los_Angeles")

# kept: streets, park roads (Golden Gate Park, the Presidio, Fort Mason), Treasure and Yerba Buena Islands, Hunters Point
# Shipyard, pedestrian streets. Left out: freeways and ramps, paper streets, private roads and lots, unpaved rights of
# way, addressing-only segments.
LAYERS = {"STREETS", "STREETS_TI", "STREETS_YBI", "STREETS_HUNTERSP", "STREETS_PEDESTRI",
          "PARKS", "PARKS_NPS_PRESIDIO", "PARKS_NPS_FTMASON"}
SKIP_CLASS = {"1", "6"}   # freeway, freeway ramp
SPECIAL = {"OFARRELL": "O'Farrell", "OREILLY": "O'Reilly", "OSHAUGHNESSY": "O'Shaughnessy", "MACARTHUR": "MacArthur",
           "GGP": "GGP", "SFGH": "SFGH", "UCSF": "UCSF", "USF": "USF"}

# police reports: the kinds the page shows, from SFPD's categories and codes. A report can be more than one kind, and
# counts once per kind (supplements to a report share its number).
KINDS = ["Robbery", "Assault and other violence", "Pickpocketing and purse snatching", "Weapons",
         "Drug offenses", "Naloxone given for an overdose", "Car break-ins"]
VIOLENCE = {"Assault", "Homicide", "Rape", "Sex Offense"}
CAR_BREAKIN = {"Larceny - From Vehicle", "Theft From Vehicle", "Larceny - Auto Parts"}
PERSON = [0, 1, 2, 3]   # the kinds counted as reports of harm to people on the street
DRUGS = [4, 5]

SEVERITY = {"Injury (Complaint of Pain)": 0, "Injury (Other Visible)": 1, "Injury (Severe)": 2, "Fatal": 3}
# the crash report's primary collision factor, in plain words where the city's wording is hard to read
CAUSE = {"Driver or bicyclist to yield right-of-way at crosswalks": "Driver didn't yield to someone in a crosswalk",
         "Pedestrians must yield right-of-way outside of crosswalks": "Person crossing outside a crosswalk didn't yield",
         "Unsafe speed for prevailing conditions": "Driving too fast for conditions",
         "Crossing between controlled intersections (Jaywalking)": "Crossing mid-block between signals",
         "Unsafe starting or backing on highway": "Driver started or backed up unsafely",
         "Pedestrian violation of walk or wait signals": "Person crossed against the walk signal",
         "Red signal - driver or bicyclist responsibilities": "Driver ran a red light",
         "Pedestrian suddenly entering into vehicle path close enough to create an immediate hazard":
             "Person stepped into the car's path",
         "Red signal - pedestrian responsibilities": "Person crossed on a red light",
         "Unsafe turn or lane change prohibited": "Unsafe turn or lane change",
         "Failure to stop at STOP sign": "Driver didn't stop at a stop sign",
         "Unknown": "Not recorded", "": "Not recorded"}
DIRS = {"NB": "northbound", "SB": "southbound", "EB": "eastbound", "WB": "westbound"}


def z17(lon, lat):
    r = math.radians(lat)
    return (lon + 180) / 360 * N17, (1 - math.log(math.tan(r) + 1 / math.cos(r)) / math.pi) / 2 * N17


def load(name):
    return json.loads((RAW / f"{name}.json").read_text())


def when(s):
    return datetime.fromisoformat(s[:19])


def nice(name):
    """'03RD ST' -> '3rd St', 'MCALLISTER ST' -> 'McAllister St', 'JOHN F KENNEDY DR' -> 'John F Kennedy Dr'."""
    out = []
    for w in name.split():
        if w in SPECIAL:
            out.append(SPECIAL[w])
        elif m := re.fullmatch(r"0*(\d+)(ST|ND|RD|TH)", w):
            out.append(m[1] + m[2].lower())
        elif re.fullmatch(r"MC[A-Z]{2,}", w):
            out.append("Mc" + w[2:].capitalize())
        elif re.fullmatch(r"O'[A-Z]+", w):
            out.append("O'" + w[2:].capitalize())
        elif len(w) == 1 or w.isdigit():
            out.append(w)
        else:
            out.append("-".join(p.capitalize() for p in w.split("-")))
    return " ".join(out)


def cross(v):
    """A cross street as the city writes it; None at a dead end, the city line or a mid-block split."""
    v = (v or "").strip()
    if not v or re.match(r"(START|END|MID)\s*:|MID BLOCK", v):
        return None
    return " / ".join(nice(p.strip()) for p in v.split("\\") if p.strip())


def hundred(r):
    nums = [float(r.get(f) or 0) for f in ("lf_fadd", "lf_toadd", "rt_fadd", "rt_toadd")]
    nums = [n for n in nums if n > 0]
    return int(min(nums)) // 100 * 100 if nums else None


def side(r):
    """1 or 2 when the segment has house numbers on one side only (odd or even), as each half of a divided street
    does; else 0."""
    left, right = ([int(float(r.get(f) or 0)) for f in fs] for fs in (("lf_fadd", "lf_toadd"), ("rt_fadd", "rt_toadd")))
    if any(left) != any(right):
        n = next(v for v in left + right if v)
        return 1 if n % 2 else 2
    return 0


_sun = {}


def dark(t):
    """Whether a local time in San Francisco is between sunset and sunrise (NOAA's approximation, within a few
    minutes)."""
    d = t.date()
    if d not in _sun:
        g = 2 * math.pi / 365 * (d.timetuple().tm_yday - 1)
        eq = 229.18 * (0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g) - 0.014615 * math.cos(2 * g)
                       - 0.040849 * math.sin(2 * g))
        dec = (0.006918 - 0.399912 * math.cos(g) + 0.070257 * math.sin(g) - 0.006758 * math.cos(2 * g)
               + 0.000907 * math.sin(2 * g) - 0.002697 * math.cos(3 * g) + 0.00148 * math.sin(3 * g))
        lat, lon = math.radians(37.77), -122.42
        ha = math.degrees(math.acos(math.cos(math.radians(90.833)) / (math.cos(lat) * math.cos(dec))
                                    - math.tan(lat) * math.tan(dec)))
        off = datetime(d.year, d.month, d.day, 12, tzinfo=PT).utcoffset().total_seconds() / 60
        _sun[d] = (720 - 4 * (lon + ha) - eq + off, 720 - 4 * (lon - ha) - eq + off)
    m = t.hour * 60 + t.minute
    return m < _sun[d][0] or m >= _sun[d][1]


def pct_ranks(values):
    """For each value, the share of all values below it, 0-100 (rounded down)."""
    s = sorted(values)
    out = {}
    for i, v in enumerate(s):
        if v not in out:
            out[v] = 100 * i // len(s)
    return out


# ---------- blocks and corners ----------
rows = load("streets")
segs = [r for r in rows if r.get("layer") in LAYERS and r.get("classcode") not in SKIP_CLASS and "line" in r
        and not re.search(r"\bRAMP\b|PARKING LOT", r.get("streetname", ""))]
seg_ids = {int(r["cnn"]) for r in segs}
hoods = sorted({r["analysis_neighborhood"] for r in segs if r.get("analysis_neighborhood")})
hood_ix = {h: i for i, h in enumerate(hoods)}
hin = {int(float(r["cnn_sgmt_pkey"])) for r in load("hin")} & seg_ids
names, name_ix = [], {}


def nix(name):
    if name not in name_ix:
        name_ix[name] = len(names)
        names.append(name)
    return name_ix[name]


def node(v):
    return int(float(v)) if v else None


# a corner's position: where the segments that meet there end (each segment runs from its f_node to its t_node)
ends = collections.defaultdict(list)
for r in segs:
    c = r["line"]["coordinates"]
    for k, (lon, lat) in (("f_node_cnn", c[0]), ("t_node_cnn", c[-1])):
        if node(r.get(k)):
            ends[node(r[k])].append(z17(lon, lat))
corner_at = {n: tuple(sorted(p[i] for p in ps)[len(ps) // 2] for i in (0, 1)) for n, ps in ends.items()}

cells = collections.defaultdict(lambda: dict(b=[], c=[], x=[]))
cell_of = lambda x, y: (int(x // CELL), int(y // CELL))
index = []   # (street, CNN, hundred, cell, from street, to street, side)
blocks = []
for r in sorted(segs, key=lambda r: (r.get("streetname_gc") or r["streetname"], hundred(r) or 0, int(r["cnn"]))):
    pts = [z17(lon, lat) for lon, lat in r["line"]["coordinates"]]
    cx, cy = cell_of(sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))
    line = []
    for x, y in pts:
        p = [round(x - cx * CELL), round(y - cy * CELL)]
        if line[-2:] != p:
            line += p
    if len(line) < 4:
        continue
    s, h, sd = nix(nice(r.get("streetname_gc") or r["streetname"])), hundred(r), side(r)
    f, t = (nix(c) if (c := cross(r.get(k))) else None for k in ("f_st", "t_st"))
    rec = dict(id=int(r["cnn"]), s=s, g=[line], x=[i for i in (f, t) if i is not None])
    if h is not None:
        rec["h"] = h
    if sd:
        rec["sd"] = sd
    if r.get("analysis_neighborhood"):
        rec["nh"] = hood_ix[r["analysis_neighborhood"]]
    rec["nd"] = [n for n in (node(r.get("f_node_cnn")), node(r.get("t_node_cnn"))) if n]
    if rec["id"] in hin:
        rec["hin"] = 1
    cells[(cx, cy)]["b"].append(rec)
    blocks.append(rec)
    index.append((s, rec["id"], h, f"{cx}_{cy}", f, t, sd))

# ---------- police reports, per corner and kind, daylight and after dark ----------
police = load("police")
p_end = max(when(r["incident_datetime"]) for r in police)
p_start = p_end - WINDOW
counts = collections.defaultdict(lambda: [0] * (2 * len(KINDS)))
seen, off_map = set(), 0
for r in police:
    t, n = when(r["incident_datetime"]), node(r.get("cnn"))
    if t <= p_start:
        continue
    if n not in corner_at:
        off_map += 1
        continue
    cat, sub = r.get("incident_category") or "", r.get("incident_subcategory") or ""
    kinds = {0} if cat == "Robbery" else set()
    if cat in VIOLENCE or cat.startswith("Human Trafficking"):
        kinds.add(1)
    if sub in ("Larceny Theft - Pickpocket", "Larceny Theft - Purse Snatch"):
        kinds.add(2)
    if cat.startswith("Weapons"):
        kinds.add(3)
    if cat.startswith("Drug"):
        kinds.add(4)
    if r.get("incident_code") == "51050":
        kinds.add(5)
    if sub in CAR_BREAKIN:
        kinds.add(6)
    for k in kinds:
        if (r["incident_number"], k) not in seen:
            seen.add((r["incident_number"], k))
            counts[n][2 * k + dark(t)] += 1
for n, k in counts.items():
    x, y = corner_at[n]
    cx, cy = cell_of(x, y)
    cells[(cx, cy)]["c"].append(dict(id=n, p=[round(x - cx * CELL), round(y - cy * CELL)], k=k))

# how each block's corners rank among all blocks: people, drugs and overdoses, car break-ins (any time of day)
total = lambda n, ks: sum(counts[n][2 * k] + counts[n][2 * k + 1] for k in ks) if n in counts else 0
for key, ks in (("people", PERSON), ("drugs", DRUGS), ("cars", [6])):
    vals = {b["id"]: sum(total(n, ks) for n in b["nd"]) for b in blocks}
    ranks = pct_ranks(vals.values())
    for b in blocks:
        if vals[b["id"]]:
            b.setdefault("pr", {})[key] = ranks[vals[b["id"]]]

# ---------- pedestrian crashes ----------
crashes = load("crashes")
c_end = max(when(r["collision_datetime"]) for r in crashes)
c_start = c_end - WINDOW
causes, cause_ix = [], {}
n_crash = collections.Counter()
for r in crashes:
    t = when(r["collision_datetime"])
    if t <= c_start or not r.get("tb_latitude"):
        continue
    seg, nd = node(r.get("cnn_sgmt_fkey")), node(r.get("cnn_intrsctn_fkey"))
    # mid-block crashes belong to the block, the rest to the corner
    at = seg if (r.get("intersection") or "").startswith("Midblock") and seg in seg_ids else nd
    cause = CAUSE.get(r.get("vz_pcf_description") or "", r.get("vz_pcf_description"))
    if cause not in cause_ix:
        cause_ix[cause] = len(causes)
        causes.append(cause)
    x, y = z17(float(r["tb_longitude"]), float(r["tb_latitude"]))
    cx, cy = cell_of(x, y)
    sev = SEVERITY.get(r.get("collision_severity"), 0)
    cells[(cx, cy)]["x"].append([round(x - cx * CELL), round(y - cy * CELL), t.hour, sev, int(dark(t)), cause_ix[cause], at])
    n_crash[sev] += 1

# ---------- per neighborhood, for the city-wide view: km of street, police reports (people, drugs), pedestrians hit ----------
hood_of = {}   # a corner's neighborhood: that of the first block that ends there
for b in blocks:
    for n in b["nd"]:
        if "nh" in b:
            hood_of.setdefault(n, b["nh"])
    hood_of.setdefault(b["id"], b.get("nh"))
per_hood = [[0.0, 0, 0, 0] for _ in hoods]
for b in blocks:
    if "nh" in b:
        ln = b["g"][0]
        per_hood[b["nh"]][0] += sum(math.dist(ln[i:i + 2], ln[i + 2:i + 4]) for i in range(0, len(ln) - 2, 2)) * PX_M / 1000
for n in counts:
    if hood_of.get(n) is not None:
        per_hood[hood_of[n]][1] += total(n, PERSON)
        per_hood[hood_of[n]][2] += total(n, DRUGS)
for cell in cells.values():
    for c in cell["x"]:
        if hood_of.get(c[6]) is not None:
            per_hood[hood_of[c[6]]][3] += 1
per_hood = [[round(km, 1), p, d, x] for km, p, d, x in per_hood]

# ---------- speed and red-light cameras ----------
cams = []
speed = collections.defaultdict(lambda: dict(cit=0, warn=0, days=set()))
rows = load("speedcams")
s_start = str((max(when(r["date"]) for r in rows) - WINDOW).date())
for r in rows:
    if r["date"][:10] <= s_start:
        continue
    s = speed[r["site_id"]]
    s.update(loc=r["location"], mph=int(float(r.get("posted_speed") or 0)), at=(float(r["longitude"]), float(r["latitude"])))
    s["cit"] += int(float(r.get("issued_citations") or 0))
    s["warn"] += int(float(r.get("issued_warnings") or 0))
    s["days"].add(r["date"][:10])
for s in speed.values():
    m = re.match(r"(NB|SB|EB|WB)\s+(\d+)\s+(.*)", s["loc"])
    label = f"{nice(m[3])} near {m[2]}" if m else nice(s["loc"])
    x, y = z17(*s["at"])
    cams.append(["speed", round(x), round(y), label, DIRS.get(m[1], "") if m else "", s["mph"], s["cit"], s["warn"],
                 min(s["days"]), max(s["days"])])
red = collections.defaultdict(lambda: dict(n=0, dirs=collections.Counter(), months=set()))
rows = load("redlight")
last = max(r["month"][:7] for r in rows)
r_start = f"{int(last[:4]) - 2}-{last[5:]}"   # the 24 months up to the latest
for r in rows:
    if r["month"][:7] <= r_start:
        continue
    c = red[r["intersection"]]
    c["at"] = r["point"]["coordinates"]
    c["n"] += int(float(r.get("count") or 0))
    c["dirs"][r.get("directions_enforced") or ""] += int(float(r.get("count") or 0))
    c["months"].add(r["month"][:7])
for name, c in red.items():
    x, y = z17(*c["at"])
    cams.append(["red", round(x), round(y), name.replace("So. ", "South "), "; ".join(d for d, _ in c["dirs"].most_common() if d),
                 0, c["n"], 0, min(c["months"]), max(c["months"])])

# ---------- write ----------
shutil.rmtree(OUT, ignore_errors=True)
(OUT / "cells").mkdir(parents=True)
sizes = []
for (cx, cy), cell in cells.items():
    body = json.dumps(cell, separators=(",", ":"))
    (OUT / "cells" / f"{cx}_{cy}.json").write_text(body)
    sizes.append(len(body))
cell_keys = sorted(f"{cx}_{cy}" for cx, cy in cells)
cell_ix = {k: i for i, k in enumerate(cell_keys)}
streets = [[] for _ in names]
for s, cnn, h, key, f, t, sd in index:
    en = [cnn, h, cell_ix[key], f, t] + ([sd] if sd else [])
    while len(en) > 3 and en[-1] is None:   # empty ends left off
        en.pop()
    streets[s].append(en)
day = lambda t: str(t.date())
meta = dict(built=str(date.today()), streets_as_of=max(r.get("data_as_of", "") for r in segs)[:10], cell=CELL,
            blocks=len(index), names=names, hoods=hoods, hood_stats=per_hood, cells=cell_keys,
            police=dict(start=day(p_start + timedelta(days=1)), end=day(p_end), kinds=KINDS, people=PERSON, drugs=DRUGS),
            crashes=dict(start=day(c_start + timedelta(days=1)), end=day(c_end), causes=causes,
                         severity=["complaint of pain", "visible injury", "severe injury", "killed"]),
            cams=sorted(cams, key=lambda c: (c[0], c[3])))
(OUT / "index.json").write_text(json.dumps(meta, separators=(",", ":")))
(OUT / "streets.json").write_text(json.dumps(streets, separators=(",", ":")))
sizes.sort()
print(f"{len(index):,} blocks on {len(set(s for s, *_ in index)):,} streets, {len(hin):,} on the High Injury Network")
print(f"police {day(p_start)}..{day(p_end)}: {len(seen):,} reports of the kinds shown at {len(counts):,} corners"
      f" ({off_map:,} rows with no corner on the map); per kind:",
      {KINDS[k]: sum(v[2 * k] + v[2 * k + 1] for v in counts.values()) for k in range(len(KINDS))})
print(f"pedestrian crashes {day(c_start)}..{day(c_end)}: {sum(n_crash.values()):,}, by severity {dict(sorted(n_crash.items()))}")
print(f"cameras: {sum(c[0] == 'speed' for c in cams)} speed, {sum(c[0] == 'red' for c in cams)} red light")
print(f"{len(cells)} cells, {sum(sizes) / 2**20:.1f} MB; median {sizes[len(sizes) // 2] / 1024:.0f} KB, "
      f"largest {sizes[-1] / 1024:.0f} KB; index.json {(OUT / 'index.json').stat().st_size / 1024:.0f} KB, "
      f"streets.json {(OUT / 'streets.json').stat().st_size / 1024:.0f} KB")
