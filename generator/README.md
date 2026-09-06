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
- `generate_town_content.py` — calls the Claude API to write one unique
  paragraph of copy per town, and caches the results in `town_content.json`.
  `generate_site.py` reads that cache (if it exists) and drops each town's
  paragraph into an "About" section on that town's page. A town with no
  cached paragraph yet still builds fine — it just skips that section.
- `town_content.json` — the cache written by `generate_town_content.py`.
  Committed to the repo so a build never needs to call the API. Safe to
  hand-edit or delete individual entries (a deleted entry gets regenerated
  next run).
- `requirements.txt` — Python dependencies for `generate_town_content.py`
  (just the `anthropic` package; `generate_site.py` itself has none).

## Adding more states / towns

1. Add the new state (and its list of towns) as a key in `towns.json`.
2. Run `python3 generate_site.py` from this folder.
3. The script always rebuilds into a `dist/` folder next to itself. Copy
   that output over the live site files at the repo root (everything
   except this `generator/` folder) and commit/push as usual.

## Generating unique per-town copy (programmatic SEO)

Every town page shares one template, so without unique copy they'd all
read as the same page with the town name swapped in — bad for SEO on a
page set this size. `generate_town_content.py` fixes that by asking the
Claude API to write one short, town-appropriate paragraph per town.

The easiest way to run it is the **"Generate town content & rebuild
site"** GitHub Actions workflow (see `.github/workflows/` at the repo
root) — no local setup needed, just:

1. Add an `ANTHROPIC_API_KEY` repo secret (Settings -> Secrets and
   variables -> Actions -> New repository secret) with a key from
   [console.anthropic.com](https://console.anthropic.com).
2. Go to the **Actions** tab -> **Generate town content & rebuild site**
   -> **Run workflow**. Leave "limit" blank to fill in every missing
   town, or put in a small number (e.g. `5`) to test first.
3. The workflow generates the missing paragraphs, rebuilds the site, and
   pushes the result to `main`, which Railway auto-deploys.

Re-running the workflow later only fills in towns that are still
missing — it never re-generates (and never re-bills) a town that
already has cached copy.

To run it locally instead:

```
cd generator
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
python3 generate_town_content.py --limit 5   # test on a few towns first
python3 generate_town_content.py             # fill in everything else
python3 generate_site.py                     # rebuild dist/ with the new copy
```

## Domain

The `DOMAIN` constant at the top of `generate_site.py` is set to
`https://zipcarrd.com` and is used for canonical URLs, Open Graph tags,
and the sitemap. Update it there if the domain ever changes.
