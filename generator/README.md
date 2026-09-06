# RouteGrange site generator

This folder is not part of the live site — it's what built it.

- `generate_site.py` — builds the whole site (homepage, how-it-works,
  the New England hub, one index page per state, and one page per
  town) from `towns.json` into a `dist/` folder.
- `towns.json` — town/city names per state, sourced from a public
  places dataset. Currently: Connecticut, Maine, Massachusetts, New
  Hampshire, Rhode Island, Vermont (1,868 towns).

To add more states (e.g. expanding beyond New England), add entries
to `towns.json` under a new state name and re-run:

    python3 generate_site.py

then copy the contents of the new `dist/` over the site root.
