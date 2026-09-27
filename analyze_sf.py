#!/usr/bin/env python3
"""The page's data: data/raw/ (from fetch_sf.py) -> docs/data/ (not committed).

A block is one centerline segment, keyed by its CNN (centerline network number), the key the city's parking, sweeping
and crash data all share. Its name is the street and its hundred block, from the segment's address ranges, and it runs
between the cross streets at its two ends. Its corners are the intersections (node CNNs) at those ends.

Dated data covers the two years up to each dataset's latest date (WINDOW). Every crash and police report is also marked
daylight or after dark, from the sun's times in San Francisco on its date.

The driving side works per block side: left (0) and right (1) of the block's line, facing along it, as the city's data
has them. Parking tickets are placed by the address written on them (the block whose house numbers include it, the side
by odd or even), street cleaning by the schedule's own CNN and side, meters and the curb-line parking regulations by
geometry. The page works out "can I park here?" from these rules itself, for any time.

The map is split into cells of about 1 km (as on LA Street Rules), so the page only loads the few cells it's showing:
  cells/{x}_{y}.json  one cell: {b: blocks, c: corners, x: crashes}. Positions are zoom-17 pixels from the cell's corner.
                      block  {id: CNN, s: street name, h: hundred block (none without addresses), g: lines,
                              x: cross streets, sd: 1 or 2 when it carries only the odd or even house numbers,
                              nh: neighborhood, nd: its two corners' CNNs, hin: 1 on the High Injury Network,
                              pr: {kind: percentile}, how its corners' police reports rank among all blocks,
                              sn: its sides' names (North, SouthEast...), lp: the left side's house numbers (1 odd, 2 even),
                              w: street cleaning per side, with how often a posted day got a ticket; wn: street-cleaning
                              tickets per side; rg: time limits, permit areas and no-parking zones per side; mt: meters per
                              side (cap color, spaces, their week); tn: tickets (all, left, right); tk: per kind of ticket,
                              the count, busiest weekday, usual hours and share on weekdays; hh: a kind's tickets by the
                              half hour; see the comments where each is made}
                      corner {id: node CNN, p: [x, y], k: police reports per kind, daylight and after dark in turn,
                              q: calls to police per group (CALL_GROUPS in fetch_sf.py), the same way; only with calls,
                              kt, qt: when those reports (the walking kinds, WALK_KINDS) and calls happened, per kind or
                              group, as [half hour, count, half hour, count, ...] with the half hours of the day 0-47 in
                              daylight and 48-95 after dark; only with any}
                      crash  [x, y, hour, severity, after dark, cause, where (the block's or the corner's CNN)]
  index.json          loads with the page: names, neighborhoods (with their km of street, police reports about people
                      and about drugs, and pedestrians hit), which cells exist, the time windows, the kinds of police
                      report and crash causes (by number), the speed and red-light cameras, the kinds of parking ticket
                      (with their fine now and a note on each), the regulation kinds and meter caps, the driving summary
                      (tickets across the city: per kind, by hour and weekday, the blocks with the most street-cleaning
                      tickets), and the walking summary
                      (the city as a whole: when and how people walking were hit, around the places visitors go, the
                      corners with the most, totals per year, the High Injury Network's share of the streets
                      and of the people walking hit, and how the card's circle ranks among intersections)
  streets.json        loads on the first search: for each street name, its blocks as
                      [CNN, hundred, cell, from street, to street, odd/even side]
"""
import bisect
import collections
import csv
import json
import math
import re
import shutil
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from fetch_sf import CALL_GROUPS

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
KINDS = ["Robbery", "Assault and other violence", "Pickpocketing and purse snatching", "Weapons", "Drug offenses",
         "Car break-ins"]
VIOLENCE = {"Assault", "Homicide", "Rape", "Sex Offense"}
CAR_BREAKIN = {"Larceny - From Vehicle", "Theft From Vehicle", "Larceny - Auto Parts"}
PERSON = [0, 1, 2, 3]   # the kinds counted as reports of harm to people on the street
DRUGS = [4]
CARS = 5   # car break-ins: the driving side's
WALK_KINDS = PERSON + DRUGS   # the kinds on the walking card, which get their times of day (kt)

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
         "Illegal operation of motorized scooter": "Motorized scooter ridden against the rules",
         "Failure of driver or bicyclist to exercise due care for safety of pedestrian on roadway":
             "Driver didn't take care around someone walking in the road",
         "Duty to stop when involved in accident with injury or death": "Hit and run: the driver didn't stop",
         "Violation of right-of-way - left turn": "Driver turning left didn't yield",
         "Entering highway from alley or driveway": "Driver pulling out of a driveway or alley didn't yield",
         "Operating vehicle or bicycle on sidewalk prohibited": "Car or bicycle on the sidewalk",
         "Driver or bicyclist failure to obey signs or signals": "Driver didn't obey a sign or signal",
         "Pedestrian on roadway prohibited": "Person walking in the road where it isn't allowed",
         "Lane straddling or failure to use specified lanes": "Driver straddled lanes or used the wrong lane",
         "Illegal U-turn in business district": "Illegal U-turn",
         "Failure to yield right-of-way on sidewalk to pedestrian": "Driver crossing the sidewalk didn't yield",
         "Red signal - driver or bicyclist responsibilities with right turn":
             "Driver turning right on a red light didn't stop or yield",
         "Green signal - driver or bicyclist responsibilities": "Driver turning on a green light didn't yield",
         "Violating special traffic control markers": "Driver didn't follow the turn markings",
         "Turn at intersection from wrong position": "Driver turned from the wrong lane",
         "Wrong way driving": "Driving the wrong way",
         "Going against one-way traffic patterns": "Driving the wrong way",
         "Violation of right-of-way or uncontrolled intersection": "Driver didn't yield at a corner without signals or signs",
         "Failure to keep to right side of road": "Driver didn't keep to the right",
         "Driving under influence of alcohol and/or drugs": "Driving under the influence",
         "Driving under influence causing injury": "Driving under the influence",
         "Pedestrian prohibited in bicycle lane": "Person walking in a bike lane",
         "Overtaking and passing unsafely": "Unsafe passing",
         "Following too closely prohibited": "Following too closely",
         "Signal required before turning or changing lanes": "Driver didn't signal a turn or lane change",
         "Assault and Battery": "Assault",
         "Unknown": "Not recorded", "": "Not recorded"}
DIRS = {"NB": "northbound", "SB": "southbound", "EB": "eastbound", "WB": "westbound"}
# what the person walking was doing, from the crash report
ACTION = {"Crossing in Crosswalk at Intersection": "Crossing in a crosswalk at an intersection",
          "Crossing in Crosswalk Not at Intersection": "Crossing in a mid-block crosswalk",
          "Crossing Not in Crosswalk": "Crossing outside a crosswalk",
          "In Road, Including Shoulder": "In the road, not crossing",
          "Not in Road": "Not in the road",
          "Approaching/Leaving School Bus": "Getting on or off a school bus"}

