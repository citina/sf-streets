# SF Streets — data sources

What the page is built from, what each dataset is used for, and what was looked at and left out. Checked 2026-09-25
(walking) and 2026-09-26 (driving).
Only datasets with **a place for each row** (coordinates, a line or shape, or a key that places it, like a CNN or a
meter's post ID) and **data from the last three years** are listed.
Everything is from data.sf.gov (Socrata; SODA API at `https://data.sf.gov/resource/<id>.json`) unless noted.
`fetch_sf.py` downloads, `analyze_sf.py` builds `docs/data/`, `hoods.py` writes `docs/hoods.json`. Two datasets that
change daily (closures and temporary no-parking signs) are loaded by the page itself instead.

Dated data covers the **two years up to each dataset's latest date** (`WINDOW` in `analyze_sf.py`). `fetch_sf.py`
downloads 28 months back to leave room for the crash data's ~2-month lag, and parking tickets from the month the window
starts in. The walking summary's totals per year are
the exception: data.sf.gov counts them for every full year (pedestrians hit since 2015, police reports since 2018), and
`fetch_sf.py trends` downloads only those totals.

## In use

| Dataset | ID | Used for | Notes |
|---|---|---|---|
| Streets – Active and Retired | `3psu-pn9h` | Every block on the map (15,142), its name (street + hundred block, from the address ranges), cross streets, odd/even side, its neighborhood (the row's `analysis_neighborhood`), and its two corners (node CNNs). Street search (`streets.json`). | Active segments in the street, park and pedestrian-path layers. Left out: freeways and ramps (class 1 and 6), names with RAMP or PARKING LOT. Corner positions are the median of the segment ends that meet there (0.4 m median from where SFPD places reports) |
| Analysis Neighborhoods | `j2bu-swwd` | Neighborhood outlines on the city-wide map, neighborhood search, the tag naming the one in view, the walking map's shading | 41 neighborhoods, simplified to ~2 m; committed as `docs/hoods.json` |
| Traffic Crashes Resulting in Injury | `ubvf-ztfx` | Walking: the card's "Pedestrians hit" (how many in the circle, badly hurt or killed, the rank among intersections, time of day, after dark, main causes; not drawn on the map since 2026-09-26); pedestrians hit per neighborhood. The walking summary: by month and hour, what they were doing (`ped_action`), causes, around 24 places, the corners with the most, and totals per year since 2015 | Only crashes with a pedestrian (`type_of_collision` or `mviw`, and `ped_action` not "No Pedestrian Involved"). 1,213 in the window, 39 fatal (13.6k since 2005; every crash has an intersection CNN, about half a segment CNN; runs ~2 months behind). Mid-block crashes count for the block, the rest for the intersection. Cause is `vz_pcf_description` in plainer words (`CAUSE` in `analyze_sf.py`: every cause behind two or more crashes in the window) |
| 2024 High Injury Network | `enwt-3u8m` | Walking: the High Injury Network lines, the card's list of its streets that pass through the circle, and its share of the streets and of people walking hit (under the map) | The Department of Public Health's list for Vision Zero: corridors of one street at least a quarter mile long with 10 or more people killed or badly hurt per mile in 2020–24 (police reports matched with hospital and ambulance records), all road users. 1,438 blocks, 8% of the street length on the map, yet 49% of the people walking hit in the window were on it or at its corners. 4,928 of its 5,917 segments (`cnn_sgmt_pkey`) are blocks on the map; the rest are freeways and ramps |
| Police Department Incident Reports: 2018 to Present | `wg3w-h783` | Walking: "Violence & robbery" and "Drug offenses" dots at corners, the card's counts per kind (with the half hour of each, for its charts) and rank, the neighborhood shading, and the walking summary (reports by hour and by month, around 24 places, totals per year since 2018). Driving: "Car break-ins" | ~99k reports a year, 96% placed at a corner. Six kinds (below): 40,593 reports at 5,048 corners. Each report counts once per kind. SFPD places each at a nearby corner (`cnn`); the set of corners changed on 2024-04-24, which is why the window is two years |
| Law Enforcement Dispatched Calls for Service: Closed | `2zdj-bwza` | Walking: "Calls to police" rings at corners, and the card's calls per group (with the half hour of each, for its charts) and rank | Calls from the public only (`onview_flag` N; a third of all calls are officers' own stops, which show where police patrol). Four groups (`CALL_GROUPS` in `fetch_sf.py`, below): 110,724 calls at 5,718 corners. Each call is placed at a nearby intersection (`intersection_id`, the same node CNN as the police reports' corners); sensitive calls have no place. Calls aren't checked: for these types, a third ended with no one there when police arrived and 12% in a written report |
| Automated Speed Enforcement Citations | `d5uh-bk84` | Driving: 56 speed-camera markers with the posted limit, tickets and warnings; "Cameras near here" on the card | Daily counts per site, summed over the window (the cameras started in April 2025; the data runs about 3 months behind) |
| Red Light Camera Citations | `uzmr-g2uc` | Driving: 13 red-light camera markers with tickets per intersection; "Cameras near here" on the card | Monthly counts per intersection and direction |
| SFMTA - Parking Citations & Fines | `ab4h-6ztd` | Driving: "Tickets written here" (kinds, the fine now, usual day and time, half-hour charts), tickets per block on the map, how often each side's cleaning days got ticketed, and the driving summary | ~1.26M a year placed on blocks, 2,521,895 in the window. Downloaded a month at a time as CSV. Placed by the address written on the ticket: the block whose house numbers include it, the side by odd or even (98% place); tickets without a usable address by their coordinates, which are address points about 11 m off the street. The window ends on the last day with at least half the usual count for its weekday (the city fills in the last few days late); rows dated after today are typos. Kind names are SFMTA's short descriptions in plain words (`T_KIND` in `analyze_sf.py`) |
| Street Sweeping Schedule | `yhqp-riqs` | Driving: each side's street-cleaning sign, next dates, and "Can I park here?" | 37.9k rows, one per block side (CNN and L/R, with the side's compass name) and weekday, with hours, weeks of the month and whether it's swept on holidays; "Holiday" rows give holiday hours. 12,202 blocks. L and R are left and right of the centerline's direction, the same as its address ranges. Rows under CNNs the centerlines have retired (47 segments, where two were merged into one) go on the block their line runs along, with L and R flipped if it ran the other way |
| Parking regulations (except non-metered color curb) | `hi6h-neyh` | Driving: time limits, residential permit areas, pay or permit, no parking any time or at set hours, no overnight parking, government permits only, no oversized vehicles | ~7.8k lines drawn along the curb, with no CNN: placed on the block side they run along (within 20 m, roughly parallel) for at least a quarter of its length; 4,691 blocks. Of the 2,500 blocks with 20 or more permit-area tickets, 40 get no permit area |
| Parking Meters | `8vzz-qzz9` | Driving: metered spaces per side by cap color | On-street meters in use (active `M` or pay-by-plate `P`): 28,478 spaces on 2,157 blocks. Placed by their CNN (`street_seg_ctrln_id`) and, for the side, their position (98.5% agree with the house number's side) |
| Meter Policies | `qq7v-hds4` | Driving: each meter's paid hours, rates and time limits, tow-away hours, and hours kept for another use | Per meter post and weekday, in effect today; downloaded as CSV without the free pieces. `OP` paid, `ALT` with a rate open to all (a yellow or red meter's other hours), `ALT` without a rate kept for another use (often commuter-shuttle hours), `TOW` tow-away, `PRE` pay ahead (not shown) |
| SFMTA Managed Off-street Parking | `vqzx-t7c4` | Driving: "City garages & lots" on the map and nearby on the card | 58 garages and lots run by SFMTA, the Port, Recreation and Parks and Caltrans; 51 placed (by main entrance, or by address). No hours or rates. Privately run garages aren't in the city's open data |
| Temporary Street Closures | `8x25-yybr` | Driving: streets closed at the time picked (map and "Can I park here?"), and the card's closures | Loaded by the page itself from data.sf.gov, the whole city's, for today and the next two weeks (~500 rows): special events, shared spaces and permitted work, per CNN. Only SFMTA's permits; not closures by Public Works or the police |
| Parking Signs / Street Space Permits | `sftu-nd43` | Driving: temporary no-parking signs in "Can I park here?" and on the card | Loaded by the page from data.sf.gov: permits posted in the last four months and still running (a few dozen at a time), with CNN, side, days, hours and length along the curb. A small share of the temporary signs on the street |
| OpenStreetMap tiles *(not DataSF)* | — | The map images | Loaded by the reader's browser from tile.openstreetmap.org, only for the part of the map on screen |

**The six police kinds** (`KINDS` in `analyze_sf.py`):

| Kind | From | Layer |
|---|---|---|
| Robbery | category Robbery | Violence & robbery |
| Assault and other violence | categories Assault, Homicide, Rape, Sex Offense, Human Trafficking | Violence & robbery |
| Pickpocketing and purse snatching | subcategories Larceny Theft - Pickpocket, - Purse Snatch | Violence & robbery |
| Weapons | categories starting "Weapons" | Violence & robbery |
| Drug offenses | categories starting "Drug" | Drug offenses |
| Car break-ins | subcategories Larceny - From Vehicle, Theft From Vehicle, Larceny - Auto Parts | Car break-ins (driving) |

**The four call groups** (by `call_type_final`, the type dispatch closed the call as):

| Group | Call types |
|---|---|
| Fights and assaults | fight with or without weapons (418, 419), assault and battery (240), aggravated assault (245), stabbing (219) |
| Someone with a gun or knife | person with a gun (221) or knife (222), shots fired (216), ShotSpotter alert (216S), shooting (217) |
| Robbery | robbery (211), strong-arm robbery (212), purse snatching (213) |
| Threats and harassment | threats or harassment (650), stalking (646), indecent exposure (311) |

### Left out of the datasets in use

- **Police reports:** naloxone given for an overdose (incident code 51050, filed as Non-Criminal: 303 in two years,
  only 4 of them also drug offenses; dropped 2026-09-26 as too small a slice of overdoses), and every other category. The largest in the 28 months fetched: other larceny theft (31k rows),
  other miscellaneous (17k), malicious mischief (15k), warrants (14k), burglary (11k), motor vehicle theft (11k),
  non-criminal (9k), lost property, fraud, recovered vehicles, missing persons, disorderly conduct. Also reports with no
  corner, and supplements already counted.
- **Crashes:** crashes without a pedestrian (car-to-car, bicycles), and everything before the window (the data goes back
  to 2005). Victim age and injury details (`nwes-mmgh`, `8gtc-pjc6`) aren't fetched.
- **Calls to police:** officers' own stops, and every other call type. The largest from the public in two years: traffic
  citations (226k), suspicious persons (51k), tows (45k), trespassers (37k), noise (33k), alarms (29k), well-being checks
  (29k), burglary (17k), petty theft (13k), vandalism (11k), suicide attempts (8k), mentally disturbed persons (7k). Also
  calls marked domestic violence, elder or child abuse (DV, EA, CA: mostly at home), complaints about homeless people,
  and sit/lie enforcement.
- **Speed cameras:** `avg_issued_speed` and the mph-over buckets (`_11_to_15_mph_over` and so on) are downloaded but
  not shown.
- **Parking citations:** Muni fare and passenger conduct citations (fare evasion, failure to show proof of payment and
  the like: ~85k in two years, written at stops and stations), "no violation" rows, ~16k tickets that place on no block on the
  map (station names, empty or unmatched addresses), and ticket codes (the page shows plain names).
- **Parking regulations:** free-text details (resolution numbers, notes), and the `rpp_sym` map styling.
- **Meters:** meters temporarily inactive (`T`), removed or unknown, and off-street meters; the pay-ahead (`PRE`)
  pieces of their policies.

## Planned, not used yet

**Driving:** nothing planned now. Could add later: On-Street Parking Census (`9ivs-nf5y`, spaces per CNN, 2024), Blue
Curb Spaces (`g69s-9jxr`), Transit Only Lanes (`tzh6-6j82`), and the photos of posted temporary signs (`pigs-fac7`).

**Walking: what's built to protect people** (dropped 2026-09-26, with the "Crosswalks & signals" and "Speed limits"
layers; kept here in case it comes back)

