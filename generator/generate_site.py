#!/usr/bin/env python3
"""
ZipCarrd static site generator.
Builds the marketing homepage, a dedicated "how it works" page, a New
England directory hub, one index page per state, and one programmatic
SEO landing page per town — all from the same shared design system.

Run: python3 generate_site.py
Output: ./dist/
"""
import datetime
import json
import os
import re
import shutil

ROOT = os.path.dirname(os.path.abspath(__file__))
# assets/ lives at the deployed site root. When this script sits flat next
# to assets/ (a local build sandbox) that's ROOT itself; when it sits in a
# generator/ subfolder alongside the deployed site (the repo's normal
# layout) assets/ is one level up instead.
if os.path.isdir(os.path.join(ROOT, "assets")):
    SITE_ROOT = ROOT
else:
    SITE_ROOT = os.path.dirname(ROOT)
DIST = os.path.join(ROOT, "dist")
DOMAIN = "https://zipcarrd.com"  # update once the domain is registered
BUILD_DATE = datetime.date.today().isoformat()  # used as sitemap <lastmod>

# Stock photography (hosted externally — direct links, no local copies)
IMG_MAIN_STREET = "https://d8j0ntlcm91z4.cloudfront.net/user_3EmROCl8evT8aLsxpJaXd5oq6pI/hf_20260906_193513_0f56034d-fc4f-41f8-ac0a-c748088cd169.png"
IMG_POSTCARDS = "https://d8j0ntlcm91z4.cloudfront.net/user_3EmROCl8evT8aLsxpJaXd5oq6pI/hf_20260906_193444_dd844cd4-e01b-4d4a-ae53-02b604406a5a.png"
IMG_CARRIER = "https://d8j0ntlcm91z4.cloudfront.net/user_3EmROCl8evT8aLsxpJaXd5oq6pI/hf_20260906_193444_73f1d281-519a-453a-afa0-2f8be914df0e.png"

IMG_ROUTE_MAP = "https://d8j0ntlcm91z4.cloudfront.net/user_3EmROCl8evT8aLsxpJaXd5oq6pI/hf_20260906_213520_47c714b7-1235-4e2b-b776-9634e0863ca3.png"
IMG_POSTCARD_PROOF = "https://d8j0ntlcm91z4.cloudfront.net/user_3EmROCl8evT8aLsxpJaXd5oq6pI/hf_20260906_213520_b4eac3d3-08a5-427f-9148-5585f7d549c4.png"
IMG_TOWN_GREEN = "https://d8j0ntlcm91z4.cloudfront.net/user_3EmROCl8evT8aLsxpJaXd5oq6pI/hf_20260906_213520_eb1e4ea0-845f-4d2e-bc52-f2d1d27a847a.png"
IMG_MAILBOXES = "https://d8j0ntlcm91z4.cloudfront.net/user_3EmROCl8evT8aLsxpJaXd5oq6pI/hf_20260906_213520_15f8bd1f-c276-4cb1-bbe7-7bf19b16fbc8.png"

# Logo mark -- a circular seal (sprout + route, "ZIPCARRD" / "EVERY DOOR,
# EVERY TIME" ring text baked in) chosen by the client. Shipped as a local
# asset rather than hotlinked, so it doesn't depend on any third-party host.
LOGO_ICON = "/assets/logo.png"

PHOTO_BAND = f"""  <section class="photo-band">
    <div class="wrap">
      <div class="photo-grid">
        <div class="photo-card"><img src="{IMG_MAIN_STREET}" alt="A local Main Street lined with independent businesses" loading="lazy"><p class="cap">Every town has one</p></div>
        <div class="photo-card"><img src="{IMG_POSTCARDS}" alt="A stack of postcards ready for a shared mailer" loading="lazy"><p class="cap">One flat price, every mailbox</p></div>
        <div class="photo-card"><img src="{IMG_CARRIER}" alt="A mail carrier delivering to every home on the route" loading="lazy"><p class="cap">Every home. Every time.</p></div>
      </div>
    </div>
  </section>

"""


def hero_photo_bg(img, alt, offset=False):
    """A faded full-bleed photo behind a hero section's content."""
    cls = "hero-photo-bg offset" if offset else "hero-photo-bg"
    return f"""    <div class="{cls}"><img src="{img}" alt="{alt}" loading="eager"></div>
"""


def feature_photo(img, alt, cap, eyebrow, heading, text, reverse=False):
    """A two-column image + copy band, reused across inner pages."""
    rev = " reverse" if reverse else ""
    return f"""  <section class="feature-photo{rev}">
    <div class="wrap">
      <div class="feature-photo-grid">
        <div class="feature-photo-card"><img src="{img}" alt="{alt}" loading="lazy"><p class="cap">{cap}</p></div>
        <div class="feature-photo-copy">
          <p class="eyebrow">{eyebrow}</p>
          <h2>{heading}</h2>
          <p>{text}</p>
        </div>
      </div>
    </div>
  </section>

"""

