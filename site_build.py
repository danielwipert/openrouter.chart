"""Build the public website from output/: python site_build.py

Writes _site/ (not saved in git; GitHub Pages publishes it):
  index.html               the newest READY TO POST week
  weeks/<week>/index.html  every READY week, with its charts and CSVs
  assets/                  stylesheet, script, fonts, icon

Only weeks whose run report says READY TO POST are published, so a NOT READY
week never replaces a good one. Wording and sections live in site/site.yaml.
"""

import html
import shutil
from datetime import date, datetime, timedelta
from pathlib import Path
from string import Template

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parent
SITE_DIR = ROOT / "site"
OUTPUT_DIR = ROOT / "output"
BUILD_DIR = ROOT / "_site"
STEALTH = "Stealth (undisclosed)"
NOT_LABELED = {"other", "unknown", STEALTH}

LOGO = ('<svg class="logo" viewBox="0 0 32 32" aria-hidden="true">'
        '<circle cx="16" cy="16" r="15" fill="#0088B0" stroke="#fff" stroke-width="1.5"/>'
        '<circle cx="16" cy="16" r="10.8" fill="#D5006C" stroke="#fff" stroke-width="1.5"/>'
        '<circle cx="16" cy="16" r="6.6" fill="#F2C400" stroke="#fff" stroke-width="1.5"/>'
        '<circle cx="16" cy="16" r="2.7" fill="#121212"/></svg>')


# --- Reading one week's outputs ------------------------------------------------

def is_ready(week_dir):
    report = week_dir / "run_report.md"
    if not report.exists():
        return False
    first = report.read_text(encoding="utf-8").splitlines()[0]
    return "READY TO POST" in first and "NOT READY" not in first


def ready_weeks(output_dir=OUTPUT_DIR):
    """READY TO POST week folders, newest first."""
    weeks = [p for p in output_dir.iterdir() if p.is_dir() and is_ready(p)]
    return sorted(weeks, key=lambda p: p.name, reverse=True)


def captions(week_dir):
    """Each chart's draft caption as (title, story paragraphs): the first line is
    the chart's finding; the paragraphs after it are the week's story."""
    out, name, lines = {}, None, []

    def finish():
        if name and lines:
            story = [l for l in lines[1:] if not l.startswith(("Data:", "Source:", "["))]
            out[name] = (lines[0].rstrip("."), story)

    for line in (week_dir / "caption.md").read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            finish()
            name, lines = line[3:].strip(), []
        elif name and line.strip():
            lines.append(line.strip())
    finish()
    return out


def read_weekly(week_dir):
    return pd.read_csv(week_dir / "weekly.csv", comment="#")


def week_range(weekly):
    start = date.fromisoformat(weekly["period"].max())
    end = start + timedelta(days=6)
    if start.month == end.month:
        return f"{start:%b} {start.day} to {end.day}, {end.year}"
    return f"{start:%b} {start.day} to {end:%b} {end.day}, {end.year}"


def as_of_text(week_dir):
    meta = yaml.safe_load((week_dir / "meta.json").read_text(encoding="utf-8"))
    stamp = meta["api_meta"][-1]["as_of"].replace("Z", "+00:00")
    return datetime.fromisoformat(stamp).strftime("%b %-d, %Y")


# --- Headline numbers ----------------------------------------------------------------

def stat(weekly, dimension, value):
    """(display name, latest share, change in points vs the week before) for one stat."""
    rows = weekly[(weekly["dimension"] == dimension) & weekly["share"].notna()]
    periods = sorted(rows["period"].unique())
    latest = rows[rows["period"] == periods[-1]]
    if value == "top_named":
        named = latest[~latest["value"].isin(NOT_LABELED)]
        value = named.sort_values(["share", "value"], ascending=[False, True]).iloc[0]["value"]
    now = latest.loc[latest["value"] == value, "share"].sum()
    before = None
    if len(periods) > 1:
        prev = rows[(rows["period"] == periods[-2]) & (rows["value"] == value)]
        before = prev["share"].sum() if len(prev) else None
    change = None if before is None else (now - before) * 100
    return value, now, change


