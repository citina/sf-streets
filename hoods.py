#!/usr/bin/env python3
"""Write docs/hoods.json: the neighborhood outlines SF Streets draws on its city-wide map.

They're DataSF's Analysis Neighborhoods (dataset j2bu-swwd, public domain under the ODC PDDL): 41 neighborhoods
that cover the whole city, Treasure Island included. They rarely change, so the file is committed and this only
needs running again if the city updates the layer.

Shapes are simplified to about 2 m. Where two neighborhoods share a border, the border is simplified the same way
on both sides, so no gaps open between them when the map is zoomed in. Tiny pieces (under 500 m², bits of piers
and shoreline) are left out. Each neighborhood is [name, ring, ring, ...]; a ring is its first point in zoom-17
Web Mercator pixels (the page's map units before its local shift), then the step to each next point, all whole
pixels (about 0.95 m in San Francisco).
"""
import json
import math
import urllib.request
from collections import defaultdict
from pathlib import Path

URL = "https://data.sf.gov/resource/j2bu-swwd.geojson?$limit=1000"
OUT = Path(__file__).resolve().parent / "docs" / "hoods.json"
N17 = 2 ** 17 * 256
TOL = 2.0            # simplification tolerance, zoom-17 pixels
MIN_AREA = 500       # m²; smaller pieces are dropped
PX_M = 156543.03392 * math.cos(math.radians(37.76)) / 2 ** 17   # metres per zoom-17 pixel in SF


def z17(lon, lat):
    r = math.radians(lat)
    return (lon + 180) / 360 * N17, (1 - math.log(math.tan(r) + 1 / math.cos(r)) / math.pi) / 2 * N17


def area(pts):
    return abs(sum(ax * by - bx * ay for (ax, ay), (bx, by) in zip(pts, pts[1:] + pts[:1]))) / 2


def dp(pts, keep, i, j):
    """Douglas-Peucker between pts[i] and pts[j] (both kept): marks the points to keep in between."""
    (ax, ay), (bx, by) = pts[i], pts[j]
    dx, dy = bx - ax, by - ay
    n = math.hypot(dx, dy)
    best, far = -1.0, None
    for k in range(i + 1, j):
        px, py = pts[k]
        d = abs(dx * (py - ay) - dy * (px - ax)) / n if n else math.hypot(px - ax, py - ay)
        if d > best:
            best, far = d, k
    if far is not None and best > TOL:
        keep[far] = True
        dp(pts, keep, i, far)
        dp(pts, keep, far, j)


with urllib.request.urlopen(URL, timeout=120) as r:
    feats = json.load(r)["features"]

# every ring as a list of source points (lon, lat), without the repeated closing point
hoods = []
for f in sorted(feats, key=lambda f: f["properties"]["nhood"]):
    rings = [ring[:-1] if ring[0] == ring[-1] else ring
             for poly in f["geometry"]["coordinates"] for ring in poly]
    hoods.append((f["properties"]["nhood"].strip(), rings))

# which rings each source point is on; a point is a node (always kept) where that set changes along a ring,
# so a shared border runs between the same two nodes on both sides and simplifies to the same line
on = defaultdict(set)
for h, (_, rings) in enumerate(hoods):
    for k, ring in enumerate(rings):
        for p in ring:
            on[tuple(p)].add((h, k))

out, n_pts, dropped = [], 0, 0
for name, rings in hoods:
    flat_rings = []
    for ring in rings:
        pts = [z17(*p) for p in ring]
        if area(pts) * PX_M ** 2 < MIN_AREA:
            dropped += 1
            continue
        m = len(ring)
        keep = [on[tuple(ring[i])] != on[tuple(ring[i - 1])] or on[tuple(ring[i])] != on[tuple(ring[(i + 1) % m])]
                for i in range(m)]
        if not any(keep):   # a ring nobody shares, like the shoreline of an island: start from its first point
            keep[0] = True
        if sum(keep) == 1:   # and the point farthest from it, so the ring has two ends to simplify between
            s = keep.index(True)
            keep[max(range(m), key=lambda i: math.dist(pts[i], pts[s]))] = True
        nodes = [i for i in range(m) if keep[i]]
        # simplify each run between nodes, going round the ring (the last run wraps past the end)
        ext = pts + pts
        kext = keep + keep
        for a, b in zip(nodes, nodes[1:] + [nodes[0] + m]):
            dp(ext, kext, a, b)
        kept = [(round(x), round(y)) for i, (x, y) in enumerate(pts) if kext[i] or kext[i + m]]
        kept = [p for i, p in enumerate(kept) if p != kept[i - 1]]
        if len(kept) < 3:
            continue
        flat = list(kept[0])
        for (ax, ay), (bx, by) in zip(kept, kept[1:]):
            flat += [bx - ax, by - ay]
        flat_rings.append(flat)
        n_pts += len(kept)
    out.append([name, *flat_rings])

OUT.write_text(json.dumps({"src": "DataSF Analysis Neighborhoods (j2bu-swwd), ODC PDDL", "h": out},
                          separators=(",", ":")))
print(f"{len(out)} neighborhoods, {n_pts:,} points, {dropped} tiny pieces left out, "
      f"{OUT.stat().st_size / 1024:.0f} KB -> {OUT}")
