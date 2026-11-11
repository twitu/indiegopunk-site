#!/usr/bin/env python3
"""Pull upcoming and running jams from itch.io into calendars/jams.json. No agent, no API key.

  bin/jams_sync.py            Dry run: print what would change.
  bin/jams_sync.py --write    Apply: update dates of known itch jams, add new popular ones.

Rules
- Reads https://itch.io/jams/upcoming and /jams/in-progress (public pages, allowed by robots.txt).
- A jam already in the file (same itch URL) gets its start and end date refreshed.
- A new jam is added only if it has at least MIN_JOINED joined. A new end date can be a day short: review it.
- New jams carry source "itch-sync" so a human can review them. Format defaults to online.
- Jams are marked featured (star) at STAR_JOINED joined or more.
"""
import argparse, html, json, re, sys, time, urllib.error, urllib.request, datetime as dt
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "calendars" / "jams.json"
MIN_JOINED, STAR_JOINED, MAX_MONTHS, MAX_PAGES = 300, 2000, 9, 8
UA = "Mozilla/5.0 (compatible; indiegopunk-calendar; +https://indiegopunk.com/calendars/)"
UNITS = {"hour": 1 / 24, "day": 1, "week": 7, "month": 30, "year": 365}


def get(url):
    for wait in (0, 30, 90, 180):  # back off when itch.io answers 429
        time.sleep(wait)
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=30).read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code != 429:
                raise
    sys.exit("itch.io keeps answering 429: try again later")


def parse_page(page):
    out = []
    for chunk in page.split('<div class="jam lazy_images">')[1:]:
        m = re.search(r'<h3[^>]*><a href="(/jam/[^"]+)">(.*?)</a>', chunk)
        t = re.search(r'class="date_countdown">([0-9T:\-]+)Z?<', chunk) or re.search(r'title="([0-9\- :]+)" class="date_countdown"', chunk)
        d = re.search(r'class="date_duration">\s*([0-9.]+)\s*(\w+?)s?\s*<', chunk)
        if not (m and t and d):
            continue
        host = re.search(r'Hosted by <a [^>]*>(.*?)</a>', chunk)
        joined = re.search(r'<span class="number">([\d,]+)</span> joined', chunk)
        start = dt.datetime.fromisoformat(t.group(1).replace(" ", "T")[:19])
        days = float(d.group(1)) * UNITS.get(d.group(2).rstrip("s"), 1)
        end = start + dt.timedelta(days=days)
        out.append({"url": "https://itch.io" + m.group(1), "name": html.unescape(m.group(2)),
                    "host": html.unescape(host.group(1)) if host else "itch.io",
                    "start": start.date().isoformat(), "end": end.date().isoformat(),
                    "joined": int(joined.group(1).replace(",", "")) if joined else 0,
                    "featured_flag": "featured_flag" in chunk, "hours": round(days * 24)})
    return out


def fetch_all():
    seen = {}
    for path in ("/jams/in-progress", "/jams/upcoming"):
        for n in range(1, MAX_PAGES + 1):
            rows = parse_page(get(f"https://itch.io{path}?page={n}"))
            if not rows:
                break
            for r in rows:
                seen[r["url"]] = r
            time.sleep(3.0)
    return list(seen.values())


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--write", action="store_true"); a = ap.parse_args()
    doc = json.loads(DATA.read_text()); jams = doc["jams"]; by_url = {j["url"].rstrip("/"): j for j in jams}
    today = dt.date.today(); horizon = (today + dt.timedelta(days=30 * MAX_MONTHS)).isoformat()
    rows = fetch_all()
    if len(rows) < 10:
        sys.exit(f"only {len(rows)} jams parsed: itch.io page layout probably changed, refusing to touch the data")
    changed, added = [], []
    for r in rows:
        j = by_url.get(r["url"])
        if j:
            # The listing duration can be one day short of the jam page, so ignore a one day end difference.
            off = abs((dt.date.fromisoformat(j["end"]) - dt.date.fromisoformat(r["end"])).days)
            if j["start"] != r["start"] or off > 1:
                changed.append(f"{j['name']}: {j['start']}..{j['end']} -> {r['start']}..{r['end']}")
                j["start"], j["end"] = r["start"], r["end"]
            j["verified"] = today.isoformat()
        elif r["start"] <= horizon and r["joined"] >= MIN_JOINED:
            slug = r["url"].rsplit("/", 1)[1]
            new = {"id": slug, "name": r["name"], "url": r["url"], "start": r["start"], "end": r["end"], "host": r["host"],
                   "platform": "itch.io", "format": "online", "team": "both", "duration_hours": r["hours"],
                   "prize": False, "verified": today.isoformat(), "source": "itch-sync"}
            if r["joined"] >= STAR_JOINED:
                new["featured"] = True
            jams.append(new); added.append(f"{r['name']} ({r['joined']} joined) {r['start']}..{r['end']}")
    print(f"parsed {len(rows)} itch jams; {len(changed)} date changes, {len(added)} new")
    for l in changed: print("  ~", l)
    for l in added: print("  +", l)
    if a.write and (changed or added):
        jams.sort(key=lambda j: (j["start"], j["end"], j["id"]))
        DATA.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
