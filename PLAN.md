# SF Streets — plan

Working title. A map of San Francisco in the style of [LA Street Rules](https://citina.github.io/ticket-clock/streets/),
but the page changes with who's asking:

- **I'm driving** → *Can I park here, until when, and what gets ticketed on this block?*
- **I'm walking** → *Is this street safe to walk, when is it worst, and what's built to protect me?*

Same map, same search box, same "pick a block" card, but different layers, legend, time control, card contents
and method text for each mode. The mode lives in the URL (`#drive` / `#walk`) so either view can be linked.

---

## 1. What carries over from ticket-clock, and what's easier in SF

**Reused as-is or nearly so**

- The hand-written page, no build step, no map library: SVG block lines over OpenStreetMap tiles, pan, zoom, a
  two-finger turn with a compass back to north, "Use my location", and the search box
  (`ticket-clock/docs/streets/index.html`). LA dropped its automatic turn to the street grid in ticket-clock 121ced6
  (jumps stay north up so building names stay level); ported as LA has it now.
- Design tokens, type (Barlow / Barlow Condensed / IBM Plex Mono), mast with sister sites, panel/card styles, method `dl`,
  About and disclaimer blocks.
- Data split into ~1 km map cells (`data/cells/{key}.json`) so the page only loads what's on screen, plus
  `index.json` and `streets.json` for search.
- Pipeline shape: `fetch_*.py` → raw downloads (not committed) → `analyze_*.py` → `docs/data/` (release asset) →
  weekly GitHub Action → Pages. `pages.yml` and `weekly.yml` port with new names.

**Easier in SF than in LA**

- **Citations already have latitude/longitude** (≈2.65M of 2.69M in the last two years). No address matching; snap each
  ticket to the nearest block side by geometry.
- **Everything shares one street key, the CNN** (centerline network number): sweeping, speed limits, crashes, closures,
  crosswalks, safety zones, the High Injury Network. Joins are by CNN, and by CNN + side where the data has sides.
- **The sweeping schedule is published per block side with week flags** (`yhqp-riqs`: `blockside`, `weekday`,
  `fromhour`–`tohour`, `week1`…`week5`, `holidays`). LA's side and weeks had to be inferred from tickets; here they're given,
  and tickets become the evidence of how often each is enforced.

---

## 2. Data

All from data.sf.gov (Socrata; SODA API at `https://data.sf.gov/resource/<id>.json`). Checked 2026‑09‑24.

### Driving

| Use | Dataset | ID | Geometry | Updates | Notes |
|---|---|---|---|---|---|
| Block lines + CNN key | Streets – Active and Retired | `3psu-pn9h` | line | daily | base geometry for every card. **In use** (`fetch_sf.py`, `analyze_sf.py`): 15,142 blocks |
| Search | List of Streets and Intersections | `pu5n-qu5c` | — | weekly | names + cross streets; not needed so far, the centerlines carry both |
| Tickets written | SFMTA Parking Citations & Fines | `ab4h-6ztd` (view of `ekn6-qajs`) | point | daily | ~1.38M in the last 12 months, 98.4% with coordinates; top: street cleaning (≈41%), meter expired, RPP overtime, yellow/red zone. **Has future-dated rows (e.g. 2044)** → drop anything after `data_as_of` |
| Street cleaning, per side | Street Sweeping Schedule | `yhqp-riqs` | line | as needed | 37.9k block sides; *City Infrastructure* category |
| Time limits, RPP areas, no-parking | Parking regulations (except non-metered color curb) | `hi6h-neyh` | multiline | weekly | `regulation`, `days`, `hrs_begin/end`, `hrlimit`, `rpparea1..3`, `exceptions`. ~7.8k rows, mostly time limits. **No CNN column**: join to block sides by geometry |
| Meters | Parking Meters | `8vzz-qzz9` | point | weekly | per space; `street_seg_ctrln_id` is the CNN, `blockface_id`, `cap_color` |
| Meter hours & rates | Meter Policies | `qq7v-hds4` | — | daily | per space × day: hours, hourly rate, time limit |
| Metered blockfaces | Blockfaces with Meters / Metered Street Blocks | `mk27-a5x2` / `27b3-yjjx` | line | weekly | to draw meters as block sides, not dots |
| How many spaces | On-Street Parking Census | `9ivs-nf5y` | line | 2024 | supply per CNN |
| Garages & lots | SFMTA Managed Off-street Parking; Off-street parking map | `vqzx-t7c4`; `fuhz-9thv` | point | weekly | capacity, hours, web site |
| Accessible spaces | Blue Curb Spaces | `g69s-9jxr` | point | weekly | |
| Temporary no-parking | Temporary Street Closures | `8x25-yybr` | line | daily | events, construction |
| Tow-away zones | SFMTA Enforced Temporary Tow Zones | `6r5h-j298` | point | daily | 155k rows, most without a status, end dates into the 2040s, and only a couple current in any week. Prefer `sftu-nd43` below |
| Context | Speed Limits per Street Segment | `3t7b-gebn` | multiline | as needed | shared with walking |

### Walking

| Use | Dataset | ID | Geometry | Updates | Notes |
|---|---|---|---|---|---|
| Pedestrian injury crashes | Traffic Crashes Resulting in Injury | `ubvf-ztfx` | point | monthly | 13.6k vehicle‑pedestrian crashes since 2005 (~3.5k since 2021), every one with an intersection CNN, about half with a segment CNN; runs to 2026‑07‑31 (≈2 month lag). Has `lighting`, `ped_action`, `vz_pcf_description`, `collision_severity`, `cnn_intrsctn_fkey`, `cnn_sgmt_fkey`. *Public Safety* category |
| Deaths | Traffic Crashes Resulting in Fatality | `dau3-4s8f` | point | monthly | |
| Victims / parties | …Victims Involved; …Parties Involved | `nwes-mmgh`; `8gtc-pjc6` | — | monthly | victim age, injury level |
| Where most severe crashes concentrate | 2024 High Injury Network | `enwt-3u8m` | multiline | — | Vision Zero's own list; ~13% of streets, severe and fatal injuries 2020–24. 5,917 segments keyed by `cnn_sgmt_pkey`, the same CNN as our blocks. *Health* category |
| Protection that's there | Traffic Signals; Continental Crosswalks; Painted Safety Zones; Stop Signs | `ybh5-27n2`; `g9zy-srvv`; `vtn2-q8ky`; `4542-gpa3` | point | varies | per intersection |
| Calming / speed | Speed Limits; Intersection-Level Traffic Calming; Mid-Block Traffic Calming; Slow Streets | `3t7b-gebn`; `bp3t-bd4t`; `abhw-ffzx`; `hkz3-itiu` | line/point | varies | school zones in speed limits |
| Kids | Crossing Guard Intersections; Safe Routes schools | `ujya-ewdj`; `bhj2-gxup` | point | 2024 | |
| Sidewalk width | Sidewalk Widths (2014) | `4g86-grxu` | line | historical | old; maybe skip |
| Police reports at corners | Police Department Incident Reports: 2018 to Present | `wg3w-h783` | point | daily | **In use**: robbery, violence, pickpocketing, weapons, drugs, naloxone (code 51050), car break-ins; see §6.2 |
| *(decision needed)* Conditions | 311 Cases (streetlights out, sidewalk defects…) | `vw6y-z8j6` | point | daily | large; filter by category |

The Transportation category alone has **no crash data**; the walking side needs Public Safety and Health datasets too.

### Reviewed 2026-09-25: Citina's list and a pass through the catalog

Checked against the Public Safety, Transportation, City Infrastructure, Health and Geography categories (via
`data.sf.gov/api/views.json?category=…`; the Socrata catalog API lists only 5 SF datasets). Several links were map or
chart views; the dataset behind each is named.

**Add**

| For | Dataset | ID | Why |
|---|---|---|---|
| drive | Street Signs | `m48z-6ji4` | The MTA's sign inventory with each sign's legend and CNN: 25k street-cleaning, 7k permit (RPP), 2k no-parking-any-time, 3k tow signs. Lets the card quote the posted sign |
| drive | Parking Signs / Street Space Permits | `sftu-nd43` | Temporary no-parking signs for construction, with dates, hours, side of street and CNN; daily. Photos in `pigs-fac7`. Better source for "temporary" than the tow-zone file |
| drive + walk | Automated Speed Enforcement Citations | `d5uh-bk84` | 56 speed-camera sites since April 2025; daily warnings and citations, posted speed, average ticketed speed |
| drive | Red Light Camera Citations | `uzmr-g2uc` | 13 camera intersections, monthly counts (Citina's `icnu-39tp` is a map of `8ar7-det4`, a view of this) |
| drive | Transit Only Lanes | `tzh6-6j82` | Red lanes and their hours: when you can't park or drive in the curb lane |
| drive | Temp Street Closure Intersections | `7p5y-sxmu` | Companion to `8x25-yybr` (Citina's `nb2q-m4if` is a map of `v9cz-kk5i`, a filtered view of it) |
| walk | Street Intersections; Street Nodes | `gmfx-8h6i`; `vd6w-dq8r` | Where each intersection CNN is: the corner unit that pedestrian crashes are keyed to |
| walk | Curb Ramps | `ch9w-7kih` | Per corner, with condition scores; for wheelchairs and strollers |

**Maybe later**

| For | Dataset | ID | Why not yet |
|---|---|---|---|
| walk | Police Department Incident Reports: 2018 to Present | `wg3w-h783` | Citina's `jq29-s5wp` and `pbh9-m8j2` are maps of it. ~99k reports a year, 96% placed at an intersection CNN (snapped to a nearby corner for anonymity; the set of corners changed on 2024-04-24). Top: larceny 19k, drugs 9.7k, assault 7.7k. **Now in use** (§6.2) |
| walk | 311 Cases | `vw6y-z8j6` | Streetlights out, sidewalk defects, blocked sidewalks: conditions after dark. Large; filter by category |
| walk | Sidewalk Widths (2014) | `4g86-grxu` | Citina's `ygcm-bt3x` is its map. Per CNN and side, but from a 2014 study |
| walk | Pavement Condition; Street Tree Inventory | `5aye-4rtt`; `tkzw-k3nq` | Comfort layers, low priority |

**Skip**

| Dataset | ID | Why |
|---|---|---|
| Meter Operating Schedules | `6cqg-dxku` | Frozen in March 2014; Meter Policies `qq7v-hds4` is the daily one |
| Map of Parking Regulations | `qbyz-te2i` | A map of `hi6h-neyh`, already planned |
| SFPD Narcan/Naloxone Deployment | `q6vq-c5yf` | A chart of incident reports with code 51050. **Used after all** (Citina, 2026-09-25), from `wg3w-h783` directly, where each report has a corner: ~150 a year. The only overdose data with places; EMS overdose responses (`ed3a-sn39`) are weekly citywide totals and stopped in 2023 |
| Law Enforcement Dispatched Calls: Real-Time; …Closed | `gnap-fj3t`; `2zdj-bwza` | Unverified calls; the real-time file is a rolling ~2.5-month window. Not a weekly-page measure |
| Blockfaces | `pep9-66vw` | Curb lines from 2020, only 1.9k of 18k rows carry a CNN; offset the centerlines instead |
| Fire, DA, jail, use of force, stops, hazard zones | various | Not about the street |

---

## 3. The page (skeleton in `docs/index.html`)

```
mast            SF Streets · (sister sites)                       Updated weekly · About
h1 + lede       changes with mode
MODE SWITCH     [ 🚗 I'm driving ]  [ 🚶 I'm walking ]
find bar        Use my location · search street / address / neighborhood
time control    drive: When [Now | pick day+time]  For [1h 2h 4h overnight]
                walk:  When [Any | Daylight | After dark]
┌───────────────── map ─────────────────┐ ┌──────── card ────────┐
│ layer chips (per mode)                │ │ block name, eyebrow  │
│ OSM tiles + block lines               │ │ cards (per mode)     │
│ zoom / fit SF / north                 │ │                      │
└───────────────────────────────────────┘ └──────────────────────┘
legend (per mode)
explainer section  drive: SF street cleaning & RPP in one example
                   walk: the High Injury Network in one example
method             data + limits, per mode
about · disclaimer
```

**Driving card**

1. **Can I park here?** Verdict for the chosen time and stay, per side: "Yes, until Tue 12 pm (street cleaning, north
   side)", "2 hr limit, 9 am–6 pm, except permit area S", "Metered, $3.25/hr until 6 pm".
2. **Street cleaning, per side** — posted day, hours, weeks (1st & 3rd…), next dates, and how often a cleaning day gets
   ticketed (drawn as a sign, like LA).
3. **Meters & time limits** — hours, rate now, time limit, RPP area.
4. **Tickets written here** — kinds, median fine, usual time of day (last 12 months), same expandable rows as LA.
5. **Temporary** — closures / tow-away at the chosen time.
6. **Nearby garages & lots** — nearest few, capacity, hours.

**Walking card**

1. **At a glance** — on the High Injury Network or not; pedestrian injury crashes in 5 years, how many severe or fatal.
2. **When** — crashes by hour, daylight vs dark.
3. **Why** — top primary collision factors (e.g. "driver failed to yield to pedestrian in crosswalk").
4. **What's built here** — signal, continental crosswalk, painted safety zone, stop signs, speed limit, school zone, slow
   street, traffic calming.
5. **Reported to police at its corners** — robbery, violence, pickpocketing, weapons, drugs, naloxone; how the block ranks citywide.

**Map layers**

- Drive: blocks shaded by tickets per month (default) · street cleaning at the chosen time · meters · garages · closures.
- Walk: pedestrian injury crashes (dots, severe ringed) · High Injury Network (thick lines, default) · crosswalks & signals
  · speed limits.

---

## 4. Build pipeline

```
fetch_sf.py      data/raw/  (not committed)   SODA downloads, monthly files for citations like fetch_city.py
analyze_sf.py    docs/data/ (release asset)   index.json, streets.json, cells/{key}.json
hoods.py         docs/hoods.json (committed)  Analysis Neighborhoods j2bu-swwd outlines
```

**Units.** Driving: a *block side* = CNN + side (L/R, with its compass name). Walking: a *segment* (CNN) plus its two
*intersections* (`cnn_intrsctn`), since most pedestrian crashes are at intersections.

**Per block side (drive):** sweeping rows, regulation rows (time limit, RPP, hours), meter spaces + policies, ticket
kinds (count, median fine, half‑hour histogram), share of posted cleaning days with a ticket, supply.

**Per segment/intersection (walk):** crash counts (5 yrs, by severity, hour, lighting, factor), HIN flag, protections,
speed limit.

**"Can I park here at time T"** runs in the page, from the rule rows in the cell file, so any day and time works
without precomputing.

**Daily-changing data** (closures, tow zones): recommend the page queries data.sf.gov for the visible area directly
(Socrata allows browser requests), instead of a daily rebuild. The method note must then say the viewed area is sent to
data.sf.gov.

---

## 5. Milestones

- [x] **0. Setup** — folder, git repo, this plan, page skeleton with the mode switch.
- [x] **1. Map** — port the SVG + OSM tile map from LA Street Rules; SF bounds; neighborhoods (`hoods.py` →
  `docs/hoods.json`); search over neighborhoods and, until milestone 2, a placeholder list of ~80 major streets (now replaced by every street).
- [ ] **2. Driving data** — fetch + analyze centerlines *(done: blocks on the map, search, block links)*, sweeping, regulations, meters + policies, citations (2 yrs), garages; block card cards 2–4 and 6.
- [ ] **3. Can I park here?** — time control + rules evaluator; map recolors by chosen time.
- [ ] **4. Walking data** — *(done: pedestrian crashes, HIN, police reports and naloxone at corners, 2 yrs, daylight/dark, neighborhood shading, card)*; still to do: protections, speed limits.
- [x] **4a. Cameras** — speed (`d5uh-bk84`) and red-light (`uzmr-g2uc`) cameras on the driving map; car break-ins at corners.
- [ ] **5. Temporary** — closures and tow zones at the chosen time.
- [ ] **6. Automation** — weekly workflow, city-data release asset, Pages.
- [ ] **7. Words** — explainer sections, method, disclaimers, README with screenshots.

---

## 6. Open decisions

1. **Name.** Working title "SF Streets"; folder `~/Desktop/sf-streets`.
2. **"Where to avoid" when walking.** Traffic danger is well covered (crashes, HIN). Street crime (`wg3w-h783`) is the
   touchy one: it reflects where people report and where police patrol as much as where crime happens, and a map that
   says "avoid" over whole neighborhoods can stigmatize them. Options: (a) traffic only; (b) opt-in layer of
   person-directed incidents (robbery, assault) as counts per block, with that caveat; (c) leave for later.
   Recommendation: (a) for v1, revisit (b).
   **Decided (Citina, 2026-09-25):** include police reports on the walking side, and naloxone (overdose) reports, from the
   last two years; walking is now the focus. Built as corner counts by kind, shown as map layers (violence and robbery;
   drugs and overdoses) and on the card with a citywide rank, with the reporting and patrol caveat in the card and method.
5. **Time window.** Two years for everything dated (Citina: "2 or 3 years"). Two because SFPD changed the set of corners
   it snaps reports to on 2024-04-24, so two years stays on one set; `WINDOW` in `analyze_sf.py` changes it.
3. **Publish** as `citina/sf-streets` on GitHub Pages, and list it as a sister site on the ticket-clock pages?
4. **Map in dark mode** — LA keeps the map light in dark mode; same here?