# the walking side counts what's within some distance of a point: on the card, around the spot picked (RADII, 200 m to
# start); in the summary, PLACE_M around places people walk to, visitors especially
PLACE_M = 200
RADII = range(100, 501, 50)   # the sizes the card's circle can be, in metres (the page's slider)
PLACES = [("Union Square", 37.78795, -122.40750), ("Powell St cable car turnaround", 37.78480, -122.40780),
          ("Chinatown (Portsmouth Square)", 37.79480, -122.40530), ("North Beach (Washington Square)", 37.80070, -122.41010),
          ("Coit Tower", 37.80240, -122.40580), ("Fisherman's Wharf", 37.80800, -122.41620), ("Pier 39", 37.80870, -122.40980),
          ("Ghirardelli Square", 37.80580, -122.42290), ("Lombard St's crooked block", 37.80210, -122.41880),
          ("Ferry Building", 37.79550, -122.39370), ("Salesforce Transit Center", 37.78950, -122.39640),
          ("Moscone Center", 37.78430, -122.40120), ("Oracle Park", 37.77860, -122.38930), ("Chase Center", 37.76800, -122.38770),
          ("City Hall", 37.77930, -122.41920), ("Alamo Square", 37.77630, -122.43460), ("Japantown", 37.78510, -122.42980),
          ("Haight and Ashbury", 37.77000, -122.44690), ("Castro and Market", 37.76250, -122.43510),
          ("Dolores Park", 37.75960, -122.42690), ("16th St Mission station", 37.76500, -122.41960),
          ("24th St Mission station", 37.75220, -122.41840), ("Palace of Fine Arts", 37.80290, -122.44840),
          ("de Young Museum", 37.77150, -122.46870)]
TREND_FROM = 2015   # the first year of pedestrians hit in the per-year chart (police reports start in 2018)

# the driving side. A block's sides are left (0) and right (1) of its centerline, facing from its first end to its last,
# as the city's own data has them: the left side carries the left address range, and the sweeping schedule's L and R
# agree (96% of street-cleaning tickets placed by house number fall on their side's posted day).
SWEEP_DAYS = {"Mon": 0, "Tues": 1, "Wed": 2, "Thu": 3, "Fri": 4, "Sat": 5, "Sun": 6, "Holiday": 7}   # 7: its holiday hours
CHART_MIN = 10   # tickets of one kind on a block before it gets its own time-of-day chart
# SFMTA's short descriptions -> plain names. None: not a parking ticket (the feed also carries Muni fare and conduct
# citations, written at stops and stations). Anything not listed is "Other".
T_KIND = {"STR CLEAN": "Street cleaning", "MTR OUT DT": "Meter not paid", "METER DTN": "Meter not paid",
          "OT MTR PK": "Over the meter's time limit", "RES/OT": "Over the time limit, no area permit",
          "OT OUT DT": "Over the time limit", "OT PK DT": "Over the time limit", "PK OVR 72H": "Parked over 72 hours",
          "YEL ZONE": "Yellow zone", "TRK ZONE": "Truck loading zone", "WHITE ZONE": "White zone", "GREEN ZONE": "Green zone",
          "RED ZONE": "Red zone", "PK PHB OTD": "Tow-away zone", "PRK PROHIB": "Tow-away zone",
          "RESTRICTED": "Against a posted restriction", "NO PRK ZN": "No-parking zone", "PKG PROHIB": "No-parking zone",
          "TMP PK RES": "Temporary no-parking sign", "CNSTR TEMP": "Construction zone", "DRIVEWAY": "Blocking a driveway",
          "DBL PARK": "Double parking", "DBL PKG": "Double parking", "ON SIDEWLK": "On the sidewalk",
          "PRK GRADE": "Wheels not curbed on a hill", 'OVR 18 " C': "Too far from the curb", 'OVR 18 \\" C': "Too far from the curb",
          "ONEWAY RD": "Facing the wrong way", "WRG WY PKG": "Facing the wrong way", "ANGLE PARK": "Angle parked",
          "N/ W/I SPC": "Outside the marked space", "FIRE HYD": "Fire hydrant", "PK FR LN": "Fire lane",
          "15FT FR ST": "Fire station entrance", "20FT XWALK": "Within 20 ft of a crosswalk", "PK/CROSS": "In a crosswalk",
          "PK INTER": "In an intersection", "BLK/INTER": "Blocking an intersection", "OBSTRCT TF": "Blocking traffic",
          "OBSTRCT TR": "Blocking traffic", "OBSTR PRMT": "Blocking traffic", "BUS ZONE": "Bus zone",
          "TRNST ONLY": "Transit-only lane", "SAFE/RED Z": "Transit safety zone", "SAFETY ZN": "Transit safety zone",
          "SAFE ZONE": "Transit safety zone", "BLK BIKE L": "In a bike lane", "BIC PATHS": "In a bike lane",
          "PK STANDS": "In a taxi or bus stand", "WHLCHR ACC": "Blocking wheelchair access", "3 FT WLCHR": "Blocking wheelchair access",
          "B ZN NO DP": "Blue zone", "BL ZNE BLK": "Blue zone", "B ZN XHTCH": "Blue zone", "HANDI ZONE": "Blue zone",
          "ON ST LST": "Disabled placard misuse", "OFF ST LST": "Disabled placard misuse", "ON STREET": "Disabled placard misuse",
          "OFF STREET": "Disabled placard misuse", "ILG PRK BL": "Disabled placard misuse", "MC PRKING": "Motorcycle parking",
          "ONSTCARSH": "Car-share space", "CHGEV S": "EV charging space", "BLKEV ST": "EV charging space",
          "BK CHG BAY": "EV charging space", "LARGE VEHI": "Oversized vehicle", "100FT OVER": "Oversized vehicle",
          "CM VEH RES": "Commercial vehicle rules", "MED DIVIDE": "On a median", "PUB PROP": "On public property",
          "SCH/PUB GD": "On public property", "FACIL CRG": "City garage or lot", "FCL BLK SP": "City garage or lot",
          "FCL OT PK": "City garage or lot", "NO PLATES": "No license plate shown", "PLT LEF/AT": "License plate not shown right",
          "PLATECOVER": "License plate not shown right", "FAILRPLPLA": "License plate not shown right",
          "ALT PLATES": "License plate not shown right", "PLT F/R": "License plate not shown right",
          "IMP DPL PL": "License plate not shown right", "NOPL/PRDSP": "License plate not shown right",
          "NO EV REG": "Expired registration", "REG TABS": "Expired registration", "V5204": "Expired registration",
          "ENG IDLING": "Engine idling", "FOR SALE": "For-sale sign", "RR TRACKS": "Railroad tracks", "": "Not recorded",
          **{k: "In a park, against its rules" for k in ("NOPRK 10P6", "MAR GRN PK", "NO PERMIT", "ILL PKG", "DISOB SIGN",
                                                       "SGTSEE BUS", "COMM VEH", "PRK ON RGT", "CAR ALM 15", "ALM TME 15",
                                                       "WRK ON CAR", "FIRETRAIL")},
          **{k: None for k in ("NO VIOL", "FAIL DISPL", "UNAUTHFARE", "CNTRFTFARE", "FARE EVASI", "FR/EVA/YTH", "SMOKNG ETC",
                               "DISTURBAN", "SOUNDEQUIP", "YOUTHMSCON", "SELL/PEDDL", "LIVESTKLR", "SKARBG/ROL", "CONV W/ OP",
                               "URIN/DFECT", "CBL CAR TR")}}
