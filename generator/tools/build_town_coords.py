#!/usr/bin/env python3
"""
One-off maintenance script -- NOT part of the build/CI pipeline.

Builds ../town_coords.json: a static {"State/Town": [lat, lng]} lookup used
by generate_site.py to pick real geographically-nearby towns for each town
page's "Nearby Routes" section, instead of the old alphabetical-adjacency
fallback.

Source data: the `zipcodes` PyPI package (ships its own offline ZIP Code
database, no network access needed at run time -- see
https://pypi.org/project/zipcodes/). For each town in towns.json, this
looks up matching ZIP records in that town's state by:
  1. exact match on the ZIP's primary city name, then
  2. exact match against that ZIP's `acceptable_cities` aliases (handles
     New England villages that share a larger town's ZIP code, e.g.
     "South Hampton, NH" -> the East Kingston ZIP, "Northumberland, NH"
     -> the Groveton ZIP).
When a town matches multiple ZIP codes, its coordinate is the average of
all matches.

This only needs to be re-run when towns.json's town list actually changes
(a new state/town added). Re-run:

    pip install zipcodes
    python3 generator/tools/build_town_coords.py

and commit the updated generator/town_coords.json.
"""
import json
import os

try:
    import zipcodes
except ImportError:
    raise SystemExit("pip install zipcodes  (one-time, dev-only dependency)")

HERE = os.path.dirname(os.path.abspath(__file__))
GEN_ROOT = os.path.dirname(HERE)
TOWNS_PATH = os.path.join(GEN_ROOT, "towns.json")
OUT_PATH = os.path.join(GEN_ROOT, "town_coords.json")

STATE_ABBR = {
    "Connecticut": "CT",
    "Maine": "ME",
    "Massachusetts": "MA",
    "New Hampshire": "NH",
    "Rhode Island": "RI",
    "Vermont": "VT",
}


def build_index():
    """(name_lower, state_abbr) -> list of (lat, lng), covering both the
    primary city name and every acceptable-city alias for that ZIP."""
    idx = {}
    for z in zipcodes.list_all():
        if z["state"] not in STATE_ABBR.values():
            continue
        try:
            lat, lng = float(z["lat"]), float(z["long"])
        except (TypeError, ValueError):
            continue
        names = [z["city"]] + list(z.get("acceptable_cities") or [])
        for name in names:
            key = (name.strip().lower(), z["state"])
            idx.setdefault(key, []).append((lat, lng))
    return idx


def main():
    towns = json.load(open(TOWNS_PATH))
    idx = build_index()

    coords = {}
    unmatched = []
    for state, town_list in towns.items():
        ab = STATE_ABBR[state]
        for town in town_list:
            key = (town.strip().lower(), ab)
            matches = idx.get(key)
            if not matches:
                unmatched.append(f"{town}, {state}")
                continue
            lat = sum(m[0] for m in matches) / len(matches)
            lng = sum(m[1] for m in matches) / len(matches)
            coords[f"{state}/{town}"] = [round(lat, 5), round(lng, 5)]

    json.dump(coords, open(OUT_PATH, "w"), indent=1, sort_keys=True)
    total = sum(len(v) for v in towns.values())
    print(f"Matched {len(coords)}/{total} towns. Wrote {OUT_PATH}")
    if unmatched:
        print(f"Unmatched ({len(unmatched)}) -- these fall back to alphabetical nearby-towns:")
        for u in unmatched:
            print(f"  {u}")


if __name__ == "__main__":
    main()
