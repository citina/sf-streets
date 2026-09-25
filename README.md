# SF Streets

A map of San Francisco that answers a different question depending on how you're getting around:

- **I'm driving:** can I park on this block now, or at the time I pick, and what gets ticketed here? Street cleaning per
  side, meters and time limits, permit areas, and every kind of parking ticket written there.
- **I'm walking:** how often have people walking here been hit by cars, when, and why, and what's been built to make it
  safer? Pedestrian injury crashes, the Vision Zero High Injury Network, signals, crosswalks and speed limits.

All from [DataSF](https://data.sf.gov). A sister project to [LA Street Rules](https://citina.github.io/ticket-clock/streets/)
([ticket-clock](https://github.com/citina/ticket-clock)), and built the same way: one hand-written page, no map library,
data split into small map cells, rebuilt weekly.

**Status:** the map works, with DataSF's 41 Analysis Neighborhoods and all 15,142 blocks. Search finds any street, a
house number on it, or a neighborhood, and a block can be linked (`#walk/13060000`). The walking side shows the last two
years of pedestrian crashes, the High Injury Network, and police reports at corners (violence and robbery, drugs and
naloxone given for overdoses), by daylight or after dark, with neighborhoods shaded citywide. The driving side shows speed
and red-light cameras and car break-ins; its parking rules and tickets come next. See [PLAN.md](PLAN.md).

`hoods.py` writes `docs/hoods.json`, the neighborhood outlines. The file is committed, so run it again only if DataSF
updates the layer. The block data in `docs/data/` isn't committed (a weekly workflow will publish it, as in
ticket-clock); build it with `fetch_sf.py` and `analyze_sf.py`.

## Preview

```
python3 fetch_sf.py      # data.sf.gov -> data/raw/
python3 analyze_sf.py    # data/raw/ -> docs/data/
python3 -m http.server 8765 --directory docs
```

then open http://localhost:8765/ (add `#walk` for the walking view).
