# SF Streets — plan

Working title. A map of San Francisco in the style of [LA Street Rules](https://citina.github.io/ticket-clock/streets/),
but the page changes with who's asking:

- **I'm driving** → *Can I park here, until when, and what gets ticketed on this block?*
- **I'm walking** → *Around a spot I pick, what gets reported to police, what do people call police about, and how
  often are people walking hit by cars, when and why?*

Same map, same search box, same card, but different layers, legend, time control, card contents and method text for
each mode. The mode lives in the URL (`#drive` / `#walk`) so either view can be linked. Both sides are built and live at
https://citina.github.io/sf-streets/; this file says how, and what's still open.

---

## 1. What carries over from ticket-clock, and what's different in SF

**Reused as-is or nearly so**

- The hand-written page, no build step, no map library: SVG block lines over OpenStreetMap tiles, pan, zoom, a
  two-finger turn with a compass back to north, "Show blocks near me", and the search box
  (`ticket-clock/docs/streets/index.html`). Jumps stay north up, as on LA Street Rules since ticket-clock 121ced6.
- Design tokens, type (Barlow / Barlow Condensed / IBM Plex Mono), mast with sister sites, panel/card styles, method as
  closed rows, About with sister-site cards, disclaimer. Styles match ticket-clock `9204808` (2026-09-25): five text
  sizes (12 / 14 / 15 / 16 / 18.5 px), no light-gray text (`--ink-3` only for non-text marks), 16px text inputs, a red
  "your location" dot, tooltips for a mouse only.
- The driving card's wording and layout from LA Street Rules: the drawn street-cleaning sign, "No street-cleaning
  schedule found…", "No meters appear in SFMTA's inventory…", ticket kinds as rows that open to a note and a half-hour
  dot chart (5 before "Show all N kinds"), and the closing line "This card is worked out from SFMTA citations recorded
  since … Ticket history may not include every rule that applies here."
- Data split into ~1 km map cells (`data/cells/{key}.json`) so the page only loads what's on screen, plus `index.json`
  and `streets.json` for search. Weekly GitHub Action → release asset → Pages.

**Different in SF**

- **Everything shares one street key, the CNN** (centerline network number): sweeping, crashes, closures, meters, the
  High Injury Network. The street-cleaning schedule and meters come per block side; so does the address on a ticket.
- **Tickets are placed by their address, not their coordinates.** The coordinates are address points about 11 m off the
  street, and at corners they fall nearer the cross street. The house number picks the block (the one whose address range
  holds it) and odd or even picks the side; 98% of tickets place. Checked against the schedule: 96% of street-cleaning
  tickets fall on the posted day of the side they're placed on.
- **The sweeping schedule is published per side with week flags** (`yhqp-riqs`), so nothing about the schedule is
  inferred from tickets; tickets are the evidence of how often it's enforced.
- **The parking-ticket feed also carries Muni fare and conduct citations** (written at stops and stations); they're left
  out.

---

## 2. Data

See **[DATA_SOURCES.md](DATA_SOURCES.md)**: what's in use and for what, and what was looked at and left out. All from
data.sf.gov, plus OpenStreetMap for the map images.

---

## 3. The page (`docs/index.html`)

```
mast            SF Streets · (sister sites)                       Updated Sep 26 · About  (the day the data was built)
h1 + lede       changes with mode, with a link to the summary
MODE SWITCH     [ 🚗 I'm driving ]  [ 🚶 I'm walking ]
find bar        drive: Show blocks near me · walk: Show what's around me · search street / address / neighborhood
time control    drive: When [Now | pick day+time]  For [1 hr 2 hr 4 hr Overnight]   (SF time; overnight = until 8 am)
                walk:  When [Any | Daylight | After dark]  Within [100–500 m slider, 200 m to start]
┌───────────────── map ─────────────────┐ ┌──────── card ────────┐
│ layer chips (per mode)                │ │ title, between, hood │
│ OSM tiles + block lines               │ │ cards (per mode)     │
│ zoom / fit SF / north                 │ │                      │
└───────────────────────────────────────┘ └──────────────────────┘
legend (per mode)                         (beside the map, the card's top is level with the map's)
summary         drive: parking tickets across the city · walk: walking in the city as a whole
method          one closed row per topic, per mode
about · disclaimer
```

**Driving card** (built 2026-09-26)

1. **Can I park here?** For the time and stay picked, each side: *free* (until when, and what comes next), *pay* (the
   cost of the stay, the rate, the limit, when meters stop), *move by* (street cleaning, a tow-away, a time limit or a
   closure starting during the stay) or *no parking now*. Both sides in one box when they agree. Worked out in the page
   from the rules in the cell file (§4), so any day and time works.
2. **Street cleaning** — each side's posted sign, drawn; the next two dates; "Ticketed on X% of cleaning days (N of M)
   in the past two years".
3. **Meters, time limits, permits** — metered spaces by cap color, when they're paid, rates and limits, tow-away hours,
   time limits with their permit area, no-parking zones; the meter rate at the time picked.
4. **Closures and temporary signs** — this block's street closures and temporary no-parking signs, today and the next
   two weeks (loaded live, §4).
5. **Tickets written here** — kinds, the fine now, the usual day and time; tap for a note and the half-hour chart
   (street cleaning shows the posted time behind the dots).
6. **City garages & lots nearby**, **Car break-ins at its corners**, **Cameras near here**.

Parts 2 to 6 are rows, closed until tapped, each with its short answer under its name (the next cleaning day, metered
spaces and limits, closures listed, tickets and the most common kind, the nearest garage, break-ins, cameras); rows
opened stay open for the next block (2026-09-27). The ticket count left the card's header for the tickets row.

Sides are named by direction alone ("East side"), never odd or even; the picked block has a letter on the map on each
side (N, E, SE...) so the reader can tell which is which. Before a block is picked the card is one line, not a list of
what it will hold. After a search on a phone (the card is below the map), the message above the map gives the answer
too ("Valencia St, 500 block: both sides free until 6 am · See the card ↓") and follows the block picked; any other
message replaces it. Ranks read "Top 4% of SF blocks" (and "Fewer than most SF blocks" under the median). The card
ends with one line on its sources and a link to the method (Citina, 2026-09-27).

**On a phone** (2026-09-27) the map starts on the first screen (about 470 px down on a 375×812 screen, from 790): short
ledes, the location button as its icon and "Near me" beside the search box, one-line notes for SF time / overnight and
after dark, and the layer chips in one row that scrolls sideways. The location privacy line shows when the button is pressed, and
the disclaimer's "What the page loads" keeps the long version.

How "Can I park here?" decides:

- A side's rules: street cleaning, meters (the general grey or green ones with the most spaces, else yellow or red, else
  any), time limits and pay-or-permit, no-parking zones, closures and temporary signs.
