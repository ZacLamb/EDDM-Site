# ZipCarrd site generator

This folder is the source for the live site at the repo root. It isn't part
of the deployed site itself — it's what builds it.

- `generate_site.py` — builds the homepage, the "How It Works" page, the
  New England hub, one index page per state, one programmatic SEO landing
  page per town, and the blog (index + one page per post), all from the
  same shared design system in `../assets/style.css`.
- `towns.json` — the town data, grouped by state. Currently covers all six
  New England states (Connecticut, Maine, Massachusetts, New Hampshire,
  Rhode Island, Vermont). Cleaned up Sept 2026 to remove a handful of
  entries (`GECC`, `IRS`, `EMC`, `NETC`, `BTV`, `S BTV`, `SMC`, `UVM`) that
  turned out to be unique-ZIP-code names for organizations/facilities, not
  actual towns — each one had quietly gotten its own live route page.
- `town_coords.json` — real town centroids (`"State/Town" -> [lat, lng]`),
  used by `nearby_towns()` in `generate_site.py` to link each town page to
  towns that are actually close by, instead of just the next few towns
  alphabetically. Built by `tools/build_town_coords.py`; see that script's
  docstring for how and when to re-run it. A town missing a coordinate
  falls back to the old alphabetical-adjacency method automatically.
- `generate_town_content.py` — calls the Claude API to write one unique
  paragraph of copy per town, and caches the results in `town_content.json`.
  `generate_site.py` reads that cache (if it exists) and drops each town's
  paragraph into an "About" section on that town's page. A town with no
  cached paragraph yet still builds fine — it just skips that section.
- `town_content.json` — the cache written by `generate_town_content.py`.
  Committed to the repo so a build never needs to call the API. Safe to
  hand-edit or delete individual entries (a deleted entry gets regenerated
  next run).
- `generate_blog_post.py` — calls the Claude API to write one new evergreen
  blog post per run (see "Blog posts" below), and caches results in
  `blog_posts.json`.
- `blog_topics.json` — the curated rotation of topic angles the blog
  generator works through, in order. `blog_state.json` tracks which one is
  next and when the last post was written.
- `requirements.txt` — Python dependencies for `generate_town_content.py`
  and `generate_blog_post.py` (just the `anthropic` package;
  `generate_site.py` itself has none). `tools/build_town_coords.py` is a
  separate, dev-only maintenance script with its own dependency — see its
  docstring.

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

## Blog posts (programmatic SEO, on a schedule)

The blog writes itself, a little at a time. `generate_blog_post.py` writes
one new evergreen post per run — direct-mail marketing education aimed at
local business owners, rotating through the topic list in
`blog_topics.json` so it never repeats an angle until it's worked through
the whole list. `generate_site.py` reads whatever's cached in
`blog_posts.json` and builds `/blog/` (the index) plus one page per post,
including linking each post to a couple of state route hubs and dropping a
small "From the Blog" module into every town page, state page, and the
homepage.

The **"Generate blog post & rebuild site"** GitHub Actions workflow (see
`.github/workflows/` at the repo root) runs this automatically:

1. Uses the same `ANTHROPIC_API_KEY` repo secret as the town-content
   workflow (add it once, both workflows use it).
2. Runs on a daily schedule, but `generate_blog_post.py` itself decides
   whether a post is actually due — by default it waits at least 3 days
   since the last one (`ZIPCARRD_BLOG_INTERVAL_DAYS` in the workflow file).
   Running the check daily instead of on a "every 3 days" cron keeps the
   spacing accurate across month boundaries, where a naive `*/3` cron
   schedule would otherwise drift.
3. When a post is due, it writes it, rebuilds the site, and pushes to
   `main` — same as the town-content workflow. When it isn't due yet, the
   run does nothing and there's nothing to commit.
4. You can also trigger it manually from the Actions tab, with a "force"
   option to write a post immediately regardless of spacing (useful for
   testing).

To change the pace, edit `ZIPCARRD_BLOG_INTERVAL_DAYS` in
`.github/workflows/generate-blog-post.yml`. To change what it writes
about, edit or extend `blog_topics.json` — each entry is `{"key": ...,
"angle": ...}`, and the angle is the actual brief handed to the model.

To run it locally instead:

```
cd generator
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
python3 generate_blog_post.py --force   # ignore the day gate, write one post now
python3 generate_site.py                # rebuild dist/ with the new post
```

## Domain

The `DOMAIN` constant at the top of `generate_site.py` is set to
`https://zipcarrd.com` and is used for canonical URLs, Open Graph tags,
and the sitemap. Update it there if the domain ever changes.