| Use | Dataset | ID |
|---|---|---|
| Signals, crosswalks, safety zones, stop signs | Traffic Signals; Continental Crosswalks; Painted Safety Zones; Stop Signs | `ybh5-27n2`; `g9zy-srvv`; `vtn2-q8ky`; `4542-gpa3` |
| Speed limits and school zones | Speed Limits per Street Segment | `3t7b-gebn` (also for driving) |
| Traffic calming, slow streets | Intersection-Level Traffic Calming; Mid-Block Traffic Calming; Slow Streets | `bp3t-bd4t`; `abhw-ffzx`; `hkz3-itiu` |
| Kids | Crossing Guard Intersections; Safe Routes schools | `ujya-ewdj`; `bhj2-gxup` |
| Wheelchairs and strollers | Curb Ramps | `ch9w-7kih` |

**Maybe later:** 311 Cases (`vw6y-z8j6`: streetlights out, blocked sidewalks; large, filter by category), crash
victims and parties (`nwes-mmgh`, `8gtc-pjc6`), Traffic Crashes Resulting in Fatality (`dau3-4s8f`; the injury data
already marks fatal crashes), Pavement Condition (`5aye-4rtt`), Street Tree Inventory (`tkzw-k3nq`).

## Looked at and not used

| Dataset | ID | Why not |
|---|---|---|
| Law Enforcement Dispatched Calls for Service: Real-Time | `gnap-fj3t` | Only ~3.8k calls from the last year, as they happen; the Closed file (`2zdj-bwza`, in use) has them all |
| SFMTA Enforced Temporary Tow Zones | `6r5h-j298` | 155k rows, most without a status, end dates into the 2040s; `sftu-nd43` instead |
| Street Signs | `m48z-6ji4` | The posted signs' legends; the rules come from the sweeping schedule, meters and regulations instead |
| Blockfaces with Meters; Metered Street Blocks | `mk27-a5x2`; `27b3-yjjx` | Meters are placed on their side by position instead |
| Temp Street Closure Intersections | `7p5y-sxmu` | The closures' street segments (`8x25-yybr`) are enough for parking |
| SFMTA - Off-Street Parking Locations | `mizu-nf6z` | Last updated 2018; `vqzx-t7c4` is current |
| List of Streets and Intersections | `pu5n-qu5c` | The centerlines already carry names and cross streets |
| Street Intersections; Street Nodes | `gmfx-8h6i`; `vd6w-dq8r` | Corners are placed from the centerline ends instead |
| Fire Incidents | `wr8u-xric` | Building, vehicle and outdoor fires: not about walking on the street |
| Police Department Stop Data | `ubqf-aqzw` | Where police stopped people and why: shows where police patrol, not what happens to people walking |

Some links are maps or charts of another dataset, so the dataset behind them is used or planned instead:

| Link | Is a view of | Status |
|---|---|---|
| `icnu-39tp` | `8ar7-det4`, itself a view of `uzmr-g2uc` | In use through `uzmr-g2uc` |
| `jq29-s5wp`, `pbh9-m8j2` | `wg3w-h783` | In use through `wg3w-h783` |
| `q6vq-c5yf` (Narcan chart) | `wg3w-h783`, code 51050 | In use through `wg3w-h783` |
| `qbyz-te2i` | `hi6h-neyh` | In use through `hi6h-neyh` |
| `nb2q-m4if` | `v9cz-kk5i`, a filtered view of `8x25-yybr` | In use through `8x25-yybr` |
| `fuhz-9thv` | `vqzx-t7c4` | In use through `vqzx-t7c4` |

The Transportation category alone has no crash data; the walking side needs the Public Safety and Health categories.
The street-cleaning schedule is under City Infrastructure.
To list a category, use `data.sf.gov/api/views.json?category=…`; the Socrata catalog API lists only 5 SF datasets.