# one plain line for each kind, shown when a reader opens it on the card
T_NOTE = {"Street cleaning": "Parked on that side during its posted street-cleaning hours.",
          "Meter not paid": "The meter wasn't paid, or had run out.",
          "Over the meter's time limit": "Stayed at a meter longer than its time limit, even if paid.",
          "Over the time limit, no area permit": "Stayed longer than the posted time limit in a residential permit area, without that area's permit.",
          "Over the time limit": "Stayed longer than the posted time limit.",
          "Parked over 72 hours": "Left in the same place on the street for more than 72 hours, which isn't allowed anywhere in the city.",
          "Yellow zone": "At a yellow curb or meter, kept for commercial vehicles loading during its posted hours.",
          "Truck loading zone": "In a space kept for trucks loading.",
          "White zone": "At a white curb, kept for picking up and dropping off people during its posted hours.",
          "Green zone": "At a green curb or meter, which has a short time limit, often 15 or 30 minutes.",
          "Red zone": "At a red curb, where stopping isn't allowed at any time.",
          "Tow-away zone": "Parked in a posted tow-away zone during its hours, like a lane kept clear at rush hour.",
          "Against a posted restriction": "Parked against what a posted sign allows there.",
          "No-parking zone": "Parked where a sign says no parking.",
          "Temporary no-parking sign": "Parked where temporary no-parking signs were put up, for a move, an event or street work.",
          "Construction zone": "Parked in a zone kept clear for construction.",
          "Wheels not curbed on a hill": "On a hill, the front wheels weren't turned to the curb.",
          "Too far from the curb": "More than 18 inches from the curb.",
          "Facing the wrong way": "Parked facing against traffic.",
          "Angle parked": "Parked at an angle where parking has to be parallel to the curb, or the other way round.",
          "Outside the marked space": "Not inside the painted lines of a space.",
          "Within 20 ft of a crosswalk": "Parked within 20 feet of a crosswalk, which California law has not allowed since 2024.",
          "Blocking traffic": "Stopped where it blocked traffic.",
          "Bus zone": "In the curb space kept clear for buses at a stop.",
          "Transit-only lane": "In a lane kept for buses and streetcars.",
          "Transit safety zone": "In the marked area where people get on and off a streetcar.",
          "In a taxi or bus stand": "In a curb space kept for taxis, buses or other vehicles for hire.",
          "Blocking wheelchair access": "Blocking a curb ramp or the space next to it that wheelchairs use.",
          "Blue zone": "In a blue space for people with disabilities, or its striped area, without a disabled placard or plates.",
          "Disabled placard misuse": "Using a disabled placard or plates that weren't valid, or weren't the driver's.",
          "Motorcycle parking": "In a space kept for motorcycles.",
          "Car-share space": "In a space kept for a car-share car.",
          "EV charging space": "In a space kept for electric cars while they charge.",
          "Oversized vehicle": "A vehicle over the posted size, where oversized vehicles aren't allowed.",
          "Commercial vehicle rules": "A commercial vehicle parked against the rules for one.",
          "On public property": "Parked on public grounds, such as a school's.",
          "City garage or lot": "In a city garage or lot: not paid, over its limit, or against its rules.",
          "In a park, against its rules": "Against a city park's parking rules, like no parking from 10 pm to 6 am.",
          "No license plate shown": "No license plate on the car where it has to be.",
          "License plate not shown right": "The plate covered, not lit, or not mounted where it has to be.",
          "Expired registration": "The car's registration was out of date.",
          "Other": "Rules the page doesn't name separately, each written only a few times in the city.",
          "Not recorded": "The rule wasn't recorded on the ticket."}
# parking regulations (hi6h-neyh): the kinds, in the page's words
REG_OF = {"time limited": 0, "no parking any time": 1, "no parking anytime": 1, "no stopping": 1, "limited no parking": 2,
          "no overnight parking": 3, "pay or permit": 4, "paid + permit": 4, "government permit": 5, "no oversized vehicles": 6}
REG_KINDS = ["Time limit", "No parking any time", "No parking at set hours", "No overnight parking", "Pay or permit",
             "Government permits only", "No oversized vehicles"]
REG_DAYS = {"M-F": 0b0011111, "M-SA": 0b0111111, "M-S": 0b0111111, "M-SU": 0b1111111, "M, TH": 0b0001001, "SA": 0b0100000}
# meter caps: what the space is for (grey is for anyone; the others are kept for someone during their hours)
CAPS = ["Grey", "Green", "Yellow", "Red", "Black", "Brown", "Blue", "White"]
# a meter's day in pieces: paid (for what its cap is for), paid and open to all (a yellow or red meter's other hours),
# tow-away, and kept for another use (an alternate piece with no rate, like a commuter shuttle stop at rush hour)
METER_TYPE = {"OP": 0, "ALT": 1, "TOW": 2}


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


def half_hour(t):
    """The half hour of the day a local time falls in, 0-47, plus 48 after dark."""
    return t.hour * 2 + t.minute // 30 + 48 * dark(t)


def pairs(counter):
    """{half hour: count} -> [half hour, count, ...] in order of the half hour."""
    return [v for h in sorted(counter) for v in (h, counter[h])]


def times_field(per_kind, n_kinds):
    """A corner's times per kind or group (kt, qt): one list of pairs each, with the empty ones at the end left off."""
    out = [pairs(per_kind.get(k, {})) for k in range(n_kinds)]
    while out and not out[-1]:
        out.pop()
    return out


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
pol_times = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))   # corner -> kind -> half hour
pol_hour = [[0, 0] for _ in range(24)]   # reports about people, and about drugs, by hour of the day (each report once)
pol_month = [[0, 0] for _ in range(12)]   # reports about people by month of the year, daylight and after dark (each once)
seen, seen_g, off_map = set(), set(), 0
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
    if sub in CAR_BREAKIN:
        kinds.add(CARS)
    for k in kinds:
        if (r["incident_number"], k) not in seen:
            seen.add((r["incident_number"], k))
            counts[n][2 * k + dark(t)] += 1
            if k in WALK_KINDS:
                pol_times[n][k][half_hour(t)] += 1
    for g, ks in enumerate((PERSON, DRUGS)):
        if kinds & set(ks) and (r["incident_number"], g) not in seen_g:
            seen_g.add((r["incident_number"], g))
            pol_hour[t.hour][g] += 1
            if g == 0:
                pol_month[t.month - 1][dark(t)] += 1
# ---------- calls to police from the public, per corner and group, daylight and after dark ----------
calls = load("calls")
q_end = max(when(r["received_datetime"]) for r in calls)
q_start = q_end - WINDOW
group_of = {c: g for g, (_, cs) in enumerate(CALL_GROUPS) for c in cs}
calls_at = collections.defaultdict(lambda: [0] * (2 * len(CALL_GROUPS)))
call_times = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))   # corner -> group -> half hour
n_calls, calls_off = 0, 0
for r in calls:
    t, n = when(r["received_datetime"]), node(r.get("intersection_id"))
    if t <= q_start:
        continue
    if n not in corner_at:   # sensitive calls come without a place
        calls_off += 1
        continue
    calls_at[n][2 * group_of[r["call_type_final"]] + dark(t)] += 1
    call_times[n][group_of[r["call_type_final"]]][half_hour(t)] += 1
    n_calls += 1

for n in set(counts) | set(calls_at):
    x, y = corner_at[n]
    cx, cy = cell_of(x, y)
    c = dict(id=n, p=[round(x - cx * CELL), round(y - cy * CELL)], k=counts[n] if n in counts else [0] * (2 * len(KINDS)))
    if n in calls_at:
        c["q"] = calls_at[n]
    if kt := times_field(pol_times.get(n, {}), len(KINDS)):
        c["kt"] = kt
    if qt := times_field(call_times.get(n, {}), len(CALL_GROUPS)):
        c["qt"] = qt
    cells[(cx, cy)]["c"].append(c)

