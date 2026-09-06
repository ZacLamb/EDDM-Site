#!/usr/bin/env python3
"""
Generates one short, unique "why ZipCarrd works here" paragraph per town,
using the Claude API, and caches the results to town_content.json.

This is what keeps ~1,900 programmatic-SEO town pages from all reading as
the same template with the town name swapped in -- each page gets a real
paragraph of unique prose about mailing co-ops and community commerce.

Design notes:
  - Content is cached in town_content.json (committed to the repo), keyed
    by "State/Town". Re-running this script only fills in towns that are
    still missing -- it never re-generates (and never re-bills) a town
    that already has cached copy. Delete an entry from the JSON if you
    want it regenerated.
  - generate_site.py reads this same JSON at build time. A build never
    calls the API itself -- it only reads whatever's already cached, so
    the site regenerates instantly and for free even if this script
    hasn't been run recently.
  - The prompt deliberately forbids inventing specific unverifiable
    facts (population figures, street names, named local businesses,
    landmarks) since the model has no real per-town data source here --
    it only knows the town and state names. It's told to write general,
    true-for-the-area copy instead of hallucinated specifics.

Usage:
  export ANTHROPIC_API_KEY=sk-ant-...
  python3 generate_town_content.py            # fill in every missing town
  python3 generate_town_content.py --limit 5  # test on just 5 towns first
"""
import argparse
import json
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
SITE_ROOT = os.path.dirname(HERE)
TOWNS_PATH = os.path.join(SITE_ROOT, "towns.json")
CONTENT_PATH = os.path.join(HERE, "town_content.json")

MODEL = os.environ.get("ZIPCARRD_MODEL", "claude-haiku-4-5")
MAX_WORKERS = int(os.environ.get("ZIPCARRD_WORKERS", "8"))

PROMPT_TEMPLATE = """You are writing one short paragraph of website copy for a local page on \
ZipCarrd, a USPS EDDM co-op mailer service. Sixteen local businesses in a town split one \
professionally designed postcard and it gets mailed to every home on a real residential \
carrier route near them, for $250 flat per business.

Write a single paragraph (55-80 words) for the town of {town}, {state}. It should:
- Speak to a local business owner in {town} about why a shared neighborhood mailer reaches
  their real customers better than a mailing list or digital ads.
- Sound specific to a town like {town} in {state} in general character and tone (small-town
  Main Street commerce, community, neighbors), WITHOUT inventing specific facts you can't know
  -- no invented population numbers, no named streets, no named local businesses or landmarks,
  no made-up statistics about {town} itself.
- Not repeat the phrase "shared mailer" more than once, and not start with the town name.
- Be plain, confident marketing prose -- no headers, no bullet points, no quotation marks
  around the whole thing, just the paragraph text itself.

Return ONLY the paragraph text, nothing else."""


def load_towns():
    with open(TOWNS_PATH) as f:
        return json.load(f)


def load_cache():
    if os.path.exists(CONTENT_PATH):
        with open(CONTENT_PATH) as f:
            return json.load(f)
    return {}


_lock = threading.Lock()


def generate_one(client, state, town):
    key = f"{state}/{town}"
    prompt = PROMPT_TEMPLATE.format(town=town, state=state)
    resp = client.messages.create(
        model=MODEL,
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(block.text for block in resp.content if block.type == "text").strip()
    return key, text


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="Only generate this many missing towns (for testing)")
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: set ANTHROPIC_API_KEY", file=sys.stderr)
        sys.exit(1)

    try:
        import anthropic
    except ImportError:
        print("ERROR: pip install anthropic", file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    towns = load_towns()
    cache = load_cache()

    todo = []
    for state, town_list in towns.items():
        for town in town_list:
            key = f"{state}/{town}"
            if key not in cache:
                todo.append((state, town))

    if args.limit:
        todo = todo[: args.limit]

    total_towns = sum(len(v) for v in towns.values())
    print(f"{len(cache)}/{total_towns} towns already cached. Generating {len(todo)} more...")

    if not todo:
        print("Nothing to do.")
        return

    done = 0
    errors = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(generate_one, client, state, town): (state, town) for state, town in todo}
        for future in as_completed(futures):
            state, town = futures[future]
            try:
                key, text = future.result()
                with _lock:
                    cache[key] = text
                    done += 1
                    if done % 25 == 0:
                        with open(CONTENT_PATH, "w") as f:
                            json.dump(cache, f, indent=1, sort_keys=True)
                        print(f"  ...{done}/{len(todo)} done (checkpoint saved)")
            except Exception as e:
                errors.append((state, town, str(e)))

    with open(CONTENT_PATH, "w") as f:
        json.dump(cache, f, indent=1, sort_keys=True)

    print(f"Done. {done} generated, {len(errors)} errors. Cache now has {len(cache)}/{total_towns} towns.")
    if errors:
        print("Errors (re-run the script to retry these -- they were left out of the cache):")
        for state, town, err in errors[:20]:
            print(f"  {town}, {state}: {err}")


if __name__ == "__main__":
    main()
