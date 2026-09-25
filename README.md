# SF Streets

A map of San Francisco that answers a different question depending on how you're getting around:

- **I'm driving:** can I park on this block now, or at the time I pick, and what gets ticketed here? Street cleaning per
  side, meters and time limits, permit areas, and every kind of parking ticket written there.
- **I'm walking:** how often have people walking here been hit by cars, when, and why, and what's been built to make it
  safer? Pedestrian injury crashes, the Vision Zero High Injury Network, signals, crosswalks and speed limits.

All from [DataSF](https://data.sf.gov). A sister project to [LA Street Rules](https://citina.github.io/ticket-clock/streets/)
([ticket-clock](https://github.com/citina/ticket-clock)), and built the same way: one hand-written page, no map library,
data split into small map cells, rebuilt weekly.

**Status:** skeleton. The page layout and the driving/walking switch are in `docs/index.html`; the map, data and cards
come next. See [PLAN.md](PLAN.md) for the data sources, page structure and milestones.

## Preview

```
python3 -m http.server 8765 --directory docs
```

then open http://localhost:8765/ (add `#walk` for the walking view).