def delta_html(change):
    if change is None:
        return '<span class="delta flat">new this week</span>'
    if round(change, 1) == 0:
        return '<span class="delta flat">no change vs last week</span>'
    kind, sign = ("up", "+") if change > 0 else ("down", "−")
    return f'<span class="delta {kind}">{sign}{abs(change):.1f} pts vs last week</span>'


def stat_cards(weekly, config):
    cards = []
    for item in config["stats"]:
        name, share, change = stat(weekly, item["dimension"], item["value"])
        named = (f'<span class="stat-name">{html.escape(name)}</span>'
                 if item["value"] == "top_named" else "")
        cards.append(
            f'<div class="stat"><span class="stat-label">{html.escape(item["label"])}</span>'
            f'{named}<span class="stat-value">{share * 100:.0f}%</span>'
            f'{delta_html(change)}<div class="stat-note">{html.escape(item["note"])}</div></div>')
    return "\n      ".join(cards)


# --- Chart cards ----------------------------------------------------------------------

def chart_card(name, title, label, charts_url, story=None):
    """One chart: the image (click for full size), a short label and download buttons.
    The featured card also carries the week's story."""
    square, portrait = f"{charts_url}{name}_square.png", f"{charts_url}{name}_portrait.png"
    t = html.escape(title)
    if story is None:
        body = f'<p class="card-label">{html.escape(label)}</p>'
    else:
        paragraphs = "".join(f"<p>{html.escape(p)}</p>" for p in story)
        body = (f'<p class="card-label">{html.escape(label)}</p>'
                f'<h2 class="card-title">The week in brief</h2>'
                f'<div class="story">{paragraphs}</div>')
    return (f'<article class="card" id="{name}">'
            f'<button class="card-media" data-full="{square}" data-title="{t}" '
            f'aria-label="View full size: {t}">'
            f'<img src="{square}" alt="{t}" loading="lazy" width="1080" height="1080"></button>'
            f'<div class="card-body">{body}<div class="card-actions">'
            f'<a class="chip" href="{square}" download>Square PNG</a>'
            f'<a class="chip" href="{portrait}" download>Portrait PNG</a>'
            f'<button class="chip" type="button" data-copy="#{name}">Copy link</button>'
            f'</div></div></article>')


def sections_html(config, texts, charts_url, available):
    out = []
    for section in config["sections"]:
        names = [n for n in section["charts"] if n in available and n != config["featured_chart"]]
        if not names:
            continue
        cards = "\n".join(chart_card(n, texts.get(n, (n, []))[0], config["labels"].get(n, ""),
                                      charts_url) for n in names)
        out.append(f'<section class="section wrap" id="{section["id"]}">'
                   f'<div class="section-head"><h2>{html.escape(section["title"])}</h2>'
                   f'<p>{html.escape(section["intro"])}</p></div>'
                   f'<div class="grid">{cards}</div></section>')
    return "\n\n  ".join(out)


# --- Pages ------------------------------------------------------------------------------

