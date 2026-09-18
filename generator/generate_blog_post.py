#!/usr/bin/env python3
"""
Writes ONE new evergreen blog post per run, using the Claude API, and adds
it to blog_posts.json. Meant to run on a schedule (see
.github/workflows/generate-blog-post.yml) so the blog grows a post every
few days without anyone touching it.

Design notes:
  - Topics live in blog_topics.json (a curated, human-written list of
    angles -- see that file). This script rotates through them in order,
    tracking its place in blog_state.json. When it wraps around and reuses
    a topic, it shows the model the previous post's title/opening and
    explicitly asks for a different angle, so a second lap doesn't just
    reprint the same post.
  - Cadence is enforced HERE, not by the cron schedule, because GitHub
    Actions cron on a "every N days" field drifts across month boundaries.
    Instead the workflow can run on a plain daily cron, and this script
    checks blog_state.json's last_generated date and exits without writing
    anything (and without calling the API) if it's too soon. That gives a
    true "every N days" cadence regardless of the calendar.
  - generate_site.py reads blog_posts.json at build time and never calls
    the API itself, same pattern as generate_town_content.py /
    town_content.json.
  - The prompt asks for a single JSON object (title/description/body) so
    parsing doesn't depend on the model following a markdown convention
    exactly.

Usage:
  export ANTHROPIC_API_KEY=sk-ant-...
  python3 generate_blog_post.py                 # normal scheduled run
  python3 generate_blog_post.py --force          # ignore the day gate (testing)
"""
import argparse
import datetime
import json
import os
import random
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SITE_ROOT = os.path.dirname(HERE)
TOPICS_PATH = os.path.join(HERE, "blog_topics.json")
POSTS_PATH = os.path.join(HERE, "blog_posts.json")
STATE_PATH = os.path.join(HERE, "blog_state.json")
TOWNS_PATH = os.path.join(SITE_ROOT, "towns.json")

MODEL = os.environ.get("ZIPCARRD_MODEL", "claude-haiku-4-5")
MIN_DAYS_BETWEEN_POSTS = int(os.environ.get("ZIPCARRD_BLOG_INTERVAL_DAYS", "3"))

PROMPT_TEMPLATE = """You are writing one blog post for the ZipCarrd blog. ZipCarrd is a USPS \
EDDM mailer co-op for local businesses: for a flat $250, a business gets a professionally \
designed, full-color postcard delivered to every home on a real residential carrier route near \
them -- roughly 2,500 addresses -- with one business per category exclusivity on that route, and \
no mailing list to buy.

The blog's audience is local business owners deciding how to spend a limited marketing budget. \
The tone is practical, plainspoken, and a little skeptical of hype -- more "here's how this \
actually works" than "buy now." It should read as genuinely useful marketing education, not a \
thinly-veiled ad, even though it can reference ZipCarrd's own offer naturally where relevant.

Today's post angle: {angle}

{repeat_note}Write a complete blog post as a single JSON object with exactly these keys:
- "title": a specific, non-clickbait title (under 70 characters, no colon-subtitle padding)
- "description": one sentence (130-155 characters) for the meta description / index card
- "body": the full post body, 500-650 words, as plain text with blocks separated by a blank \
line (double newline). Most blocks are paragraphs. You may use 1-2 blocks that are just a short \
subheading on their own line, prefixed with "## " (e.g. "## Start with the offer, not the design"), \
to break up the post -- use these sparingly, only where they genuinely help.

Rules for the body:
- Do not invent specific statistics, percentages, studies, or dollar figures you can't actually \
know are true. General, defensible claims are fine ("mail tends to sit around longer than a \
scrolling feed post"); a fabricated "73% of homeowners..." is not.
- Do not start the post by restating the title.
- Write in second person to the business owner ("you", "your business") more often than not.
- End the body with one natural closing paragraph that invites the reader to see what their own \
route would reach -- do not write a "Sources" section, do not write a call-to-action button, \
that's handled separately by the page template.
- No markdown headers other than the "## " subheading blocks described above. No bullet lists, \
no bold/italic markdown syntax, no emoji.

Return ONLY the JSON object. No markdown code fence, no commentary before or after it."""


def slugify(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return re.sub(r"-+", "-", s).strip("-")


def load_json(path, default):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return default


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=1, sort_keys=True)


def days_since(date_str):
    try:
        then = datetime.date.fromisoformat(date_str)
    except (TypeError, ValueError):
        return None
    return (datetime.date.today() - then).days


def strip_code_fence(text):
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n", "", text)
        text = re.sub(r"\n```$", "", text)
    return text.strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Ignore the day-spacing gate (for testing)")
    args = parser.parse_args()

    topics = load_json(TOPICS_PATH, [])
    if not topics:
        print("ERROR: blog_topics.json is empty or missing", file=sys.stderr)
        sys.exit(1)

    posts = load_json(POSTS_PATH, {})
    state = load_json(STATE_PATH, {"next_topic_index": 0, "last_generated": None})

    since = days_since(state.get("last_generated"))
    if not args.force and since is not None and since < MIN_DAYS_BETWEEN_POSTS:
        print(f"Last post was {since} day(s) ago; waiting until {MIN_DAYS_BETWEEN_POSTS}. Nothing to do.")
        return

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: set ANTHROPIC_API_KEY", file=sys.stderr)
        sys.exit(1)
    try:
        import anthropic
    except ImportError:
        print("ERROR: pip install anthropic", file=sys.stderr)
        sys.exit(1)

    idx = state.get("next_topic_index", 0) % len(topics)
    topic = topics[idx]
    lap = state.get("next_topic_index", 0) // len(topics)  # 0 = first pass through the list

    repeat_note = ""
    if lap > 0:
        prior = next((p for p in posts.values() if p.get("topic_key") == topic["key"]), None)
        if prior:
            repeat_note = (
                f'This topic was already covered once before, in a post titled "{prior["title"]}" '
                f'that opened with: "{prior["body"][:160]}...". Write a genuinely different post -- '
                f"a different angle, a different opening, different specifics -- not a reword of that one.\n\n"
            )

    towns = load_json(TOWNS_PATH, {})
    state_names = list(towns.keys())
    state_links = random.sample(state_names, k=min(3, len(state_names))) if state_names else []

    prompt = PROMPT_TEMPLATE.format(angle=topic["angle"], repeat_note=repeat_note)
    client = anthropic.Anthropic(api_key=api_key)
    resp = client.messages.create(
        model=MODEL,
        max_tokens=1600,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = "".join(block.text for block in resp.content if block.type == "text").strip()
    raw = strip_code_fence(raw)
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"ERROR: model did not return valid JSON: {e}\n---\n{raw}\n---", file=sys.stderr)
        sys.exit(1)

    title = parsed["title"].strip()
    slug = slugify(title)
    original_slug = slug
    n = 2
    while slug in posts:
        slug = f"{original_slug}-{n}"
        n += 1

    posts[slug] = {
        "title": title,
        "description": parsed["description"].strip(),
        "date": datetime.date.today().isoformat(),
        "topic_key": topic["key"],
        "body": parsed["body"].strip(),
        "state_links": state_links,
    }
    save_json(POSTS_PATH, posts)

    state["next_topic_index"] = idx + 1
    state["last_generated"] = datetime.date.today().isoformat()
    save_json(STATE_PATH, state)

    print(f"Wrote new post: {slug} (topic: {topic['key']}, lap {lap}). {len(posts)} posts total.")


if __name__ == "__main__":
    main()
