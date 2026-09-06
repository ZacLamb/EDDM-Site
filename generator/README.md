# ZipCarrd site generator

This folder is the source for the live site at the repo root. It isn't part
of the deployed site itself — it's what builds it.

- `generate_site.py` — builds the homepage, the "How It Works" page, the
  New England hub, one index page per state, and one programmatic SEO
  landing page per town, all from the same shared design system in
  `../assets/style.css`.
- `towns.json` — the town data, grouped by state. Currently covers all six
  New England states (Connecticut, Maine, Massachusetts, New Hampshire,
  Rhode Island, Vermont).

## Adding more states / towns

1. Add the new state (and its list of towns) as a key in `towns.json`.
2. Run `python3 generate_site.py` from this folder.
3. The script writes the full site — including the new state's pages —
   into `../dist/` relative to this folder is not used; instead it always
   rebuilds into a `dist/` folder next to `generate_site.py`. Copy that
   output over the live site files at the repo root (everything except
   this `generator/` folder) and commit/push as usual.

## Domain

The `DOMAIN` constant at the top of `generate_site.py` is set to
`https://zipcarrd.com` and is used for canonical URLs, Open Graph tags,
and the sitemap. Update it there if the domain ever changes.