# how each block's corners rank among all blocks: people, drug offenses, car break-ins (any time of day)
total = lambda n, ks: sum(counts[n][2 * k] + counts[n][2 * k + 1] for k in ks) if n in counts else 0
calls_total = lambda n: sum(calls_at[n]) if n in calls_at else 0
for key, ks in (("people", PERSON), ("drugs", DRUGS), ("cars", [CARS]), ("calls", None)):
    vals = {b["id"]: sum(total(n, ks) if ks else calls_total(n) for n in b["nd"]) for b in blocks}
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
hits = []   # every pedestrian crash in the window: (x, y, time, severity, after dark, cause, where, what the person was doing)
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
    hits.append((x, y, t, sev, int(dark(t)), cause_ix[cause], at, ACTION.get(r.get("ped_action"), "Not recorded")))

# ---------- per neighborhood, for the city-wide view: km of street, police reports (people, drugs), pedestrians hit ----------
hood_of = {}   # a corner's neighborhood: that of the first block that ends there
for b in blocks:
    for n in b["nd"]:
        if "nh" in b:
            hood_of.setdefault(n, b["nh"])
    hood_of.setdefault(b["id"], b.get("nh"))
def block_km(b):
    ln = b["g"][0]
    return sum(math.dist(ln[i:i + 2], ln[i + 2:i + 4]) for i in range(0, len(ln) - 2, 2)) * PX_M / 1000


per_hood = [[0.0, 0, 0, 0] for _ in hoods]
for b in blocks:
    if "nh" in b:
        per_hood[b["nh"]][0] += block_km(b)
for n in counts:
    if hood_of.get(n) is not None:
        per_hood[hood_of[n]][1] += total(n, PERSON)
        per_hood[hood_of[n]][2] += total(n, DRUGS)
for cell in cells.values():
    for c in cell["x"]:
        if hood_of.get(c[6]) is not None:
            per_hood[hood_of[c[6]]][3] += 1
per_hood = [[round(km, 1), p, d, x] for km, p, d, x in per_hood]

# ---------- the walking summary: the city as a whole ----------
# the streets that meet at each corner; an intersection is where two or more differently named streets meet
at_node = collections.defaultdict(dict)   # node -> {street name: a block of that street ending there}
for b in blocks:
    for n in b["nd"]:
        at_node[n].setdefault(names[b["s"]], b["id"])
crossings = [n for n in corner_at if len(at_node[n]) >= 2]
# what's around a point: pedestrians hit, of them badly hurt or killed, police reports about people, about drugs, calls
# to police (any time of day)
points = [(x, y, 1, int(sev >= 2), 0, 0, 0) for x, y, t, sev, *_ in hits]
points += [(*corner_at[n], 0, 0, total(n, PERSON), total(n, DRUGS), calls_total(n)) for n in set(counts) | set(calls_at)]


