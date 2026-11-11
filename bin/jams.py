#!/usr/bin/env python3
"""Maintain calendars/jams.json, the one source of truth for the game jam calendar.

  bin/jams.py check             Validate the data file. Exit 1 on any error.
  bin/jams.py build             Validate, sort by date, rewrite jams.json and jams.ics.
  bin/jams.py add --name ...    Append one jam, then build.
  bin/jams.py stale [DAYS]      List jams not verified for DAYS days (default 30).
"""
import argparse, json, re, sys, datetime as dt
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "calendars"
DATA, FEED = ROOT / "jams.json", ROOT / "jams.ics"
FORMATS = {"online", "in-person", "hybrid"}
TEAMS = {"solo", "team", "both"}
REQUIRED = ["id", "name", "url", "start", "end", "host", "format", "team", "verified"]
KEYS = REQUIRED + ["platform", "location", "theme", "duration_hours", "prize", "note", "featured"]


def load():
    return json.loads(DATA.read_text())


def date(s):
    return dt.date.fromisoformat(s)


def validate(doc):
    errs, seen = [], set()
    for i, j in enumerate(doc.get("jams", [])):
        tag = f"jam[{i}] {j.get('id', '?')}"
        for k in REQUIRED:
            if j.get(k) in (None, ""):
                errs.append(f"{tag}: missing {k}")
        for k in j:
            if k not in KEYS:
                errs.append(f"{tag}: unknown key {k}")
        if j.get("id") in seen:
            errs.append(f"{tag}: duplicate id")
        seen.add(j.get("id"))
        if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", str(j.get("id", ""))):
            errs.append(f"{tag}: id must be a kebab slug")
        if not re.match(r"https://", str(j.get("url", ""))):
            errs.append(f"{tag}: url must start with https://")
        try:
            if date(j["start"]) > date(j["end"]):
                errs.append(f"{tag}: start is after end")
            date(j["verified"])
        except (KeyError, ValueError):
            errs.append(f"{tag}: bad date (use YYYY-MM-DD)")
        if j.get("format") not in FORMATS:
            errs.append(f"{tag}: format must be one of {sorted(FORMATS)}")
        if j.get("team") not in TEAMS:
            errs.append(f"{tag}: team must be one of {sorted(TEAMS)}")
        if len(j.get("note") or "") > 160:
            errs.append(f"{tag}: note is over 160 characters")
    return errs


def esc(t):
    return re.sub(r"([\;,])", r"\\\1", str(t or "")).replace("\n", "\\n")


def feed(jams):
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Indie Go Punk//Game Jams//EN",
           "X-WR-CALNAME:Indie Go Punk game jams", "REFRESH-INTERVAL;VALUE=DURATION:P1D"]
    for j in jams:
        end = (date(j["end"]) + dt.timedelta(days=1)).strftime("%Y%m%d")
        out += ["BEGIN:VEVENT", f"UID:{j['id']}@indiegopunk.com", f"DTSTAMP:{now}",
                f"DTSTART;VALUE=DATE:{j['start'].replace('-', '')}", f"DTEND;VALUE=DATE:{end}",
                f"SUMMARY:{esc(j['name'])}", f"URL:{j['url']}",
                f"DESCRIPTION:{esc((j.get('note') or '') + ' ' + j['url'])}",
                f"LOCATION:{esc(j.get('location') or 'Online')}", "END:VEVENT"]
    out.append("END:VCALENDAR")
    return "\r\n".join(out) + "\r\n"


def write(doc):
    doc["jams"].sort(key=lambda j: (j["start"], j["end"], j["id"]))
    DATA.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    FEED.write_text(feed(doc["jams"]))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check"); sub.add_parser("build")
    st = sub.add_parser("stale"); st.add_argument("days", nargs="?", type=int, default=30)
    a = sub.add_parser("add")
    for k in ["id", "name", "url", "start", "end", "host"]:
        a.add_argument("--" + k, required=k != "id")
    a.add_argument("--format", default="online", choices=sorted(FORMATS))
    a.add_argument("--team", default="both", choices=sorted(TEAMS))
    a.add_argument("--platform"); a.add_argument("--location"); a.add_argument("--theme"); a.add_argument("--note")
    a.add_argument("--hours", type=int); a.add_argument("--prize", action="store_true")
    args = p.parse_args()

    doc = load()
    if args.cmd == "add":
        j = {k: getattr(args, k) for k in ["name", "url", "start", "end", "host", "format", "team", "platform", "location", "theme", "note"] if getattr(args, k)}
        j["id"] = args.id or re.sub(r"[^a-z0-9]+", "-", f"{args.name} {args.start[:4]}".lower()).strip("-")
        j["duration_hours"] = args.hours; j["prize"] = args.prize
        j["verified"] = dt.date.today().isoformat()
        doc["jams"].append(j)
    if args.cmd == "stale":
        cut = dt.date.today() - dt.timedelta(days=args.days)
        for j in doc["jams"]:
            if date(j["end"]) >= dt.date.today() and date(j["verified"]) < cut:
                print(f"{j['verified']}  {j['id']}  {j['url']}")
        return
    errs = validate(doc)
    if errs:
        print("\n".join(errs), file=sys.stderr); sys.exit(1)
    if args.cmd in ("build", "add"):
        write(doc); print(f"ok: {len(doc['jams'])} jams, wrote jams.json and jams.ics")
    else:
        print(f"ok: {len(doc['jams'])} jams")


if __name__ == "__main__":
    main()
