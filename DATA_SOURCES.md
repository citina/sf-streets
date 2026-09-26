# SF Streets — data sources

What the page is built from, what each dataset is used for, and what was looked at and left out. Checked 2026-09-25.
Everything is from data.sf.gov (Socrata; SODA API at `https://data.sf.gov/resource/<id>.json`) unless noted.
`fetch_sf.py` downloads, `analyze_sf.py` builds `docs/data/`, `hoods.py` writes `docs/hoods.json`.

Dated data covers the **two years up to each dataset's latest date** (`WINDOW` in `analyze_sf.py`). `fetch_sf.py`
downloads 28 months back to leave room for the crash data's ~2-month lag.

## In use

| Dataset | ID | Used for | Notes |
|---|---|---|---|
| Streets – Active and Retired | `3psu-pn9h` | Every block on the map (15,142), its name (street + hundred block, from the address ranges), cross streets, odd/even side, its neighborhood (the row's `analysis_neighborhood`), and its two corners (node CNNs). Street search (`streets.json`). | Active segments in the street, park and pedestrian-path layers. Left out: freeways and ramps (class 1 and 6), names with RAMP or PARKING LOT. Corner positions are the median of the segment ends that meet there (0.4 m median from where SFPD places reports) |
| Analysis Neighborhoods | `j2bu-swwd` | Neighborhood outlines on the city-wide map, neighborhood search, the tag naming the one in view, the walking map's shading | 41 neighborhoods, simplified to ~2 m; committed as `docs/hoods.json` |
| Traffic Crashes Resulting in Injury | `ubvf-ztfx` | Walking: "Pedestrians hit" dots (ringed when badly hurt or killed), the card's counts, time-of-day chart, after-dark count and main causes; pedestrians hit per neighborhood | Only crashes with a pedestrian (`type_of_collision` or `mviw`, and `ped_action` not "No Pedestrian Involved"). 1,213 in the window, 39 fatal (13.6k since 2005; every crash has an intersection CNN, about half a segment CNN; runs ~2 months behind). Mid-block crashes count for the block, the rest for the intersection. Cause is `vz_pcf_description` in plainer words |
| 2024 High Injury Network | `enwt-3u8m` | Walking: the red High Injury Network lines, the card's "High Injury Network: Yes/No" | Vision Zero's list: ~13% of streets, where the severe and fatal injuries of 2020–24 concentrate. 4,928 of its 5,917 segments (`cnn_sgmt_pkey`) are blocks on the map; the rest are freeways and ramps |
| Police Department Incident Reports: 2018 to Present | `wg3w-h783` | Walking: "Violence & robbery" and "Drugs & overdoses" dots at corners, the card's counts per kind and citywide rank, the neighborhood shading. Driving: "Car break-ins" | ~99k reports a year, 96% placed at a corner. Seven kinds (below): 40,896 reports at 5,050 corners. Each report counts once per kind. SFPD places each at a nearby corner (`cnn`); the set of corners changed on 2024-04-24, which is why the window is two years |
| Automated Speed Enforcement Citations | `d5uh-bk84` | Driving: 56 speed-camera markers with the posted limit, tickets and warnings; "Cameras near here" on the card | Daily counts per site, summed over the window (the cameras started in April 2025) |
| Red Light Camera Citations | `uzmr-g2uc` | Driving: 13 red-light camera markers with tickets per intersection; "Cameras near here" on the card | Monthly counts per intersection and direction |
| OpenStreetMap tiles *(not DataSF)* | — | The map images | Loaded by the reader's browser from tile.openstreetmap.org, only for the part of the map on screen |

**The seven police kinds** (`KINDS` in `analyze_sf.py`):

| Kind | From | Layer |
|---|---|---|
| Robbery | category Robbery | Violence & robbery |
| Assault and other violence | categories Assault, Homicide, Rape, Sex Offense, Human Trafficking | Violence & robbery |
| Pickpocketing and purse snatching | subcategories Larceny Theft - Pickpocket, - Purse Snatch | Violence & robbery |
| Weapons | categories starting "Weapons" | Violence & robbery |
| Drug offenses | categories starting "Drug" | Drugs & overdoses |
| Naloxone given for an overdose | incident code 51050 | Drugs & overdoses |
| Car break-ins | subcategories Larceny - From Vehicle, Theft From Vehicle, Larceny - Auto Parts | Car break-ins (driving) |

### Left out of the datasets in use

- **Police reports:** every other category. The largest in the 28 months fetched: other larceny theft (31k rows),
  other miscellaneous (17k), malicious mischief (15k), warrants (14k), burglary (11k), motor vehicle theft (11k),
  non-criminal (9k), lost property, fraud, recovered vehicles, missing persons, disorderly conduct. Also reports with no
  corner, and supplements already counted.
- **Crashes:** crashes without a pedestrian (car-to-car, bicycles), and everything before the window (the data goes back
  to 2005). Victim age and injury details (`nwes-mmgh`, `8gtc-pjc6`) aren't fetched.
- **Speed cameras:** `avg_issued_speed` and the mph-over buckets (`_11_to_15_mph_over` and so on) are downloaded but
  not shown.

## Planned, not used yet

**Driving** (milestones 2, 3 and 5 in [PLAN.md](PLAN.md))

| Use | Dataset | ID | Notes |
|---|---|---|---|
| Tickets written | SFMTA Parking Citations & Fines | `ab4h-6ztd` (view of `ekn6-qajs`) | ~1.38M in 12 months, 98.4% with coordinates; top: street cleaning (≈41%), meter expired, RPP overtime, yellow/red zone. **Has future-dated rows (e.g. 2044)**: drop anything after `data_as_of` |
| Street cleaning, per side | Street Sweeping Schedule | `yhqp-riqs` | 37.9k block sides with day, hours and week flags; *City Infrastructure* category |
| Time limits, permit areas, no parking | Parking regulations (except non-metered color curb) | `hi6h-neyh` | `regulation`, `days`, `hrs_begin/end`, `hrlimit`, `rpparea1..3`, `exceptions`; ~7.8k rows, mostly time limits. **No CNN column**: join to block sides by geometry |
| The posted signs | Street Signs | `m48z-6ji4` | Sign legend and CNN: 25k street-cleaning, 7k permit, 2k no-parking-any-time, 3k tow signs. Lets the card quote the sign |
| Meters | Parking Meters | `8vzz-qzz9` | Per space; `street_seg_ctrln_id` is the CNN |
| Meter hours and rates | Meter Policies | `qq7v-hds4` | Per space and day: hours, rate, time limit |
| Metered block sides | Blockfaces with Meters / Metered Street Blocks | `mk27-a5x2` / `27b3-yjjx` | To draw meters as block sides, not dots |
| How many spaces | On-Street Parking Census | `9ivs-nf5y` | Supply per CNN (2024) |
| Garages and lots | SFMTA Managed Off-street Parking; Off-street parking map | `vqzx-t7c4`; `fuhz-9thv` | Capacity, hours |
| Accessible spaces | Blue Curb Spaces | `g69s-9jxr` | |
| Temporary no-parking | Parking Signs / Street Space Permits | `sftu-nd43` | Construction no-parking with dates, hours, side and CNN; daily. Photos in `pigs-fac7` |
| Closures | Temporary Street Closures; Temp Street Closure Intersections | `8x25-yybr`; `7p5y-sxmu` | Events and construction |
| Red lanes | Transit Only Lanes | `tzh6-6j82` | When the curb lane is off limits |

**Walking** (the rest of milestone 4: what's built to protect people)

| Use | Dataset | ID |
|---|---|---|
| Signals, crosswalks, safety zones, stop signs | Traffic Signals; Continental Crosswalks; Painted Safety Zones; Stop Signs | `ybh5-27n2`; `g9zy-srvv`; `vtn2-q8ky`; `4542-gpa3` |
| Speed limits and school zones | Speed Limits per Street Segment | `3t7b-gebn` (also for driving) |
| Traffic calming, slow streets | Intersection-Level Traffic Calming; Mid-Block Traffic Calming; Slow Streets | `bp3t-bd4t`; `abhw-ffzx`; `hkz3-itiu` |
| Kids | Crossing Guard Intersections; Safe Routes schools | `ujya-ewdj`; `bhj2-gxup` |
| Wheelchairs and strollers | Curb Ramps | `ch9w-7kih` |

**Maybe later:** 311 Cases (`vw6y-z8j6`: streetlights out, blocked sidewalks; large, filter by category), crash
victims and parties (`nwes-mmgh`, `8gtc-pjc6`), Traffic Crashes Resulting in Fatality (`dau3-4s8f`; the injury data
already marks fatal crashes), Sidewalk Widths (`4g86-grxu`, a 2014 study), Pavement Condition (`5aye-4rtt`), Street
Tree Inventory (`tkzw-k3nq`).

## Looked at and not used

| Dataset | ID | Why not |
|---|---|---|
| EMS overdose responses | `ed3a-sn39` | Weekly citywide totals, no places, stopped in 2023. Naloxone reports from `wg3w-h783` are the only overdose data with places |
| Law Enforcement Dispatched Calls: Real-Time; …Closed | `gnap-fj3t`; `2zdj-bwza` | Unverified calls; the real-time file is a rolling ~2.5-month window |
| Meter Operating Schedules | `6cqg-dxku` | Frozen in March 2014; `qq7v-hds4` is the current one |
| SFMTA Enforced Temporary Tow Zones | `6r5h-j298` | 155k rows, most without a status, end dates into the 2040s; `sftu-nd43` instead |
| Blockfaces | `pep9-66vw` | Curb lines from 2020; only 1.9k of 18k rows have a CNN |
| List of Streets and Intersections | `pu5n-qu5c` | The centerlines already carry names and cross streets |
| Street Intersections; Street Nodes | `gmfx-8h6i`; `vd6w-dq8r` | Corners are placed from the centerline ends instead |
| Fire, DA, jail, use of force, stops, hazard zones | various | Not about the street |

Some links are maps or charts of another dataset, so the dataset behind them is used or planned instead:

| Link | Is a view of | Status |
|---|---|---|
| `icnu-39tp` | `8ar7-det4`, itself a view of `uzmr-g2uc` | In use through `uzmr-g2uc` |
| `jq29-s5wp`, `pbh9-m8j2` | `wg3w-h783` | In use through `wg3w-h783` |
| `q6vq-c5yf` (Narcan chart) | `wg3w-h783`, code 51050 | In use through `wg3w-h783` |
| `qbyz-te2i` | `hi6h-neyh` | Planned through `hi6h-neyh` |
| `nb2q-m4if` | `v9cz-kk5i`, a filtered view of `8x25-yybr` | Planned through `8x25-yybr` |
| `ygcm-bt3x` | `4g86-grxu` | Maybe later |

The Transportation category alone has no crash data; the walking side needs the Public Safety and Health categories.
To list a category, use `data.sf.gov/api/views.json?category=…`; the Socrata catalog API lists only 5 SF datasets.