def counter(m):
    """A function that counts what's within m metres of a point, from a grid of cells m wide."""
    r = m / PX_M
    grid = collections.defaultdict(list)
    for pt in points:
        grid[(int(pt[0] // r), int(pt[1] // r))].append(pt)

    def around(x, y):
        s = [0] * 5
        for i in range(int(x // r) - 1, int(x // r) + 2):
            for j in range(int(y // r) - 1, int(y // r) + 2):
                for px, py, *v in grid.get((i, j), ()):
                    if (px - x) ** 2 + (py - y) ** 2 <= r * r:
                        for k in range(5):
                            s[k] += v[k]
        return s
    return around


# each place is compared with the same circle around every intersection: the share of intersections with fewer
around = counter(PLACE_M)
circles = [around(*corner_at[n]) for n in crossings]
ranked = [sorted(c[k] for c in circles) for k in range(4)]
rank = lambda k, v: 100 * bisect.bisect_left(ranked[k], v) // len(circles)
places = []
for name, lat, lon in PLACES:
    x, y = z17(lon, lat)
    s = around(x, y)[:4]
    places.append([name, round(x), round(y), *s, rank(0, s[0]), rank(2, s[2]), rank(3, s[3])])


def cuts(m):
    """For the card's circle at m metres: per count, the value at each percent of the intersections, so the page can
    tell the share with fewer. At least p% have fewer than v when q[p - 1] < v, for p from 1 to 99 (as rank(), rounded
    down)."""
    count = counter(m)
    circ = [count(*corner_at[n]) for n in crossings]
    q = {}
    for key, k in (("hit", 0), ("people", 2), ("drugs", 3), ("calls", 4)):
        v = sorted(c[k] for c in circ)
        q[key] = [v[math.ceil(len(v) * p / 100) - 1] for p in range(1, 100)]
    return q


circle_q = {m: cuts(m) for m in RADII}

# the corners where the most people walking were hit: the top five, and any tied with the fifth (at most ten)
by_corner = collections.defaultdict(lambda: [0, 0])
for x, y, t, sev, dk, c, at, act in hits:
    if at in corner_at and len(at_node[at]) >= 2:
        by_corner[at][0] += 1
        by_corner[at][1] += sev >= 2
top = sorted(by_corner.items(), key=lambda kv: (-kv[1][0], -kv[1][1]))
cut = top[4][1][0] if len(top) >= 5 else 0
top_corners = []
for n, (hit, bad) in top[:10]:
    if hit < cut:
        break
    streets = sorted(at_node[n])[:3]
    x, y = corner_at[n]
    top_corners.append([" & ".join(streets), n, at_node[n][streets[0]], round(x), round(y), hit, bad])

# pedestrians hit by month of the year and hour of the day, in daylight and after dark; how badly hurt; what they were
# doing; the causes
mh = [[[0, 0] for _ in range(24)] for _ in range(12)]
sev_dark = [[0, 0] for _ in range(4)]
for x, y, t, sev, dk, c, at, act in hits:
    mh[t.month - 1][t.hour][dk] += 1
    sev_dark[sev][dk] += 1
actions = collections.Counter(h[7] for h in hits).most_common()
# the High Injury Network's share of the streets, and of the people walking hit on its blocks or at their corners:
# [blocks on it, km on it, km in all, hit there, hit in all, badly hurt or killed there, badly hurt or killed in all]
hin_at = {b["id"] for b in blocks if "hin" in b} | {n for b in blocks if "hin" in b for n in b["nd"]}
hin_share = [sum("hin" in b for b in blocks), round(sum(block_km(b) for b in blocks if "hin" in b)),
             round(sum(block_km(b) for b in blocks)), sum(h[6] in hin_at for h in hits), len(hits),
             sum(h[6] in hin_at and h[3] >= 2 for h in hits), sum(h[3] >= 2 for h in hits)]
top_causes = [[c, n] for c, n in collections.Counter(h[5] for h in hits).most_common(6)]

# totals per year across the city (from fetch_sf.py's trends): full years only
trends = load("trends")
per_year = lambda rows, end, first, keys: [[int(r["y"]), *(int(float(r.get(k) or 0)) for k in keys)] for r in rows
                                           if r.get("y") and first <= int(r["y"]) < (end + timedelta(days=1)).year]
summary = dict(place_m=PLACE_M, intersections=len(crossings), circle_q=circle_q, places=places, corners=top_corners, mh=mh, sev=sev_dark,
               actions=actions, causes=top_causes, pol_hour=pol_hour, pol_month=pol_month, hin=hin_share,
               years=dict(hit=per_year(trends["hit"], c_end, TREND_FROM, ("n", "killed")),
                          people=per_year(trends["people"], p_end, 0, ("n",)), drugs=per_year(trends["drugs"], p_end, 0, ("n",))))

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

# ---------- the driving side: parking rules per block side, and the tickets written there ----------
row_of = {int(r["cnn"]): r for r in segs}
geo = {b["id"]: [z17(lon, lat) for lon, lat in row_of[b["id"]]["line"]["coordinates"]] for b in blocks}
rec_of = {b["id"]: b for b in blocks}
G = 64   # grid cell for finding the nearest block, in zoom-17 pixels
seg_grid = collections.defaultdict(list)
for cnn, pts in geo.items():
    for i in range(len(pts) - 1):
        (ax, ay), (bx, by) = pts[i], pts[i + 1]
        for gx in range(int(min(ax, bx) // G), int(max(ax, bx) // G) + 1):
            for gy in range(int(min(ay, by) // G), int(max(ay, by) // G) + 1):
                seg_grid[(gx, gy)].append((cnn, ax, ay, bx, by))


def to_seg(x, y, ax, ay, bx, by):
    """Distance from a point to a piece of line, and which side of it the point is on (0 left, 1 right, facing from a
    to b; zoom-17 pixels grow southward, so left has a negative cross product)."""
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    t = max(0, min(1, ((x - ax) * dx + (y - ay) * dy) / L)) if L else 0
    return math.hypot(x - ax - t * dx, y - ay - t * dy), int(dx * (y - ay) - dy * (x - ax) > 0)


def nearest(x, y, maxd, ok=None, heading=None):
    """The nearest block within maxd pixels (and allowed by ok(cnn)), as (distance, CNN, side); with a heading
    (dx, dy), only a piece of line within about 25 degrees of parallel to it."""
    best = (maxd, None, 0)
    for gx in range(int(x // G) - 1, int(x // G) + 2):
        for gy in range(int(y // G) - 1, int(y // G) + 2):
            for cnn, ax, ay, bx, by in seg_grid.get((gx, gy), ()):
                if ok and not ok(cnn):
                    continue
                if heading:
                    hx, hy = heading
                    dx, dy = bx - ax, by - ay
                    if abs(hx * dx + hy * dy) < .9 * math.hypot(hx, hy) * math.hypot(dx, dy):
                        continue
                d, s = to_seg(x, y, ax, ay, bx, by)
                if d < best[0]:
                    best = (d, cnn, s)
    return best


def near_line(cnn, x, y):
    """How far a point is from a block's line, and which side of it it's on."""
    pts = geo[cnn]
    return min(to_seg(x, y, *pts[i], *pts[i + 1]) for i in range(len(pts) - 1))


side_of = lambda cnn, x, y: near_line(cnn, x, y)[1]


def compass(dx, dy):
    """The direction a vector points in on the map (y grows southward): North, NorthEast, ..., as the sweeping schedule
    names sides; one of the four main ones unless it's more than 22.5 degrees off."""
    a = math.degrees(math.atan2(dx, -dy)) % 360
    return ["North", "NorthEast", "East", "SouthEast", "South", "SouthWest", "West", "NorthWest"][int((a + 22.5) // 45) % 8]


def minutes(v, end=False):
    """'800' -> 480, '2400' -> 0 (or 1440 at the end of a span), '4:30' -> 270."""
    v = str(v).strip()
    h, m = (int(p) for p in v.split(":")) if ":" in v else divmod(int(float(v)), 100)
    t = h * 60 + m
    return 1440 if end and t in (0, 1440) else t % 1440


def sf_holidays(y):
    """San Francisco's city holidays in a year, observed dates (a Saturday one moves to the Friday, a Sunday one to the
    Monday); the first three are the ones SFMTA enforces nothing on."""
    def obs(d):
        return d - timedelta(days=1) if d.weekday() == 5 else d + timedelta(days=1) if d.weekday() == 6 else d

    def nth(month, wd, n):   # the nth weekday wd of a month; n = -1 for the last
        if n > 0:
            d = date(y, month, 1)
            return d + timedelta(days=(wd - d.weekday()) % 7 + 7 * (n - 1))
        d = date(y, month + 1, 1) - timedelta(days=1)
        return d - timedelta(days=(d.weekday() - wd) % 7)
    thanks = nth(11, 3, 4)
    return [obs(date(y, 1, 1)), thanks, obs(date(y, 12, 25)), nth(1, 0, 3), nth(2, 0, 3), nth(5, 0, -1),
            obs(date(y, 6, 19)), obs(date(y, 7, 4)), nth(9, 0, 1), nth(10, 0, 2), obs(date(y, 11, 11)), thanks + timedelta(days=1)]


# the sweeping schedule still lists some segments by CNNs the centerlines have since retired (two segments merged into
# one): those rows go on the block their line runs along, their side flipped if the old line ran the other way
sweep_rows = load("sweeping")
moved = {}
for cnn in {int(r["cnn"]) for r in sweep_rows} - set(rec_of):
    line = next((r["line"]["coordinates"] for r in sweep_rows if int(r["cnn"]) == cnn and r.get("line")), None)
    if not line:
        continue
    pts, got = [z17(lon, lat) for lon, lat in line], collections.Counter()
    for i in range(len(pts) - 1):
        (ax, ay), (bx, by) = pts[i], pts[i + 1]
        for f in (.25, .5, .75):
            got[nearest(ax + f * (bx - ax), ay + f * (by - ay), 8, heading=(bx - ax, by - ay))[1]] += math.dist(pts[i], pts[i + 1])
    got.pop(None, None)
    if got:
        new = got.most_common(1)[0][0]
        (ax, ay), (bx, by), (cx, cy), (dx, dy) = pts[0], pts[-1], geo[new][0], geo[new][-1]
        moved[cnn] = (new, (bx - ax) * (dx - cx) + (by - ay) * (dy - cy) < 0)
for r in sweep_rows:
    if int(r["cnn"]) in moved:
        new, flip = moved[int(r["cnn"])]
        r["cnn"], r["cnnrightleft"] = str(new), {"L": "R", "R": "L"}[r["cnnrightleft"]] if flip else r["cnnrightleft"]
print(f"street cleaning: {len(moved)} retired segments placed on today's blocks")

# side names: the sweeping schedule's where it has one, else the direction the side faces
named = collections.defaultdict(collections.Counter)
for r in sweep_rows:
    if r.get("blockside"):
        named[(int(r["cnn"]), 0 if r["cnnrightleft"] == "L" else 1)][r["blockside"]] += 1
for b in blocks:
    pts = geo[b["id"]]
    dx, dy = pts[-1][0] - pts[0][0], pts[-1][1] - pts[0][1]
    own = [named[(b["id"], s)].most_common(1)[0][0] if named[(b["id"], s)] else None for s in (0, 1)]
    b["sn"] = [own[0] or compass(dy, -dx), own[1] or compass(-dy, dx)]
    r = row_of[b["id"]]
    nums = [int(float(r.get(f) or 0)) for f in ("lf_fadd", "lf_toadd", "rt_fadd", "rt_toadd")]
    lp, rp = next((n % 2 for n in nums[:2] if n), None), next((n % 2 for n in nums[2:] if n), None)
    b["_par"] = (lp, rp)   # the parity of each side's house numbers
    if lp is not None or rp is not None:
        b["lp"] = 2 - (lp if lp is not None else 1 - rp)   # the left side's house numbers: 1 odd, 2 even

# ---------- tickets: SFMTA parking citations, placed on a block by the address written on them ----------
ADDR = re.compile(r"^(\d+)\s+(.+)$")
skey = lambda s: " ".join(re.sub(r"[^A-Z0-9 ]", "", s.upper()).split())
by_addr = collections.defaultdict(list)   # street -> [(lowest house number, highest, CNN)]
name_of = {}
for cnn in geo:
    r = row_of[cnn]
    name_of[cnn] = skey(r["streetname"])
    nums = [int(float(r.get(f) or 0)) for f in ("lf_fadd", "lf_toadd", "rt_fadd", "rt_toadd")]
    if any(nums):
        by_addr[name_of[cnn]].append((min(n for n in nums if n), max(nums), cnn))
tickets = []   # (CNN, side or None, kind, fine, time)
t_kinds, t_kix = [], {}
t_off, t_other = collections.Counter(), collections.Counter()
t_last = datetime.combine(date.today(), datetime.min.time())
for path in sorted((RAW / "tickets").glob("*.csv")):
    with path.open(newline="") as f:
        for r in csv.DictReader(f):
            t = when(r["citation_issued_datetime"])
            if t >= t_last:   # dated ahead: a typo
                continue
            desc = r["violation_desc"].strip()
            kind = T_KIND.get(desc, "Other")
            if kind is None:
                continue
            if desc not in T_KIND:
                t_other[desc] += 1
            m = ADDR.match(r["citation_location"].strip())
            num, street = (int(m[1]), skey(m[2])) if m else (None, skey(r["citation_location"]))
            xy = z17(float(r["longitude"]), float(r["latitude"])) if r["latitude"] and r["longitude"] else None
            cnn = None
            # the block whose address range holds the house number (the nearest one when several do); else the nearest
            # block of that street, or of any street, near the ticket's coordinates
            if num is not None and street in by_addr:
                cands = [c for lo, hi, c in by_addr[street] if lo <= num <= hi]
                if cands:
                    cnn = cands[0] if len(cands) == 1 or not xy else min(cands, key=lambda c: near_line(c, *xy)[0])
            if cnn is None and xy:
                cnn = nearest(*xy, 60, (lambda k: name_of[k] == street) if street in by_addr else None)[1] or nearest(*xy, 25)[1]
            if cnn is None:
                t_off["no block"] += 1
                continue
            lp, rp = rec_of[cnn]["_par"]
            # the side: by the house number's parity where the block has house numbers, else by the coordinates
            side = ((0 if num % 2 == lp else 1) if lp is not None else (1 if num % 2 == rp else 0)) if num is not None and (lp, rp) != (None, None) \
                else side_of(cnn, *xy) if xy else None
            if kind not in t_kix:
                t_kix[kind] = len(t_kinds)
                t_kinds.append(kind)
            fine = float(r["fine_amount"] or 0)
            tickets.append((cnn, side, t_kix[kind], fine, t))
# the city fills in the last few days over the next week: the window ends on the last day with at least half the usual
# tickets for its weekday
daily = collections.Counter(t[4].date() for t in tickets)
usual = {wd: sorted(n for d, n in daily.items() if d.weekday() == wd)[sum(d.weekday() == wd for d in daily) // 2] for wd in range(7)}
t_end = datetime.combine(max(d for d, n in daily.items() if n >= usual[d.weekday()] / 2), datetime.max.time())
t_start = t_end - WINDOW
tickets = [t for t in tickets if t[4] <= t_end]
tickets = [t for t in tickets if t[4] > t_start]
print(f"tickets {(t_start + timedelta(days=1)).date()}..{t_end.date()}: {len(tickets):,} on blocks ({t_off['no block']:,} placed nowhere);"
      f" {sum(t[1] is None for t in tickets):,} without a side; not named: {t_other.most_common(8)}")

SWEEP = t_kix["Street cleaning"]
# the days street cleaning was off citywide: city holidays, and any day with hardly any street-cleaning tickets
per_day = collections.Counter(t[4].date() for t in tickets if t[2] == SWEEP)
hols = {d for y in range(t_start.year, t_end.year + 1) for d in sf_holidays(y)}
typical = {wd: sorted(n for d, n in per_day.items() if d.weekday() == wd)[len([1 for d in per_day if d.weekday() == wd]) // 2]
           for wd in range(7) if any(d.weekday() == wd for d in per_day)}
all_days = [t_start.date() + timedelta(days=i) for i in range(1, (t_end.date() - t_start.date()).days + 1)]
off_days = {d for d in all_days if d in hols or per_day[d] < .1 * typical.get(d.weekday(), 0)}
print(f"street cleaning off citywide on {len(off_days)} days:", sorted(str(d) for d in off_days if d not in hols))

# ---------- street cleaning, per side: the posted day, hours and weeks, and how often a posted day got a ticket ----------
sweep_groups = collections.defaultdict(lambda: collections.defaultdict(int))   # (CNN, side) -> (from, to, weeks, holidays) -> days
weeks_of = lambda r: sum(1 << i for i in range(5) if r.get(f"week{i + 1}") == "1")
# a day's "swept on holidays too" says nothing more when the side has holiday hours at the same time
hol_rows = {(r["cnn"], r["cnnrightleft"], r["fromhour"], r["tohour"], weeks_of(r)) for r in sweep_rows if r.get("weekday") == "Holiday"}
for r in sweep_rows:
    cnn = int(r["cnn"])
    if cnn not in rec_of or r.get("weekday") not in SWEEP_DAYS:
        continue
    weeks = weeks_of(r)
    hol = r.get("holidays") == "1" and (r["cnn"], r["cnnrightleft"], r["fromhour"], r["tohour"], weeks) not in hol_rows
    key = (int(r["fromhour"]) * 60, int(r["tohour"]) * 60, weeks, int(hol))
    sweep_groups[(cnn, 0 if r["cnnrightleft"] == "L" else 1)][key] |= 1 << SWEEP_DAYS[r["weekday"]]
sweep_t = collections.defaultdict(list)   # (CNN, side) -> the times of its street-cleaning tickets
for cnn, side, k, fine, t in tickets:
    if k == SWEEP and side is not None:
        sweep_t[(cnn, side)].append(t)
posted_days = {}   # (days, weeks) -> the posted days in the window, city holidays and days off left out
for (cnn, side), groups in sweep_groups.items():
    b = rec_of[cnn]
    for (t0, t1, weeks, hol), days in sorted(groups.items(), key=lambda g: (g[0][0], g[1])):
        if (days, weeks) not in posted_days:
            posted_days[(days, weeks)] = {d for d in all_days if days >> d.weekday() & 1 and weeks >> ((d.day - 1) // 7) & 1
                                          and d not in off_days}
        posted = posted_days[(days, weeks)]
        hit = [t for t in sweep_t[(cnn, side)] if t.date() in posted and t0 <= t.hour * 60 + t.minute <= t1]
        # [side, days (bit 0 Monday ... 6 Sunday, 7 its holiday hours), from, to (minutes), weeks of the month (bit 0 the
        #  1st), swept on holidays too, posted days in the window, days with a ticket in the posted hours, those tickets]
        b.setdefault("w", []).append([side, days, t0, t1, weeks, hol, len(posted), len({t.date() for t in hit}), len(hit)])
for b in blocks:
    n = [len(sweep_t[(b["id"], s)]) for s in (0, 1)]
    if any(n):
        b["wn"] = n   # street-cleaning tickets on each side, at any time

# ---------- parking regulations: time limits, permit areas, no parking. Lines along the curb, placed by geometry ----------
reg_len = collections.defaultdict(float)   # (CNN, side, regulation) -> length along it, in pixels
STEP = 4
for r in load("regs"):
    kind = REG_OF.get((r.get("regulation") or "").strip().lower())
    if kind is None or not r.get("shape"):
        continue
    days = REG_DAYS.get((r.get("days") or "").strip().upper(), 0b1111111)
    b0, b1 = r.get("hrs_begin"), r.get("hrs_end")
    t0, t1 = (minutes(b0), minutes(b1, True)) if b0 not in (None, "") and b1 not in (None, "") else (0, 1440)
    if t0 == t1 % 1440:
        t0, t1 = 0, 1440
    lim = round(float(r.get("hrlimit") or 0) * 60)
    areas = ",".join(a for a in (r.get(f"rpparea{i}") for i in (1, 2, 3)) if a and a.strip() not in ("", "0"))
    reg = (kind, days, t0, t1, lim if kind == 0 else 0, areas if kind in (0, 4) else "")
    for part in r["shape"]["coordinates"]:
        pts = [z17(lon, lat) for lon, lat in part]
        for i in range(len(pts) - 1):
            (ax, ay), (bx, by) = pts[i], pts[i + 1]
            L = math.hypot(bx - ax, by - ay)
            for k in range(max(1, int(L // STEP))):
                f = (k + .5) / max(1, int(L // STEP))
                d, cnn, side = nearest(ax + f * (bx - ax), ay + f * (by - ay), 20, heading=(bx - ax, by - ay))
                if cnn:
                    reg_len[(cnn, side, reg)] += L / max(1, int(L // STEP))
blen = {cnn: sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)) for cnn, pts in geo.items()}
for (cnn, side, reg), L in sorted(reg_len.items(), key=lambda kv: (kv[0][0], kv[0][1], kv[0][2])):
    if L >= max(8, .25 * blen[cnn]):   # a regulation that runs along a good part of that side, not one that only reaches it
        # [side, kind (REG_KINDS), days (bit 0 Monday), from, to (minutes; to < from runs past midnight), time limit
        #  (minutes), permit areas exempt from it]
        rec_of[cnn].setdefault("rg", []).append([side, *reg])

# ---------- meters: each space's side, and its hours, rates and time limits (the meter's policy) ----------
policy = collections.defaultdict(list)   # post -> [(day, from, to, type, rate in cents, time limit)]
DOW2 = {"Mo": 0, "Tu": 1, "We": 2, "Th": 3, "Fr": 4, "Sa": 5, "Su": 6}
with (RAW / "policies.csv").open(newline="") as f:
    for r in csv.DictReader(f):
        if r["scheduletype"] in METER_TYPE and r["dayofweek"] in DOW2:
            rate = round(float(r["hourlyrate"] or 0) * 100)
            kind = 3 if r["scheduletype"] == "ALT" and not rate else METER_TYPE[r["scheduletype"]]
            policy[r["postid"]].append((DOW2[r["dayofweek"]], minutes(r["starttime"]), minutes(r["endtime"], True), kind,
                                        rate, int(float(r["timelimitminutes"] or 0))))


def schedule(pieces):
    """A meter's week as [[days, from, to, type, rate, limit], ...], the days a piece is the same merged into one."""
    out = collections.defaultdict(int)
    for d, *rest in pieces:
        out[tuple(rest)] |= 1 << d
    return [[days, *p] for p, days in sorted(out.items())]


spaces = collections.Counter()   # (CNN, side, cap, schedule) -> spaces
m_off = collections.Counter()
for r in load("meters"):
    if r.get("active_meter_flag") not in ("M", "P") or not r.get("latitude"):
        continue
    x, y = z17(float(r["longitude"]), float(r["latitude"]))
    cnn = node(r.get("street_seg_ctrln_id"))
    if cnn not in rec_of:
        cnn = nearest(x, y, 20)[1]
    if cnn is None:
        m_off["no block"] += 1
        continue
    cap = CAPS.index(r["cap_color"]) if r.get("cap_color") in CAPS else 0
    spaces[(cnn, side_of(cnn, x, y), cap, json.dumps(schedule(policy.get(r["post_id"], []))))] += 1
for (cnn, side, cap, sch), n in sorted(spaces.items()):
    # [side, cap (CAPS), spaces, their week: [[days, from, to, type (0 paid, 1 paid and open to all, 2 tow-away, 3 kept
    #  for another use), rate (cents an hour), time limit (minutes)], ...]; an empty week: no hours in the city's list]
    rec_of[cnn].setdefault("mt", []).append([side, cap, n, json.loads(sch)])


def usual_hours(mins, share=.5):
    """Clock-hour ranges holding the busiest `share` of tickets, as [[start, end], ...] in minutes (as on LA Street
    Rules): the fewest hours that cover it, runs split by one quiet hour joined, the two biggest runs kept."""
    c = [0] * 24
    for m in mins:
        c[m // 60 % 24] += 1
    pick = [False] * 24
    for hr in sorted(range(24), key=lambda h: -c[h]):
        if sum(c[h] for h in range(24) if pick[h]) >= share * sum(c):
            break
        pick[hr] = True
    pick = [p or (pick[h - 1] and pick[(h + 1) % 24]) for h, p in enumerate(pick)]
    if all(pick):
        return [[0, 1440]]
    s0 = pick.index(False)
    runs, a = [], None
    for i in range(s0, s0 + 25):
        if i < s0 + 24 and pick[i % 24]:
            a = i if a is None else a
        elif a is not None:
            runs.append((sum(c[j % 24] for j in range(a, i)), a % 24, i - a))
            a = None
    runs = sorted(sorted(runs, reverse=True)[:2], key=lambda r: r[1])
    return [[h * 60, (h + n) * 60] for _, h, n in runs]


# ---------- what gets ticketed, per block ----------
# the fine for each kind now: the median in the last 90 days across the city (fines go up; warnings carry none)
k_fine = collections.defaultdict(list)
for cnn, side, k, fine, t in tickets:
    if fine > 0 and t > t_end - timedelta(days=90):
        k_fine[k].append(fine)
fine_now = [round(sorted(k_fine[k])[len(k_fine[k]) // 2]) if k_fine[k] else 0 for k in range(len(t_kinds))]
per_kind = collections.defaultdict(list)   # (CNN, kind) -> [(fine, time)]
t_side = collections.defaultdict(lambda: [0, 0, 0])
for cnn, side, k, fine, t in tickets:
    per_kind[(cnn, k)].append((fine, t))
    t_side[cnn][0] += 1
    if side is not None:
        t_side[cnn][1 + side] += 1
for (cnn, k), ts in per_kind.items():
    dows = collections.Counter(t.weekday() for _, t in ts)
    mins = [t.hour * 60 + t.minute for _, t in ts]
    # [kind, tickets, busiest weekday (0 Monday), usual hours, share on weekdays]
    rec_of[cnn].setdefault("tk", []).append([k, len(ts),
                                             min(dows, key=lambda d: (-dows[d], d)), usual_hours(mins),
                                             round(sum(dows[d] for d in range(5)) / len(ts), 2)])
    if len(ts) >= CHART_MIN:   # by the half hour: [kind, first half hour, counts from there]
        hh = collections.Counter(m // 30 for m in mins)
        rec_of[cnn].setdefault("hh", []).append([k, min(hh)] + [hh[j] for j in range(min(hh), max(hh) + 1)])
for b in blocks:
    b.pop("_par", None)
    if b["id"] in t_side:
        b["tn"] = t_side[b["id"]]   # tickets: all, on the left side, on the right (the rest had no side)
    if "tk" in b:
        b["tk"].sort(key=lambda t: (-t[1], t[0]))
# the driving summary, for the city as a whole: tickets per kind, by hour and weekday (street cleaning and the rest), how
# often a posted cleaning day got a ticket, and the blocks with the most street-cleaning tickets
k_n = collections.Counter(t[2] for t in tickets)
t_hour, t_dow = [[0, 0] for _ in range(24)], [[0, 0] for _ in range(7)]
for cnn, side, k, fine, t in tickets:
    t_hour[t.hour][k != SWEEP] += 1
    t_dow[t.weekday()][k != SWEEP] += 1
posted_all = sum(w[6] for b in blocks for w in b.get("w", []))
hit_all = sum(w[7] for b in blocks for w in b.get("w", []))
top_sweep = []
for b in sorted(blocks, key=lambda b: -sum(b.get("wn", [0]))):
    if len(top_sweep) == 10:
        break
    pts = geo[b["id"]]
    key = "_".join(str(int(v // CELL)) for v in (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)))
    top_sweep.append([names[b["s"]] + (f", {b['h'] or '1–99'} block" if "h" in b else ""), b["id"], key, sum(b["wn"])])
drive_summary = dict(kinds=[[k, n] for k, n in k_n.most_common()],
                     hour=t_hour, dow=t_dow, sweep_days=[posted_all, hit_all], top_sweep=top_sweep,
                     meters=sum(spaces.values()), sweep_blocks=sum(1 for b in blocks if "w" in b))
print(f"street cleaning on {sum(1 for b in blocks if 'w' in b):,} blocks; regulations on {sum(1 for b in blocks if 'rg' in b):,};"
      f" meters on {sum(1 for b in blocks if 'mt' in b):,} ({sum(spaces.values()):,} spaces, {m_off['no block']} placed nowhere);"
      f" tickets on {len(t_side):,}")

# ---------- city garages and lots: at the main entrance, or the middle of the block the city lists them on ----------
OWNER = {"SFMTA": "SFMTA", "PORT": "the Port of San Francisco", "RPD": "SF Recreation and Parks", "CALTRANS": "Caltrans"}
SUFFIX = {"STREET": "ST", "AVENUE": "AVE", "BOULEVARD": "BLVD", "DRIVE": "DR"}
garage_rows = load("garages")
shared = collections.Counter(r.get("street_address") for r in garage_rows)
garages = []
for r in garage_rows:
    m = ADDR.match((r.get("street_address") or "").strip())
    street = " ".join(SUFFIX.get(w, w) for w in skey(m[2]).split()) if m else ""
    at = [c for lo, hi, c in by_addr.get(street, []) if lo <= int(m[1]) <= hi] if m else []
    if r.get("main_entrance_lat"):
        x, y = z17(float(r["main_entrance_long"]), float(r["main_entrance_lat"]))
    elif node(r.get("street_seg_ctrln_id")) in geo or at and shared[r["street_address"]] == 1:   # an address several share is a placeholder
        pts = geo[node(r.get("street_seg_ctrln_id")) if node(r.get("street_seg_ctrln_id")) in geo else at[0]]
        x, y = pts[len(pts) // 2]
    else:
        continue
    # [name, x, y, garage (1) or lot (0), run by, spaces, services, website, where]
    garages.append([r["facility_name"].strip().replace("OFarrell", "O'Farrell").replace("St. Marys", "St. Mary's"), round(x), round(y), int(r.get("facility_type") == "G"),
                    OWNER.get((r.get("owner") or "").upper(), r.get("owner") or ""), int(float(r.get("capacity") or 0)),
                    r.get("services") or "", r.get("web_site") or "", (r.get("location") or r.get("street_address") or "").strip()])
print(f"city garages and lots: {len(garages)} placed, of {len(load('garages'))}")

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
            police=dict(start=day(p_start + timedelta(days=1)), end=day(p_end), n=len(seen), kinds=KINDS, people=PERSON, drugs=DRUGS, cars=CARS),
            calls=dict(start=day(q_start + timedelta(days=1)), end=day(q_end), n=n_calls, groups=[g for g, _ in CALL_GROUPS]),
            crashes=dict(start=day(c_start + timedelta(days=1)), end=day(c_end), n=sum(n_crash.values()), causes=causes,
                         severity=["complaint of pain", "visible injury", "severe injury", "killed"]),
            cams=sorted(cams, key=lambda c: (c[0], c[3])), summary=summary,
            tickets=dict(start=day(t_start + timedelta(days=1)), end=day(t_end), n=len(tickets), kinds=t_kinds, fines=fine_now,
                         notes=[T_NOTE.get(k, "") for k in t_kinds], sweep=SWEEP, chart_min=CHART_MIN,
                         off=sorted(str(d) for d in off_days), city=drive_summary),
            regs=REG_KINDS, caps=CAPS, garages=sorted(garages))
(OUT / "index.json").write_text(json.dumps(meta, separators=(",", ":")))
(OUT / "streets.json").write_text(json.dumps(streets, separators=(",", ":")))
sizes.sort()
print(f"{len(index):,} blocks on {len(set(s for s, *_ in index)):,} streets, {len(hin):,} on the High Injury Network")
print(f"police {day(p_start)}..{day(p_end)}: {len(seen):,} reports of the kinds shown at {len(counts):,} corners"
      f" ({off_map:,} rows with no corner on the map); per kind:",
      {KINDS[k]: sum(v[2 * k] + v[2 * k + 1] for v in counts.values()) for k in range(len(KINDS))})
print(f"calls to police {day(q_start)}..{day(q_end)}: {n_calls:,} at {len(calls_at):,} corners ({calls_off:,} without a place); per group:",
      {g: sum(v[2 * i] + v[2 * i + 1] for v in calls_at.values()) for i, (g, _) in enumerate(CALL_GROUPS)})
print(f"pedestrian crashes {day(c_start)}..{day(c_end)}: {sum(n_crash.values()):,}, by severity {dict(sorted(n_crash.items()))}")
print(f"cameras: {sum(c[0] == 'speed' for c in cams)} speed, {sum(c[0] == 'red' for c in cams)} red light")
print(f"summary: {len(places)} places, {len(top_corners)} top corners (from {cut} hit), {len(crossings):,} intersections;"
      f" {len(json.dumps(summary, separators=(',', ':'))) / 1024:.1f} KB")
print(f"{len(cells)} cells, {sum(sizes) / 2**20:.1f} MB; median {sizes[len(sizes) // 2] / 1024:.0f} KB, "
      f"largest {sizes[-1] / 1024:.0f} KB; index.json {(OUT / 'index.json').stat().st_size / 1024:.0f} KB, "
      f"streets.json {(OUT / 'streets.json').stat().st_size / 1024:.0f} KB")