def render_page(week_dir, weeks, config, depth):
    """HTML for one week. depth 0 = site root, 2 = weeks/<week>/."""
    up = "../" * depth
    label = week_dir.name
    week_base = "" if depth else f"weeks/{label}/"
    charts_url = f"{week_base}charts/"
    weekly = read_weekly(week_dir)
    texts = captions(week_dir)
    available = {p.name.rsplit("_", 1)[0] for p in (week_dir / "charts").glob("*_square.png")}
    featured = config["featured_chart"]
    headline, story = texts.get(featured, (config["name"], []))
    year, number = label.split("-W")
    newest = weeks[0].name

    def week_url(name):
        if name == newest:
            return up or "./"
        return f"{up}weeks/{name}/"

    options = "\n        ".join(
        f'<option value="{week_url(w.name)}"{" selected" if w.name == label else ""}>'
        f'Week {int(w.name.split("-W")[1])}, {w.name.split("-W")[0]}'
        f'{" (latest)" if w.name == newest else ""}</option>' for w in weeks)
    archive = "\n          ".join(
        f'<li{" class=current" if w.name == label else ""}><a href="{week_url(w.name)}">'
        f'{html.escape(week_range(read_weekly(w)))}</a></li>' for w in weeks)
    nav = "\n      ".join(f'<a href="#{s["id"]}">{html.escape(s["title"])}</a>'
                          for s in config["sections"]) + '\n      <a href="#method">Method</a>'
    featured_card = (chart_card(featured, headline, config["labels"].get(featured, ""), charts_url,
                                story) if featured in available else "")

    values = {
        "page_title": html.escape(f'{config["name"]}: {headline}'),
        "description": html.escape(config["tagline"]),
        "headline": html.escape(headline),
        "page_url": config["site_url"] + ("" if label == newest else f"weeks/{label}/"),
        "og_image": f'{config["site_url"]}weeks/{label}/charts/{featured}_square.png',
        "assets": f"{up}assets/",
        "home": up or "./",
        "week_base": week_base,
        "logo": LOGO,
        "site_name": html.escape(config["name"]),
        "nav_links": nav,
        "week_options": options,
        "kicker": html.escape(f"Week {int(number)}, {week_range(weekly)}"),
        "tagline": html.escape(config["tagline"]),
        "stat_cards": stat_cards(weekly, config),
        "featured": featured_card,
        "sections": sections_html(config, texts, charts_url, available),
        "method_items": "\n          ".join(f"<li>{html.escape(m)}</li>" for m in config["method"]),
        "week_range": html.escape(week_range(weekly)),
        "archive_links": archive,
        "author": html.escape(config["author"]),
        "company": html.escape(config["company"]),
        "repo_url": config["repo_url"],
        "as_of": as_of_text(week_dir),
        "updated": as_of_text(week_dir),
    }
    template = Template((SITE_DIR / "template.html").read_text(encoding="utf-8"))
    return template.substitute(values)


def build(output_dir=OUTPUT_DIR, build_dir=BUILD_DIR):
    config = yaml.safe_load((SITE_DIR / "site.yaml").read_text(encoding="utf-8"))
    weeks = ready_weeks(output_dir)
    if not weeks:
        raise SystemExit("No READY TO POST week in output/ yet: nothing to publish.")
    if build_dir.exists():
        shutil.rmtree(build_dir)
    assets = build_dir / "assets"
    (assets / "fonts").mkdir(parents=True)
    for name in ("site.css", "site.js"):
        shutil.copy(SITE_DIR / name, assets / name)
    for font in (ROOT / "fonts").glob("FiraSans-*"):
        shutil.copy(font, assets / "fonts" / font.name)
    (assets / "favicon.svg").write_text(LOGO.replace('class="logo" ', 'xmlns="http://www.w3.org/2000/svg" '),
                                        encoding="utf-8")

    for week in weeks:
        target = build_dir / "weeks" / week.name
        shutil.copytree(week / "charts", target / "charts")
        for name in ("weekly.csv", "monthly.csv"):
            shutil.copy(week / name, target / name)
        (target / "index.html").write_text(render_page(week, weeks, config, depth=2),
                                           encoding="utf-8")
    (build_dir / "index.html").write_text(render_page(weeks[0], weeks, config, depth=0),
                                          encoding="utf-8")
    (build_dir / ".nojekyll").write_text("", encoding="utf-8")  # serve files as they are
    return build_dir, [w.name for w in weeks]


def main():
    build_dir, weeks = build()
    print(f"Built {build_dir} with {len(weeks)} week(s): {', '.join(weeks)}")


if __name__ == "__main__":
    main()
