# SF Streets — plan

Working title. A map of San Francisco in the style of [LA Street Rules](https://citina.github.io/ticket-clock/streets/),
but the page changes with who's asking:

- **I'm driving** → *Can I park here, until when, and what gets ticketed on this block?*
- **I'm walking** → *How often are people walking hit by cars here, when and why, what gets reported to police at its
  corners, and what's built to protect them?*

Same map, same search box, same "pick a block" card, but different layers, legend, time control, card contents
and method text for each mode. The mode lives in the URL (`#drive` / `#walk`) so either view can be linked.

---

## 1. What carries over from ticket-clock, and what's easier in SF

**Reused as-is or nearly so**

- The hand-written page, no build step, no map library: SVG block lines over OpenStreetMap tiles, pan, zoom, a
  two-finger turn with a compass back to north, "Show blocks near me", and the search box
  (`ticket-clock/docs/streets/index.html`). LA dropped its automatic turn to the street grid in ticket-clock 121ced6
  (jumps stay north up so building names stay level); ported as LA has it now.
- Design tokens, type (Barlow / Barlow Condensed / IBM Plex Mono), mast with sister sites, panel/card styles, method as
  closed rows, About with sister-site cards, disclaimer. Styles match ticket-clock `9204808` (2026-09-25): five text
  sizes (12 / 14 / 15 / 16 / 18.5 px), no light-gray text (`--ink-3` only for non-text marks), 16px text inputs, a red
  "your location" dot, tooltips for a mouse only.
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

See **[DATA_SOURCES.md](DATA_SOURCES.md)**: what's in use and for what, what's planned for each milestone, and what was
looked at and left out (including Citina's list of 2026-09-25). All from data.sf.gov, plus OpenStreetMap for the map
images.

---

## 3. The page (skeleton in `docs/index.html`)

```
mast            SF Streets · (sister sites)                       Updated weekly · About
h1 + lede       changes with mode
MODE SWITCH     [ 🚗 I'm driving ]  [ 🚶 I'm walking ]
find bar        Show blocks near me · search street / address / neighborhood
time control    drive: When [Now | pick day+time]  For [1h 2h 4h overnight]
                walk:  When [Any | Daylight | After dark]
┌───────────────── map ─────────────────┐ ┌──────── card ────────┐
│ layer chips (per mode)                │ │ block name, eyebrow  │
│ OSM tiles + block lines               │ │ cards (per mode)     │
│ zoom / fit SF / north                 │ │                      │
└───────────────────────────────────────┘ └──────────────────────┘
legend (per mode)
explainer section  drive: SF street cleaning & RPP in one example
                   walk: summary of the city as a whole (built): when, where (around 24 places visitors go,
                   neighborhoods, corners), how, and totals per year
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
7. *(built)* **Car break-ins at its corners** and **Cameras near here** (within 500 m).

When the parking cards are built, use LA Street Rules' wording and layout as of ticket-clock `9204808`, adapted for
SFMTA:

- Subtitle: "505 SFMTA tickets since Sep 17, 2024" (not "Worked out from …").
- No schedule: "**No street-cleaning schedule found.** …" (and "…though 2 street-cleaning tickets have been written here
  since …" when there are a few). No meters: "No meters appear in SFMTA's inventory for this block, and no meter tickets
  since …". Metered: "12 metered spaces on this block", then their hours from `qq7v-hds4`.
- Last line: "This card is worked out from SFMTA citations recorded since … Ticket history may not include every rule
  that applies here."
- Ticket kinds: 5 before "Show all N kinds"; on phones the count/bar column is 76px (`max-width:480px`), and a time range
  never breaks inside ("9–10 pm", with no-break spaces and word joiners).
- A kind's dot chart: a bold heading ("What time of day these tickets were written", `.kchart-t`), axis labels "12am 3am
  6am 9am noon 3pm 6pm 9pm 12am" (every 6 hours under 340px, like the walking card's hour chart), and "Each dot is about
  N tickets, stacked by the half hour" under it.

**Walking card** (built, except 4)

1. **Pedestrians hit here** — on the block and at its two corners, two years: how many, how many badly hurt or killed,
   on the High Injury Network or not; what time of day they were hit, how many after dark, and the top causes.
2. **Reported to police at its corners** — robbery, violence, pickpocketing, weapons, drugs, naloxone; how the block's
   corners rank citywide.
3. **Calls to police at its corners** — calls from the public about fights and assaults, a gun or knife, robbery, threats
   and harassment; how the block's corners rank citywide.
4. **What's built here** — signal, continental crosswalk, painted safety zone, stop signs, speed limit, school zone, slow
   street, traffic calming.

**Map layers**

- Drive: speed and red-light cameras (built, default) · car break-ins (built) · blocks shaded by tickets per month ·
  street cleaning at the chosen time · meters · garages · closures.
- Walk: High Injury Network (thick lines) · pedestrians hit (dots, severe ringed) · violence and robbery (discs) · drugs
  and overdoses (squares) · calls to police (blue rings), all built and on by default, with neighborhoods shaded by violence and robbery per km of street
  while the whole city shows · crosswalks & signals · speed limits.

**Wording rules** (Citina, with the ticket-clock restyle)

- Never claim 100% unless it's literally 100% (block ranks are rounded down, so they never say "more than 100%").
- Labels say literally what they mean ("no street-cleaning schedule found", not "no sweeping").
- No "safe time" or "safe street" claims.
- Privacy lines promise only what the page itself does. "Show blocks near me" only centers the map; if the page ever
  queries data.sf.gov for the visible area (§4), recheck that line and the method note.

---

## 4. Build pipeline

```
fetch_sf.py      data/raw/  (not committed)   SODA downloads, one file per dataset (citations may need monthly files, like fetch_city.py)
analyze_sf.py    docs/data/ (release asset)   index.json, streets.json, cells/{key}.json
hoods.py         docs/hoods.json (committed)  Analysis Neighborhoods j2bu-swwd outlines
```

**Units.** Driving: a *block side* = CNN + side (L/R, with its compass name). Walking: a *segment* (CNN) plus its two
*intersections* (`cnn_intrsctn`), since most pedestrian crashes are at intersections.

**Per block side (drive):** sweeping rows, regulation rows (time limit, RPP, hours), meter spaces + policies, ticket
kinds (count, median fine, half‑hour histogram), share of posted cleaning days with a ticket, supply.

**Per segment/intersection (walk):** pedestrian crashes (2 yrs, with severity, hour, daylight or dark, cause), HIN flag,
police reports per kind at each corner (daylight and dark) with citywide ranks; still to come: protections, speed limit.

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
- [ ] **4. Walking data** — *(done: pedestrian crashes, HIN, police reports and naloxone at corners, 2 yrs, daylight/dark, neighborhood shading, card, the citywide summary)*; calls to police from the public at corners (`2zdj-bwza`); still to do: protections, speed limits.
- [x] **4a. Cameras** — speed (`d5uh-bk84`) and red-light (`uzmr-g2uc`) cameras on the driving map; car break-ins at corners.
- [x] **4b. Styles** — ticket-clock `9204808`'s type sizes, find bar, closed method rows, red location dot, tooltips,
  About cards (§1).
- [ ] **5. Temporary** — closures and tow zones at the chosen time.
- [ ] **6. Automation** — weekly workflow, city-data release asset, Pages.
- [ ] **7. Words** — explainer sections, method, disclaimers, README with screenshots.

---

## 6. Open decisions

1. **Name.** Working title "SF Streets"; folder `~/Desktop/sf-streets`. Proposed 2026-09-25: Both Sides (recommended),
   Curb to Corner, SF Street Rules, Block by Block, Curb & Crosswalk.
2. **"Where to avoid" when walking.** Traffic danger is well covered (crashes, HIN). Street crime (`wg3w-h783`) is the
   touchy one: it reflects where people report and where police patrol as much as where crime happens, and a map that
   says "avoid" over whole neighborhoods can stigmatize them. Options: (a) traffic only; (b) opt-in layer of
   person-directed incidents (robbery, assault) as counts per block, with that caveat; (c) leave for later.
   Recommendation: (a) for v1, revisit (b).
   **Decided (Citina, 2026-09-25):** include police reports on the walking side, and naloxone (overdose) reports, from the
   last two years; walking is now the focus. Built as corner counts by kind, shown as map layers (violence and robbery;
   drugs and overdoses) and on the card with a citywide rank, with the reporting and patrol caveat in the card and method.
3. **Publish.** The repo is public at `citina/sf-streets` (2026-09-25). Still open: turn on GitHub Pages (needs the
   weekly data workflow, since `docs/data/` isn't committed), and list it as a sister site on the ticket-clock pages?
4. **Map in dark mode.** Kept light, as on LA Street Rules; revisit only if LA changes.
5. **Time window.** Two years for everything dated (Citina: "2 or 3 years"). Two because SFPD changed the set of corners
   it snaps reports to on 2024-04-24, so two years stays on one set; `WINDOW` in `analyze_sf.py` changes it.