with open(os.path.join(ROOT, "towns.json")) as f:
    TOWNS = json.load(f)  # {"Massachusetts": ["Abington", ...], ...}

# AI-generated per-town copy for the programmatic SEO pages, keyed by
# "State/Town". Produced by generator/generate_town_content.py and committed
# to the repo. Optional -- a build works fine (falling back to generic copy)
# for any town not yet in the cache, so content can roll out incrementally.
TOWN_CONTENT_PATH = os.path.join(ROOT, "town_content.json")
if os.path.exists(TOWN_CONTENT_PATH):
    with open(TOWN_CONTENT_PATH) as f:
        TOWN_CONTENT = json.load(f)
else:
    TOWN_CONTENT = {}

STATE_SLUGS = {name: re.sub(r"\s+", "-", name.lower()) for name in TOWNS}


def slugify(name: str) -> str:
    s = name.lower().strip()
    s = s.replace("&", "and")
    s = re.sub(r"[’']", "", s)
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s


def write(path: str, content: str) -> None:
    full = os.path.join(DIST, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(content)


BRAND_MARK = f"""<img src="{LOGO_ICON}" alt="ZipCarrd" width="22" height="22">"""


def head(title: str, description: str, canonical: str, schema: str = "", og_image: str = None) -> str:
    img = og_image or IMG_MAIN_STREET
    schema_block = f'<script type="application/ld+json">{schema}</script>\n' if schema else ""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{description}">
<link rel="canonical" href="{DOMAIN}{canonical}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{description}">
<meta property="og:type" content="website">
<meta property="og:url" content="{DOMAIN}{canonical}">
<meta property="og:image" content="{img}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title}">
<meta name="twitter:description" content="{description}">
<meta name="twitter:image" content="{img}">
<link rel="icon" type="image/png" href="{LOGO_ICON}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400..900;1,9..144,500..700&family=Karla:wght@400;500;700&family=Courier+Prime:wght@400;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/assets/style.css">
{schema_block}</head>
<body>
"""


def topbar(active: str = "") -> str:
    return f"""<header class="topbar">
  <div class="topbar-inner">
    <a class="brand" href="/" aria-label="ZipCarrd">
      <span class="brand-mark brand-mark-lg">{BRAND_MARK}</span>
    </a>
    <input type="checkbox" id="nav-toggle" class="nav-toggle-input">
    <label for="nav-toggle" class="nav-toggle" aria-label="Menu">
      <span></span><span></span><span></span>
    </label>
    <nav class="primary-nav">
      <a href="/new-england.html">Find Your Town</a>
      <a href="/how-it-works.html">How It Works</a>
      <a href="/#pricing">Pricing</a>
      <a class="btn btn-primary nav-cta-mobile" href="/#claim">Claim a Spot</a>
    </nav>
    <a class="btn btn-primary nav-cta" href="/#claim">Claim a Spot</a>
  </div>
</header>
"""


CLAIM_WEBHOOK_URL = "https://services.leadconnectorhq.com/hooks/EKnlvu3m2cubdvna2PD4/webhook-trigger/cb4dd36d-c0d7-4295-8525-f52a08383b37"

FOOT_SCRIPT = f"""<script>
  (function () {{
    var WEBHOOK_URL = "{CLAIM_WEBHOOK_URL}";
    var form = document.getElementById('claim-form');
    var confirm = document.getElementById('claim-confirm');
    if (!form) return;
    var town = '', state = '';
    try {{
      var params = new URLSearchParams(window.location.search);
      town = params.get('town') || '';
      state = params.get('state') || '';
      if (town) {{
        var zip = document.getElementById('biz-zip');
        if (zip) zip.placeholder = state ? (town + ', ' + state) : town;
      }}
    }} catch (e) {{}}
    form.addEventListener('submit', function (e) {{
      e.preventDefault();
      var payload = {{
        business: form.business.value,
        category: form.category.value,
        zip: form.zip.value,
        phone: form.phone.value,
        email: form.email.value,
        town: town,
        state: state,
        page_url: window.location.href,
        submitted_at: new Date().toISOString()
      }};
      try {{
        fetch(WEBHOOK_URL, {{
          method: 'POST',
          mode: 'no-cors',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify(payload)
        }});
      }} catch (err) {{}}
      confirm.classList.add('show');
      form.querySelectorAll('input').forEach(function (i) {{ i.disabled = true; }});
      form.querySelector('button[type="submit"]').disabled = true;
    }});
  }})();
</script>
"""


def footer() -> str:
    return f"""<footer>
  <div class="wrap">
    <div class="foot-inner">
      <div class="foot-brand">
        <span class="brand-mark brand-mark-lg">
          <img src="{LOGO_ICON}" alt="ZipCarrd">
        </span>
        <span class="mono" style="font-size:0.72rem; color:var(--ink-soft); margin-left:4px;">Every door, one route at a time</span>
      </div>
      <nav class="foot-links">
        <a href="/new-england.html">Find Your Town</a>
        <a href="/how-it-works.html">How It Works</a>
        <a href="/#pricing">Pricing</a>
        <a href="/#claim">Claim a Spot</a>
      </nav>
    </div>
    <div class="foot-bar">
      <span>A Revenue Generating Solutions LLC program</span>
      <span class="mono">EVERY-DOOR ROUTE PROGRAM</span>
    </div>
  </div>
</footer>
{FOOT_SCRIPT}</body>
</html>
"""


CLAIM_SECTION = """  <section id="claim" class="claim">
    <div class="wrap">
      <div class="claim-inner">
        <div class="claim-copy">
          <p class="eyebrow">Claim Your Spot</p>
          <h2>See what your route reaches.</h2>
          <p style="color:var(--ink-soft); font-size:1.05rem; max-width:46ch;">Tell us where your business is and we'll check which route it falls on, exactly how many homes it reaches, and whether your category's still open.</p>
        </div>
        <div class="worksheet">
          <p class="worksheet-title"><span>Route Availability Worksheet</span><span>Form 250-A</span></p>
          <form id="claim-form">
            <div class="field-row">
              <div class="field">
                <label for="biz-name">Business Name</label>
                <input id="biz-name" name="business" type="text" required>
              </div>
              <div class="field">
                <label for="biz-category">Category</label>
                <input id="biz-category" name="category" type="text" placeholder="e.g. HVAC, salon, pizzeria" required>
              </div>
            </div>
            <div class="field">
              <label for="biz-zip">Business Address or ZIP Code</label>
              <input id="biz-zip" name="zip" type="text" required>
            </div>
            <div class="field-row">
              <div class="field">
                <label for="biz-phone">Phone</label>
                <input id="biz-phone" name="phone" type="tel" required>
              </div>
              <div class="field">
                <label for="biz-email">Email</label>
                <input id="biz-email" name="email" type="email" required>
              </div>
            </div>
            <button class="btn btn-primary" type="submit">Check Availability</button>
            <p class="confirm" id="claim-confirm" role="status">Request received — we'll follow up with your route details and open spots shortly.</p>
          </form>
        </div>
      </div>
    </div>
  </section>
"""

CHECK_SVG = '<svg viewBox="0 0 20 20" fill="none"><path d="M4 10.5L8 14.5L16 5.5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>'


HOMEPAGE_SCHEMA = json.dumps({
    "@context": "https://schema.org",
    "@type": "Organization",
    "name": "ZipCarrd",
    "url": DOMAIN,
    "logo": f"{DOMAIN}{LOGO_ICON}",
    "description": "ZipCarrd puts a local business's postcard in every mailbox on a real USPS carrier route for $250 flat.",
    "parentOrganization": {"@type": "Organization", "name": "Revenue Generating Solutions LLC"},
})


def build_homepage():
    title = "ZipCarrd | Reach Every Home Near You for $250 Flat"
    desc = "ZipCarrd puts your postcard in every mailbox on a real USPS carrier route near you — about 2,500 homes — for $250 flat. No mailing list, no design fee, one business per category."
    body = topbar() + f"""
<main id="top">
  <section class="hero" style="border-bottom:1px solid var(--steel-line); padding-bottom:0;">
{hero_photo_bg(IMG_MAIN_STREET, "A local Main Street lined with independent businesses", offset=True)}    <div class="wrap">
      <div class="hero-grid">
        <div>
          <p class="eyebrow">Every Home. One Flat Price.</p>
          <h1 class="display">Reach every home<br>near you.<br><em>For $250 flat.</em></h1>
          <p class="hero-sub">Your postcard lands in every mailbox on a real USPS carrier route near your business — about 2,500 homes — for $250 flat. No mailing list to buy, no design fee, and you're the only business in your category on the route.</p>
          <div class="hero-actions">
            <a class="btn btn-primary" href="#claim">Check My Route</a>
            <a class="btn btn-ghost" href="/new-england.html">Find My Town</a>
          </div>
          <p class="hero-note">No mailing list required &middot; Delivered to every home on the route</p>
        </div>
        <div class="charter">
          <p class="charter-title">Route Charter &middot; Sample</p>
          <div class="charter-box">
            <div class="l1">$250 FLAT</div>
            <div class="l2">EVERY HOME, EVERY TIME</div>
            <div class="l3">ONE CATEGORY &middot; ZIPCARRD</div>
          </div>
          <div class="charter-meta">
            <span>ROUTE TYPE<br><strong>RESIDENTIAL</strong></span>
            <span style="text-align:right;">REACH<br><strong>~2,500 HOMES</strong></span>
          </div>
        </div>
      </div>
    </div>
  </section>

  <section class="stats" style="padding:0; border-radius:0;">
    <div class="wrap" style="padding:0;">
      <div class="stats-inner">
        <div class="stat"><div class="num mono">~2,500</div><div class="label">Homes reached</div></div>
        <div class="stat"><div class="num mono">$0.10</div><div class="label">Roughly, per home reached</div></div>
        <div class="stat"><div class="num mono">$250</div><div class="label">Flat, all in</div></div>
      </div>
    </div>
  </section>

{PHOTO_BAND}
  <section id="how">
    <div class="wrap">
      <div class="section-head">
        <p class="eyebrow">How It Works</p>
        <h2>From carrier route to kitchen counter, in four stops.</h2>
        <p>Every mailer runs the same route, every time — here's what happens between claiming your spot and landing in the mailbox. <a class="callout-link" href="/how-it-works.html">See the full mailing details &rarr;</a></p>
      </div>
      <div class="route-line">
        <div class="route-track"></div>
        <div class="stops">
          <div class="stop"><div class="stop-marker">1</div><p class="stop-label">Stop 01</p><h3>We map your route</h3><p>We pull real carrier-route data for the neighborhood around your business — exact home count, not a zip-code guess.</p></div>
          <div class="stop"><div class="stop-marker">2</div><p class="stop-label">Stop 02</p><h3>You claim a spot</h3><p>16 spots per mailer, one business per category. If a plumber's already in, no other plumber gets on that route.</p></div>
          <div class="stop"><div class="stop-marker">3</div><p class="stop-label">Stop 03</p><h3>We design &amp; print</h3><p>Your listing is laid out professionally and printed in full color — no design fee, no software to learn, nothing for you to do.</p></div>
          <div class="stop"><div class="stop-marker">4</div><p class="stop-label">Stop 04</p><h3>It reaches every home</h3><p>Delivered to every address on the route — renters and owners, no purchased list required.</p></div>
        </div>
      </div>
    </div>
  </section>

{feature_photo(
    IMG_MAILBOXES,
    "A row of rural mailboxes on wooden posts along a residential route",
    "Rain, shine, or first snow",
    "Every Address, Every Time",
    "The route doesn't skip houses.",
    "EDDM delivers to every address on the carrier route the Postal Service already walks — renters and owners alike, no purchased list, no addresses left out.",
)}
  <section id="pricing">
    <div class="wrap">
      <div class="pricing-grid">
        <div>
          <div class="stamp">
            <div class="cur">$</div>
            <div class="amt">250</div>
            <div class="per">Flat &middot; Every Home</div>
          </div>
        </div>
        <div>
          <p class="eyebrow">Pricing</p>
          <h2 style="font-size:clamp(1.9rem,3.4vw,2.6rem); margin:0 0 22px;">One flat price. Nothing to design, print, or mail yourself.</h2>
          <ul class="includes">
            <li>{CHECK_SVG}<span><strong>Every home on your route</strong> — about 2,500 addresses, renters and owners alike</span></li>
            <li>{CHECK_SVG}<span><strong>Professional design &amp; layout</strong> — included, no separate design fee</span></li>
            <li>{CHECK_SVG}<span><strong>Full-color printing</strong> — no separate print bill, no minimum order</span></li>
            <li>{CHECK_SVG}<span><strong>Postage</strong> to every address on your route — included</span></li>
            <li>{CHECK_SVG}<span><strong>One category exclusivity</strong> — no competitor shares your route</span></li>
            <li>{CHECK_SVG}<span><strong>Real carrier-route targeting</strong> — no guessing at zip-code radius</span></li>
          </ul>
          <span class="scarcity"><span class="dot"></span>One spot per category, per route — first come, first served</span>
        </div>
      </div>
    </div>
  </section>

  <section id="faq">
    <div class="wrap">
      <div class="section-head">
        <p class="eyebrow">FAQ</p>
        <h2>Before you claim a spot.</h2>
        <p>Want the full mechanics — how the mailing program works, what it costs to go it alone? <a class="callout-link" href="/how-it-works.html">Read the full breakdown &rarr;</a></p>
      </div>
      <div class="faq-list">
        <details open>
          <summary><span>Will a competitor be on my mailer?</span><span class="plus">+</span></summary>
          <p class="faq-a">No. Each mailer holds 16 spots and we cap it at one business per category, so a plumber never shares a route with another plumber, a salon with another salon, and so on.</p>
        </details>
        <details>
          <summary><span>How is my route chosen?</span><span class="plus">+</span></summary>
          <p class="faq-a">We pull the actual carrier routes nearest your business address and show you the real home count before you commit — typically around 2,500 homes, though it varies route to route.</p>
        </details>
        <details>
          <summary><span>Do I need to provide my own artwork?</span><span class="plus">+</span></summary>
          <p class="faq-a">No — send us your logo, a phone number, and what you want to offer, and we design and lay out the whole thing for you.</p>
        </details>
      </div>
    </div>
  </section>

{CLAIM_SECTION}
</main>
""" + footer()
    write("index.html", head(title, desc, "/", schema=HOMEPAGE_SCHEMA) + body)


def build_how_it_works():
    title = "How ZipCarrd Works | Every Home, $250 Flat"
    desc = "How ZipCarrd uses USPS Every Door Direct Mail (EDDM) to put your postcard in every home on a real carrier route for $250 flat — and the real math behind that price."
    body = topbar() + f"""
<main id="top">
  <section class="hero" style="padding-bottom:56px;">
{hero_photo_bg(IMG_ROUTE_MAP, "A carrier-route map pinned to a corkboard with string and pushpins")}    <div class="wrap">
      <div class="breadcrumb"><a href="/">Home</a> / How It Works</div>
      <p class="eyebrow">The Mailing Program</p>
      <h1 class="display" style="font-size:clamp(2.2rem,5vw,3.4rem);">How you reach<br>every home for <em>$250</em>.</h1>
      <p class="hero-sub">ZipCarrd runs on USPS Every Door Direct Mail (EDDM) — the same postal program retailers and franchises use to blanket a neighborhood without buying a mailing list. Here's exactly how it works, and why we can offer it to you for $250 flat.</p>
    </div>
  </section>

  <section id="eddm">
    <div class="wrap">
      <div class="section-head">
        <p class="eyebrow">What Is EDDM?</p>
        <h2>Every Door Direct Mail, in plain terms.</h2>
        <p>EDDM is a USPS program that delivers mail to every address on a chosen carrier route without needing individual names or a purchased mailing list — the Postal Service used it to deliver nearly 3 billion pieces last fiscal year. ZipCarrd uses it to get your postcard into every home on your route, renters and owners alike.</p>
      </div>
    </div>
  </section>

{feature_photo(
    IMG_ROUTE_MAP,
    "A carrier-route map pinned to a corkboard with string and pushpins",
    "The route, mapped",
    "Step One",
    "We pull the actual carrier route.",
    "No zip-code guessing — we map the exact USPS carrier route around your business and show you the real home count before you commit to a spot.",
)}
  <section id="math">
    <div class="wrap">
      <div class="section-head">
        <p class="eyebrow">The Math</p>
        <h2>Splitting the route is what makes $250 possible.</h2>
        <p>EDDM postage alone runs about $0.247 per piece at current USPS retail rates — before design or printing. Mailing a 2,500-home route solo adds up fast.</p>
      </div>
      <div class="math-grid">
        <div class="math-card">
          <p class="tag">Mailing It Alone</p>
          <div class="total">~$1,100+</div>
          <ul>
            <li><span>Postage (2,500 &times; $0.247)</span><span>~$618</span></li>
            <li><span>Design</span><span>~$150&ndash;300</span></li>
            <li><span>Printing</span><span>~$200&ndash;300</span></li>
            <li><span>Businesses on route</span><span>1</span></li>
          </ul>
        </div>
        <div class="vs">VS</div>
        <div class="math-card">
          <p class="tag">Growing It With ZipCarrd</p>
          <div class="total win">$250</div>
          <ul>
            <li><span>Postage</span><span>Included</span></li>
            <li><span>Design</span><span>Included</span></li>
            <li><span>Printing</span><span>Included</span></li>
            <li><span>Businesses on route</span><span>16, one per category</span></li>
          </ul>
        </div>
      </div>
      <p class="footnote">Local and home-service EDDM mailers typically see response rates in the 2&ndash;5% range depending on category (industry benchmark, CRST/DMA data) &mdash; on a 2,500-home route, that's roughly 50&ndash;125 households likely to respond. Actual results vary by category, offer, and route. USPS EDDM Retail postage per piece as published at usps.com; rates subject to change.</p>
    </div>
  </section>

{feature_photo(
    IMG_POSTCARD_PROOF,
    "Hands holding a printed postcard proof up to sunlight",
    "The proof, in hand",
    "What Your $250 Buys",
    "A real, professionally printed postcard.",
    "Design and printing are included in the flat $250 — you're not paying a design fee or a separate print bill on top, and you see the layout before it mails.",
    reverse=True,
)}
  <section id="faq">
    <div class="wrap">
      <div class="section-head">
        <p class="eyebrow">FAQ</p>
        <h2>Every question we get before someone claims a spot.</h2>
      </div>
      <div class="faq-list">
        <details open>
          <summary><span>What is Every Door Direct Mail (EDDM)?</span><span class="plus">+</span></summary>
          <p class="faq-a">EDDM is a USPS program that delivers mail to every address on a chosen carrier route without needing individual names or a purchased mailing list. ZipCarrd uses it to get your postcard into every home on your route.</p>
        </details>
        <details>
          <summary><span>How is my route chosen?</span><span class="plus">+</span></summary>
          <p class="faq-a">We pull the actual USPS carrier routes nearest your business address and show you the real home count before you commit — typically around 2,500 homes, though it varies route to route.</p>
        </details>
        <details>
          <summary><span>Will a competitor be on my mailer?</span><span class="plus">+</span></summary>
          <p class="faq-a">No. Each mailer holds 16 spots and we cap it at one business per category, so a plumber never shares a route with another plumber, a salon with another salon, and so on.</p>
        </details>
        <details>
          <summary><span>How long until my mailer goes out?</span><span class="plus">+</span></summary>
          <p class="faq-a">Once your route fills its remaining spots, we move straight to design and print, then queue postage with USPS. Timing depends on how quickly the other 15 spots on your specific route fill.</p>
        </details>
        <details>
          <summary><span>Do I need to provide my own artwork?</span><span class="plus">+</span></summary>
          <p class="faq-a">No — send us your logo, a phone number, and what you want to offer, and we design and lay out the whole thing for you.</p>
        </details>
        <details>
          <summary><span>Can I claim more than one route?</span><span class="plus">+</span></summary>
          <p class="faq-a">Yes. Businesses that serve a wider area often claim a spot on several adjacent routes at $250 each.</p>
        </details>
      </div>
    </div>
  </section>

{CLAIM_SECTION}
</main>
""" + footer()
    write("how-it-works.html", head(title, desc, "/how-it-works.html") + body)


def build_new_england_hub():
    title = "Find Your Town | ZipCarrd New England Routes"
    desc = "Browse ZipCarrd carrier routes across Connecticut, Maine, Massachusetts, New Hampshire, Rhode Island, and Vermont — every home reached for $250 flat."
    cards = ""
    for state in TOWNS:
        slug = STATE_SLUGS[state]
        count = len(TOWNS[state])
        cards += f"""<a class="state-card" href="/routes/{slug}/">
          <h3>{state}</h3>
          <p>{count} towns &amp; cities</p>
        </a>
"""
    body = topbar() + f"""
<main id="top">
  <section class="hero" style="padding-bottom:56px;">
{hero_photo_bg(IMG_TOWN_GREEN, "A New England town green with a white church steeple in autumn")}    <div class="wrap">
      <div class="breadcrumb"><a href="/">Home</a> / Find Your Town</div>
      <p class="eyebrow">New England Routes</p>
      <h1 class="display" style="font-size:clamp(2.2rem,5vw,3.4rem);">Find your <em>route</em>.</h1>
      <p class="hero-sub">ZipCarrd is rolling out carrier-route by carrier-route across New England. Pick your state to find your town.</p>
    </div>
  </section>
{feature_photo(
    IMG_TOWN_GREEN,
    "A New England town green with a white church steeple in autumn",
    "New England, in fall",
    "Six States, One Program",
    "Same route logic, town after town.",
    "Every town below runs on the same real USPS carrier-route data — pick a state to see which towns already have active routes.",
)}
  <section>
    <div class="wrap">
      <div class="state-grid">
{cards}      </div>
    </div>
  </section>
{CLAIM_SECTION}
</main>
""" + footer()
    write("new-england.html", head(title, desc, "/new-england.html") + body)


def build_state_index(state: str):
    slug = STATE_SLUGS[state]
    towns = TOWNS[state]
    title = f"ZipCarrd Routes in {state} | Find Your Town"
    desc = f"Every {state} town where a local business can reach every home on a carrier route for $250 flat on ZipCarrd — {len(towns)} towns and counting."
    items = "".join(
        f'<li><a href="/routes/{slug}/{slugify(t)}.html">{t}</a></li>\n' for t in towns
    )
    body = topbar() + f"""
<main id="top">
  <section class="hero" style="padding-bottom:56px;">
    <div class="wrap">
      <div class="breadcrumb"><a href="/">Home</a> / <a href="/new-england.html">Find Your Town</a> / {state}</div>
      <p class="eyebrow">{state}</p>
      <h1 class="display" style="font-size:clamp(2.2rem,5vw,3.4rem);">ZipCarrd in <em>{state}</em></h1>
      <p class="hero-sub">{len(towns)} towns and cities across {state} where a local business can reach every home on a carrier route for $250 flat. Don't see your town listed yet as an active route? Claim it anyway — we'll map the nearest carrier route when you do.</p>
    </div>
  </section>
  <section>
    <div class="wrap">
      <ul class="town-list">
{items}      </ul>
    </div>
  </section>
{CLAIM_SECTION}
</main>
""" + footer()
    write(f"routes/{slug}/index.html", head(title, desc, f"/routes/{slug}/") + body)


# Deterministic "nearby towns" pick for internal linking -- the next N towns
# after this one in its state's list (wrapping around). towns.json is stored
# alphabetically per state, so this isn't geographic, but it's a stable,
# free way to give every town page outbound links to other town pages
# instead of leaving them as crawl dead-ends.
def nearby_towns(state: str, town: str, n: int = 6):
    towns = TOWNS[state]
    if town not in towns or len(towns) <= 1:
        return []
    idx = towns.index(town)
    count = min(n, len(towns) - 1)
    return [towns[(idx + i) % len(towns)] for i in range(1, count + 1)]


def nearby_towns_section(state: str, town: str) -> str:
    slug = STATE_SLUGS[state]
    towns = nearby_towns(state, town)
    if not towns:
        return ""
    links = "".join(
        f'<li><a href="/routes/{slug}/{slugify(t)}.html">{t}</a></li>\n' for t in towns
    )
    return f"""
  <section>
    <div class="wrap">
      <div class="section-head">
        <p class="eyebrow">Nearby Routes</p>
        <h2>Also serving towns near {town}.</h2>
      </div>
      <ul class="town-list">
{links}      </ul>
    </div>
  </section>
"""


# Three Q&As restating facts already established elsewhere on the site
# (route size, no mailing list, one-category exclusivity) -- reworded per
# town for a bit of unique on-page text and a shot at an FAQ rich result,
# without inventing any town-specific fact we can't actually back up.
def town_faq(town: str, state: str):
    return [
        (
            f"How many homes does the {town} route reach?",
            f"A standard residential carrier route in {town} reaches roughly 2,500 homes — renters and owners alike, all on one real USPS delivery route.",
        ),
        (
            f"Do I need my own mailing list to reach {town} homes?",
            "No. The route itself is the list — every address gets a postcard, with nothing for you to buy, build, or maintain.",
        ),
        (
            f"Can a competitor claim the same {town} route as me?",
            f"No. Each route sells one spot per category, so once you claim your category in {town}, no direct competitor can share your route.",
        ),
    ]


def town_faq_section(town: str, state: str) -> str:
    qas = town_faq(town, state)
    items = "".join(
        f"""        <details{' open' if i == 0 else ''}>
          <summary><span>{q}</span><span class="plus">+</span></summary>
          <p class="faq-a">{a}</p>
        </details>
"""
        for i, (q, a) in enumerate(qas)
    )
    return f"""
  <section id="faq">
    <div class="wrap">
      <div class="section-head">
        <p class="eyebrow">FAQ</p>
        <h2>The {town} route, answered.</h2>
      </div>
      <div class="faq-list">
{items}      </div>
    </div>
  </section>
"""


def town_schema(state: str, town: str, slug: str, tslug: str) -> str:
    qas = town_faq(town, state)
    obj = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "Service",
                "name": f"ZipCarrd EDDM Mailer — {town}, {state}",
                "serviceType": "Direct mail advertising",
                "areaServed": {"@type": "City", "name": town, "containedInPlace": state},
                "provider": {"@type": "Organization", "name": "ZipCarrd", "url": DOMAIN},
                "offers": {"@type": "Offer", "price": "250", "priceCurrency": "USD"},
            },
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "Home", "item": f"{DOMAIN}/"},
                    {"@type": "ListItem", "position": 2, "name": "Find Your Town", "item": f"{DOMAIN}/new-england.html"},
                    {"@type": "ListItem", "position": 3, "name": state, "item": f"{DOMAIN}/routes/{slug}/"},
                    {"@type": "ListItem", "position": 4, "name": town, "item": f"{DOMAIN}/routes/{slug}/{tslug}.html"},
                ],
            },
            {
                "@type": "FAQPage",
                "mainEntity": [
                    {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}
                    for q, a in qas
                ],
            },
        ],
    }
    return json.dumps(obj)


def build_town_page(state: str, town: str):
    slug = STATE_SLUGS[state]
    tslug = slugify(town)
    title = f"Reach Every Home in {town}, {state} for $250 | ZipCarrd"
    desc = f"Get your postcard into every mailbox on a real carrier route in {town}, {state} for $250 flat. No mailing list, no design fee, one business per category."
    qs = f"?town={town.replace(' ', '+')}&state={state.replace(' ', '+')}"
    town_copy = TOWN_CONTENT.get(f"{state}/{town}", "").strip()
    about_section = ""
    if town_copy:
        about_section = f"""
  <section>
    <div class="wrap">
      <div class="section-head">
        <p class="eyebrow">Why {town}</p>
        <h2>Built for towns like {town}.</h2>
        <p>{town_copy}</p>
      </div>
    </div>
  </section>
"""
    body = topbar() + f"""
<main id="top">
  <section class="hero" style="padding-bottom:0;">
    <div class="wrap">
      <div class="breadcrumb"><a href="/">Home</a> / <a href="/new-england.html">Find Your Town</a> / <a href="/routes/{slug}/">{state}</a> / {town}</div>
      <div class="hero-grid">
        <div>
          <p class="eyebrow">{town}, {state}</p>
          <h1 class="display" style="font-size:clamp(2.2rem,5vw,3.6rem);">Reach every home<br>in <em>{town}</em>.</h1>
          <p class="hero-sub">For $250 flat, your postcard reaches every home on a real carrier route in {town} — about 2,500 addresses — with no mailing list to buy and no design fee. You're the only business in your category on the route.</p>
          <div class="hero-actions">
            <a class="btn btn-primary" href="/{qs}#claim">Check My {town} Route</a>
            <a class="btn btn-ghost" href="/how-it-works.html">See How It Works</a>
          </div>
          <p class="hero-note">No mailing list required &middot; One spot per category in {town}</p>
        </div>
        <div class="charter">
          <p class="charter-title">Route Charter &middot; {town}</p>
          <div class="charter-box">
            <div class="l1">{state.upper()}</div>
            <div class="l2">EVERY HOME, EVERY TIME</div>
            <div class="l3">$250 FLAT &middot; ZIPCARRD</div>
          </div>
          <div class="charter-meta">
            <span>ROUTE TYPE<br><strong>RESIDENTIAL</strong></span>
            <span style="text-align:right;">REACH<br><strong>~2,500 HOMES</strong></span>
          </div>
        </div>
      </div>
      <div class="town-mini-stats">
        <div><div class="num mono">~2,500</div><div class="label">Homes reached</div></div>
        <div><div class="num mono">$0.10</div><div class="label">Roughly, per home reached</div></div>
        <div><div class="num mono">$250</div><div class="label">Flat, all in</div></div>
      </div>
    </div>
  </section>
{about_section}
  <section id="pricing">
    <div class="wrap">
      <div class="section-head">
        <p class="eyebrow">Pricing</p>
        <h2>One flat price to reach every home on your {town} route.</h2>
        <p>Nothing to design, print, or mail yourself. <a class="callout-link" href="/how-it-works.html">See the full mailing breakdown &rarr;</a></p>
      </div>
      <ul class="includes">
        <li>{CHECK_SVG}<span><strong>Every home on your {town} route</strong> — about 2,500 addresses, renters and owners alike</span></li>
        <li>{CHECK_SVG}<span><strong>Professional design &amp; layout</strong> — included, no separate design fee</span></li>
        <li>{CHECK_SVG}<span><strong>Full-color printing</strong> — no separate print bill, no minimum order</span></li>
        <li>{CHECK_SVG}<span><strong>Postage</strong> to every address on your {town} carrier route — included</span></li>
        <li>{CHECK_SVG}<span><strong>One category exclusivity</strong> — no competitor shares your route</span></li>
      </ul>
      <span class="scarcity"><span class="dot"></span>One spot per category in {town} — first come, first served</span>
    </div>
  </section>
{town_faq_section(town, state)}
{nearby_towns_section(state, town)}
{CLAIM_SECTION}
</main>
""" + footer()
    schema = town_schema(state, town, slug, tslug)
    write(
        f"routes/{slug}/{tslug}.html",
        head(title, desc, f"/routes/{slug}/{tslug}.html", schema=schema, og_image=IMG_TOWN_GREEN) + body,
    )


def build_sitemap(all_urls):
    urls = "\n".join(
        f"  <url><loc>{DOMAIN}{u}</loc><lastmod>{BUILD_DATE}</lastmod></url>" for u in all_urls
    )
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{urls}
</urlset>
"""
    write("sitemap.xml", xml)
    write("robots.txt", f"User-agent: *\nAllow: /\nSitemap: {DOMAIN}/sitemap.xml\n")


def main():
    if os.path.exists(DIST):
        shutil.rmtree(DIST)
    all_urls = ["/", "/how-it-works.html", "/new-england.html"]

    build_homepage()
    build_how_it_works()
    build_new_england_hub()

    total_towns = 0
    for state, towns in TOWNS.items():
        slug = STATE_SLUGS[state]
        build_state_index(state)
        all_urls.append(f"/routes/{slug}/")
        seen = set()
        for town in towns:
            tslug = slugify(town)
            if tslug in seen:
                continue
            seen.add(tslug)
            build_town_page(state, town)
            all_urls.append(f"/routes/{slug}/{tslug}.html")
            total_towns += 1

    build_sitemap(all_urls)
    shutil.copytree(os.path.join(SITE_ROOT, "assets"), os.path.join(DIST, "assets"))
    print(f"Built {len(all_urls)} pages ({total_towns} town pages) into {DIST}")


if __name__ == "__main__":
    main()
