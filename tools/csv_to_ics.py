"""Convert explicit lesson rows to ICS locally (no network access)."""
import argparse
import csv
import datetime as dt
from pathlib import Path
from import_timetable import parse_ics


def escape(value):
    return value.replace('\\', '\\\\').replace('\n', '\\n').replace(',', '\\,').replace(';', '\\;')


def fold(line):
    parts, current = [], ''
    for char in line:
        if len((current + char).encode('utf-8')) > 75:
            parts.append(current)
            current = ' '
        current += char
    return '\r\n'.join(parts + [current])


def convert(text):
    reader = csv.DictReader(text.lstrip('\ufeff').splitlines(keepends=True))
    required = {'date', 'start', 'end', 'name', 'location', 'description'}
    if not required.issubset(reader.fieldnames or []):
        raise ValueError('CSV requires date,start,end,name,location,description columns')
    lines = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//AI Passport Timetable//EN', 'CALSCALE:GREGORIAN']
    for i, row in enumerate(reader, 1):
        if None in row or any(row[k] is None for k in required):
            raise ValueError(f'Invalid CSV row {i}')
        date = dt.date.fromisoformat(row['date'].strip())
        times = []
        for key in ('start', 'end'):
            time = dt.datetime.strptime(row[key].strip(), '%H:%M').time()
            times.append(dt.datetime.combine(date, time).strftime('%Y%m%dT%H%M%S'))
        lines.extend(['BEGIN:VEVENT', f'UID:lesson-{i}@passport.example', 'DTSTAMP:20260101T000000Z',
                      'DTSTART;TZID=Asia/Shanghai:' + times[0], 'DTEND;TZID=Asia/Shanghai:' + times[1],
                      'SUMMARY:' + escape(row['name'].strip()), 'LOCATION:' + escape(row['location']),
                      'DESCRIPTION:' + escape(row['description']), 'END:VEVENT'])
    lines.append('END:VCALENDAR')
    result = '\r\n'.join(fold(line) for line in lines) + '\r\n'
    parse_ics(result)  # Reject empty, overnight and overlong records before writing.
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('csv', type=Path)
    p.add_argument('--output', type=Path, default=Path('private/timetable.ics'))
    args = p.parse_args()
    result = convert(args.csv.read_text(encoding='utf-8-sig'))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(result.encode('utf-8'))
    print('ICS written locally. Do not commit personal calendars.')
