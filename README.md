# SF Streets

A map of San Francisco that answers a different question depending on how you're getting around:

- **I'm driving:** can I park on this block now, or at the time I pick, and for how long, and what gets ticketed here?
  Street cleaning per side, meters and time limits, permit areas, today's street closures and temporary no-parking
  signs, and every kind of parking ticket written there.
- **I'm walking:** within a distance you pick (100 to 500 m) of a spot on the map, an address or where you are, what
  gets reported to police, what do people call police about, and how often have people walking been hit by cars, when
  and why? Police reports of violence, robbery and drug offenses, calls to police, pedestrian injury crashes, and the
  Vision Zero High Injury Network.

All from [DataSF](https://data.sf.gov), and not 100% accurate: the city's data misses temporary changes, so the posted
signs are what count; [DATA_SOURCES.md](DATA_SOURCES.md) lists which dataset is used for what, and
which were left out. A sister project to [LA Street Rules](https://citina.github.io/ticket-clock/streets/)
([ticket-clock](https://github.com/citina/ticket-clock)), and built the same way: one hand-written page, no map library,
data split into small map cells, rebuilt weekly. Live at **https://citina.github.io/sf-streets/**.

**Status:** both sides are built, over DataSF's 41 Analysis Neighborhoods and all 15,142 blocks. Search finds any
street, a house number on it, or a neighborhood. A block can be linked on the driving side (`#drive/13060000`), and a
spot and distance on the walking side (`#walk/@37.76411,-122.42181/250m`).

- **Driving:** for the time and stay picked, each side of a block is colored on the map (free, pay, have to move, no
  parking), and the card says why: street cleaning (drawn as its sign, with the next dates and how often a cleaning day
  got ticketed), meters with their hours, rates and limits, time limits and permit areas, tow-away hours, closures and
  temporary no-parking signs. Then every kind of ticket written there in the last two years (2.5M across the city,
  placed by the address on each ticket), city-run garages nearby, car break-ins and cameras. A summary covers parking
  tickets across the city.
- **Walking:** police reports (violence and robbery, drug offenses), calls to police and pedestrian crashes within the
  distance picked, by daylight or after dark, with times of day and ranks against every intersection; the map shows the
  High Injury Network, police reports and calls at corners, and neighborhoods shaded citywide. A summary covers the
  whole city: when and where people walking were hit and violence and robbery was reported, around the places visitors
  go, and totals per year.

See [PLAN.md](PLAN.md) for how it works and what's still open.

`hoods.py` writes `docs/hoods.json`, the neighborhood outlines. The file is committed, so run it again only if DataSF
updates the layer. The block data in `docs/data/` isn't committed: every Monday `.github/workflows/weekly.yml` runs
`fetch_sf.py` and `analyze_sf.py`, checks the counts against last week's (a drop of more than 10% stops it, and last
week's data stays up), and publishes `docs/data/` as the `sf-data` release. Parking tickets come a month at a time and
are kept between runs in the Actions cache, so a run downloads only the last two months and those whose copy is over
four weeks old (a run without the cache takes about 20 minutes more). Street closures and temporary no-parking signs
aren't in the release: the page loads them from data.sf.gov when it opens. `pages.yml` then deploys `docs/` to GitHub
Pages with that release unpacked into it; it also deploys on every push that changes `docs/`. To rebuild by hand, run
the weekly workflow from the Actions tab (its `force` box publishes past the count check).

## Preview

```
python3 fetch_sf.py      # data.sf.gov -> data/raw/ (about 250 MB; the first run takes about 25 minutes)
python3 analyze_sf.py    # data/raw/ -> docs/data/
python3 -m http.server 8765 --directory docs
```

then open http://localhost:8765/ (add `#walk` for the walking view).
