#!/usr/bin/env python3
"""The page's data: data/raw/ (from fetch_sf.py) -> docs/data/ (not committed).

A block is one centerline segment, keyed by its CNN (centerline network number), the key the city's parking, sweeping
and crash data all share. Its name is the street and its hundred block, from the segment's address ranges, and it runs
between the cross streets at its two ends.

The blocks are split into map cells of about 1 km (as on LA Street Rules), so the page only loads the few cells it's
showing:
  cells/{x}_{y}.json  the blocks in one cell: [{id: CNN, s: street name, h: hundred block (none without addresses),
                      g: lines in zoom-17 pixels from the cell's corner, x: cross streets, sd: 1 or 2 when it carries
                      only the odd or even house numbers, nh: neighborhood}]
  index.json          loads with the page: names and neighborhoods (the cells refer to them by number) and which
                      cells exist
  streets.json        loads on the first search: for each street name, its blocks as
                      [CNN, hundred, cell, from street, to street, odd/even side]

So far only the blocks themselves; PLAN.md §4 lists what each block gets next.
"""
import collections
import json
import math
import re
import shutil
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "docs" / "data"
N17 = 2 ** 17 * 256
CELL = 1024   # map cell edge in zoom-17 Web Mercator pixels (1 px is about 0.95 m in SF)

# kept: streets, park roads (Golden Gate Park, the Presidio, Fort Mason), Treasure and Yerba Buena Islands, Hunters Point
# Shipyard, pedestrian streets. Left out: freeways and ramps, paper streets, private roads and lots, unpaved rights of
# way, addressing-only segments.
LAYERS = {"STREETS", "STREETS_TI", "STREETS_YBI", "STREETS_HUNTERSP", "STREETS_PEDESTRI",
          "PARKS", "PARKS_NPS_PRESIDIO", "PARKS_NPS_FTMASON"}
SKIP_CLASS = {"1", "6"}   # freeway, freeway ramp
SPECIAL = {"OFARRELL": "O'Farrell", "OREILLY": "O'Reilly", "OSHAUGHNESSY": "O'Shaughnessy", "MACARTHUR": "MacArthur",
           "GGP": "GGP", "SFGH": "SFGH", "UCSF": "UCSF", "USF": "USF"}


def z17(lon, lat):
    r = math.radians(lat)
    return (lon + 180) / 360 * N17, (1 - math.log(math.tan(r) + 1 / math.cos(r)) / math.pi) / 2 * N17


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


rows = json.loads((RAW / "streets.json").read_text())
segs = [r for r in rows if r.get("layer") in LAYERS and r.get("classcode") not in SKIP_CLASS and "line" in r
        and not re.search(r"\bRAMP\b|PARKING LOT", r.get("streetname", ""))]
hoods = sorted({r["analysis_neighborhood"] for r in segs if r.get("analysis_neighborhood")})
hood_ix = {h: i for i, h in enumerate(hoods)}
names, name_ix = [], {}


def nix(name):
    if name not in name_ix:
        name_ix[name] = len(names)
        names.append(name)
    return name_ix[name]


shutil.rmtree(OUT, ignore_errors=True)
(OUT / "cells").mkdir(parents=True)
cells = collections.defaultdict(list)
index = []   # (street, CNN, hundred, cell, from street)
for r in sorted(segs, key=lambda r: (r.get("streetname_gc") or r["streetname"], hundred(r) or 0, int(r["cnn"]))):
    pts = [z17(lon, lat) for lon, lat in r["line"]["coordinates"]]
    cx, cy = int(sum(p[0] for p in pts) / len(pts) // CELL), int(sum(p[1] for p in pts) / len(pts) // CELL)
    line = []
    for x, y in pts:
        p = [round(x - cx * CELL), round(y - cy * CELL)]
        if line[-2:] != p:
            line += p
    if len(line) < 4:
        continue
    s, h, sd = nix(nice(r.get("streetname_gc") or r["streetname"])), hundred(r), side(r)
    f, t = (nix(c) if (c := cross(r.get(k))) else None for k in ("f_st", "t_st"))
    x = [i for i in (f, t) if i is not None]
    rec = dict(id=int(r["cnn"]), s=s, g=[line], x=x)
    if h is not None:
        rec["h"] = h
    if sd:
        rec["sd"] = sd
    if r.get("analysis_neighborhood"):
        rec["nh"] = hood_ix[r["analysis_neighborhood"]]
    cells[(cx, cy)].append(rec)
    index.append((s, rec["id"], h, f"{cx}_{cy}", f, t, sd))

sizes = []
for (cx, cy), recs in cells.items():
    body = json.dumps(recs, separators=(",", ":"))
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
as_of = max(r.get("data_as_of", "") for r in segs)[:10]
meta = dict(built=str(date.today()), streets_as_of=as_of, cell=CELL, blocks=len(index), names=names, hoods=hoods,
            cells=cell_keys)
(OUT / "index.json").write_text(json.dumps(meta, separators=(",", ":")))
(OUT / "streets.json").write_text(json.dumps(streets, separators=(",", ":")))
sizes.sort()
print(f"{len(index):,} blocks on {len(set(s for s, *_ in index)):,} streets in {len(cells)} cells, "
      f"{sum(sizes) / 2**20:.1f} MB; median {sizes[len(sizes) // 2] / 1024:.0f} KB, largest {sizes[-1] / 1024:.0f} KB; "
      f"index.json {(OUT / 'index.json').stat().st_size / 1024:.0f} KB, "
      f"streets.json {(OUT / 'streets.json').stat().st_size / 1024:.0f} KB")
