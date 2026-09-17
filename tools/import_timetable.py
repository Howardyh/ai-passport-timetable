#!/usr/bin/env python3
"""Compile explicit ICS occurrences into a compact, offline Shanghai timetable.

Recurrence is deliberately rejected instead of silently dropping occurrences.
Personal outputs go into ignored private/ and main/timetable_data.c files.
"""
import argparse
import datetime as dt
import hashlib
import json
import re
from pathlib import Path

SHANGHAI = dt.timezone(dt.timedelta(hours=8))
EPOCH = dt.date(1970, 1, 1)


def unescape(value):
    return re.sub(r"\\([nN,;\\])", lambda m: "\n" if m[1] in "nN" else m[1], value)


def timestamp(key, value):
    if "VALUE=DATE" in key or len(value) == 8:
        raise ValueError("All-day events are not supported as lessons")
    if "TZID=" in key and not any(t in key for t in ("TZID=Asia/Shanghai", "TZID=Asia/Chongqing")):
        raise ValueError("Unsupported timezone: " + key)
    if value.endswith("Z"):
        return dt.datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=dt.timezone.utc).astimezone(SHANGHAI)
    return dt.datetime.strptime(value, "%Y%m%dT%H%M%S").replace(tzinfo=SHANGHAI)


def parse_ics(text):
    lines = re.sub(r"\r?\n[ \t]", "", text.lstrip("\ufeff")).splitlines()
    if not lines or lines[0] != "BEGIN:VCALENDAR" or "END:VCALENDAR" not in lines:
        raise ValueError("Invalid VCALENDAR")
    events, current, seen = [], None, set()
    for line in lines:
        if line == "BEGIN:VEVENT":
            if current is not None:
                raise ValueError("Nested event")
            current = {}
        elif line == "END:VEVENT":
            if current is None:
                raise ValueError("Unexpected event end")
            if any(k in current for k in ("RRULE", "RDATE", "EXDATE", "RECURRENCE-ID")):
                raise ValueError("Recurring ICS requires expansion to explicit occurrences first")
            if current.get("STATUS", ("", ""))[1] == "CANCELLED":
                current = None
                continue
            start = timestamp(*current["DTSTART"])
            end = timestamp(*current["DTEND"])
            if end <= start or end.date() != start.date():
                raise ValueError("Invalid or overnight lesson")
            event = dict(day=(start.date() - EPOCH).days, start=start.hour * 60 + start.minute,
                         end=end.hour * 60 + end.minute, date=start.date().isoformat(),
                         name=unescape(current["SUMMARY"][1]),
                         location=unescape(current.get("LOCATION", ("", ""))[1]),
                         description=unescape(current.get("DESCRIPTION", ("", ""))[1]))
            if not event["name"] or any(len(event[k].encode()) > 384 for k in ("name", "location", "description")):
                raise ValueError("Missing name or overlong lesson text")
            identity = current.get("UID", ("", json.dumps(event, sort_keys=True)))[1]
            if identity in seen:
                raise ValueError("Duplicate UID; resolve calendar revisions before importing")
            seen.add(identity)
            events.append(event)
            current = None
        elif current is not None and ":" in line:
            key, value = line.split(":", 1)
            current[key.split(";", 1)[0]] = (key, value)
    if current is not None or not events:
        raise ValueError("Incomplete or empty calendar")
    return sorted(events, key=lambda e: (e["day"], e["start"], e["name"]))


def generate(source, root):
    raw = source.read_bytes()
    events = parse_ics(raw.decode("utf-8-sig"))
    private = root / "private"
    private.mkdir(exist_ok=True)
    (private / "timetable.ics").write_bytes(raw)
    (private / "timetable.json").write_text(json.dumps(events, ensure_ascii=False, indent=2), encoding="utf-8")
    q = lambda x: json.dumps(x, ensure_ascii=False)
    code = ['// Generated personal data. Do not publish.', '#include "timetable.h"',
            'const timetable_event_t timetable_events[] = {']
    for e in events:
        code.append('    {%d, %d, %d, %s, %s, %s},' %
                    (e['day'], e['start'], e['end'], q(e['name']), q(e['location']), q(e['description'])))
    code += ['};', 'const size_t timetable_count = sizeof(timetable_events) / sizeof(timetable_events[0]);',
             'const char timetable_source_hash[] = "%s";' % hashlib.sha256(raw).hexdigest()]
    (root / "main/timetable_data.c").write_text("\n".join(code) + "\n", encoding="utf-8")
    print(json.dumps(dict(events=len(events), courses=len({e['name'] for e in events}),
                         first=events[0]['date'], last=events[-1]['date'],
                         sha256=hashlib.sha256(raw).hexdigest()), ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("ics", type=Path)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    generate(args.ics, args.root)