- A side with meters *and* a posted time limit has two kinds of space (the time limit doesn't apply at a meter): the
  card works out both and shows the better one, saying which ("At a space without a meter").
- Tow-away or other-use hours on only some of a side's meters, no parking any time on part of a side, some lanes closed,
  or temporary signs along part of a side: a warning line, not "no parking" for the whole side.
- A time limit counts from arrival or from when it starts, across back-to-back pieces with the same limit. 72 hours is
  the longest any stay can be.
- Holidays, from SFMTA's schedule: nothing but tow-away and no-parking-any-time on New Year's Day, Thanksgiving and
  Christmas; on the other nine city holidays, meters, holiday street cleaning and tow-away still run, time limits,
  daytime street cleaning and commuter-shuttle hours don't. Closures and temporary signs apply every day.
- A meter piece marked "alternate" with no rate (often commuter-shuttle hours) is "not for general parking (see the
  sign)", never free.

**Walking card** (built 2026-09-26)

The walking side counts what's in a circle, not on a block: 100 to 500 m (the "Within" slider, 200 m to start) around a
spot you tap on the map, a searched address (the middle of its block), your location, or a place or corner in the
summary. The link carries the spot and size (`#walk/@37.76411,-122.42181/250m`) but never your own location. Every rank
compares the circle with one the same size around each of the city's 7,550 intersections (`circle_q` in the summary).

1. **Reported to police** — robbery, assault and other violence, pickpocketing, weapons, drug offenses, most first; tap a
   kind for what it covers and, with 10 or more, its half-hour dot chart; ranks; an hour chart and how many after dark.
2. **Calls to police** — fights and assaults, a gun or knife, robbery, threats and harassment, the same way.
3. **People walking hit** — "16 people walking hit in the past two years", the number big with its words after it; the
   High Injury Network streets through the circle (with a "?" to its explanation), the rank, the hour chart, after
   dark, the top causes in plain words. No count of the badly hurt or killed for a circle, or for a corner in the
   summary: so few people could point to someone (Citina, 2026-09-27). Citywide totals keep them.

Like the driving card, each is a row closed until tapped, its count under its name ("Calls to police — 1,526 in the
past two years"); the rows opened stay open for the next spot. Ranks read "Top 2% of SF intersections"; each row ends
with one short note (reports are placed at the nearest corner; a call is what someone reported, not what police found),
and the dates and the rest are in the method (Citina, 2026-09-27). Before a spot is picked the card is one line ("See
what's within 200 m of it: police reports, calls to police and people walking hit"), as on the driving side.

**Map layers**

- Drive: *Can I park?* (on; each side of a block its own line, about 4.5 m off the middle, colored free / pay / move /
  no parking for the time and stay picked) · *Closures* (on; streets closed at the time picked, dashed) · *City garages
  & lots* · *Speed & red-light cameras* (on) · *Car break-ins*. Only the map cells in view are recolored when the time
  or stay changes. *Tickets per block* was dropped 2026-09-26 (too crowded); tickets stay on the card and in the summary.
- Legend labels are short (Citina, 2026-09-27): Free · Pay at the meter · Time-limited · No parking; "Violence & robbery
  reports", "Calls to police", "Bigger = more". What to tap is said on the map ("Tap a street to pick a block", "Tap the
  map to pick a spot") until something is picked, then the tag names the neighborhood.
- Walk: High Injury Network · violence and robbery (on) · drug offenses · calls to police (off until tapped, so busy
  areas don't pile up marks; 2026-09-27), with neighborhoods shaded while the whole city shows, and the card's circle on
  top. On a phone the map's hint is just "Pick a neighborhood".

**Wording rules** (Citina)

- Never claim 100% unless it's literally 100% (ranks are rounded down).
- Labels say literally what they mean ("no street-cleaning schedule found", "city-run garages", "free for your stay"
  means free of the rules in the city's lists).
- No "safe time" or "safe street" claims.
- The disclaimer says the page is not 100% accurate: it's built from the city's data, which misses temporary changes;
  the posted signs count; the explanations are the page's own reading of the data (Citina, 2026-09-26). It's one short
  paragraph; "not a guide to parking illegally" and what the page loads are behind "More" (2026-09-27).
- Privacy lines promise only what the page does. "Show blocks near me" only centers the map; "Show what's around me"
  also puts the circle there, in the browser, kept out of the link. The driving side loads the whole city's closures
  and temporary signs from data.sf.gov, never just the area in view.
- A term the reader meets is explained where it's used, or linked with a "?" to where it is.
- No text that means nothing to readers: no dataset IDs, CNN numbers, ticket codes or internal codes on the page.
  Datasets named in the method are linked.

---

## 4. Build pipeline

```
fetch_sf.py      data/raw/  (not committed)   SODA downloads: JSON per dataset; meter policies and tickets as CSV,
                                              tickets a month at a time (data/raw/tickets/YYYY-MM.csv)
analyze_sf.py    docs/data/ (release asset)   index.json, streets.json, cells/{key}.json (its docstring lists the fields)
hoods.py         docs/hoods.json (committed)  Analysis Neighborhoods j2bu-swwd outlines
```

- **Driving, per block side** (left or right of the block's line, as the city's data has them): street-cleaning groups
  with their enforcement, regulations, meter groups (cap, spaces, week of paid / open-to-all / tow-away / other-use
  pieces with rates and limits); per block, tickets per kind with half-hour counts. Regulations have no CNN: they're
  lines along the curb, placed on the side they run along for at least a quarter of the block.
- **Walking, per corner and crash**: police reports per kind and calls per group at each corner (daylight and dark, and
  the half hour of each), pedestrian crashes with position, severity, hour, daylight or dark and cause.
- **Daily-changing data** (closures `8x25-yybr`, temporary no-parking signs `sftu-nd43`): the page loads it from
  data.sf.gov itself, for the whole city, today and the next two weeks.
- **Weekly** (`weekly.yml`, Mondays): fetch, analyze, check the counts against last week's (a drop of more than 10%
  stops it), publish `docs/data/` as the `sf-data` release, deploy Pages. Ticket months are kept between runs in the
  Actions cache; a month is downloaded again when it's one of the last two or its copy is over four weeks old.
- **Windows**: two years up to each dataset's latest date. Tickets end on the last day with at least half the usual
  count for its weekday, since the city fills in the last few days late.

---

## 5. Milestones

- [x] **0. Setup** — folder, git repo, plan, page skeleton with the mode switch.
- [x] **1. Map** — the SVG + OSM tile map from LA Street Rules; SF bounds; neighborhoods; search over every street.
- [x] **2. Driving data** — street cleaning, regulations, meters and policies, tickets (2 yrs); the card (2026-09-26).
- [x] **3. Can I park here?** — the time control, the rules worked out in the page, the map colored by side (2026-09-26).
- [x] **4. Walking data** — pedestrian crashes, HIN, police reports and calls at corners, the circle, the summary.
- [x] **4a. Cameras** — speed and red-light cameras; car break-ins at corners.
- [x] **4b. Styles** — ticket-clock `9204808`'s type sizes, find bar, closed method rows, location dot, tooltips.
- [x] **5. Temporary** — closures and temporary no-parking signs, loaded live (2026-09-26).
- [x] **6. Automation** — `weekly.yml` and `pages.yml`; live at https://citina.github.io/sf-streets/ (2026-09-26).
- [ ] **7. Words** — README screenshots.

---

## 6. Open decisions

1. **Name.** Working title "SF Streets". Proposed 2026-09-25: Both Sides (recommended), Curb to Corner, SF Street Rules,
   Block by Block, Curb & Crosswalk.
2. **Police reports on the walking side.** Decided (Citina, 2026-09-25): included, from the last two years, with the
   reporting and patrol caveat in the card and method. Naloxone reports dropped 2026-09-26 (303 in two years, filed as
   non-criminal, a small slice of overdoses).
3. **Publish.** Public at `citina/sf-streets`, on GitHub Pages with weekly data. Still open: list it as a sister site on
   the ticket-clock pages?
4. **Map in dark mode.** Kept light, as on LA Street Rules.
5. **Time window.** Two years for everything dated. SFPD changed the set of corners it places reports at on 2024-04-24,
   so two years stays on one set; `WINDOW` in `analyze_sf.py` changes it.
6. **Privately run garages** aren't in the city's open data; the page shows the city-run ones only. A commercial source
   would be a new kind of dependency.
7. **The walking side's dropped layers** (crosswalks and signals, speed limits, "What's built here") stay dropped unless
   Citina brings them back.
