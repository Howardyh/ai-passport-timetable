import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from import_timetable import parse_ics

def calendar(extra='', start='20260924T070000Z', end='20260924T082000Z'):
    return f'BEGIN:VCALENDAR\nBEGIN:VEVENT\nDTSTART:{start}\nDTEND:{end}\nSUMMARY:测试课程\nLOCATION:A1\\,二楼\nDESCRIPTION:教师\\n节次\n{extra}\nEND:VEVENT\nEND:VCALENDAR'

class ImportTests(unittest.TestCase):
    def test_utc_and_escaping(self):
        e = parse_ics(calendar())[0]
        self.assertEqual((e['date'],e['start'],e['end']), ('2026-09-24',900,980))
        self.assertEqual(e['location'], 'A1,二楼')
        self.assertEqual(e['description'], '教师\n节次')
    def test_local_date_rollover(self):
        self.assertEqual(parse_ics(calendar(start='20260924T230000Z',end='20260925T000000Z'))[0]['date'], '2026-09-25')
    def test_recurrence_is_not_silently_ignored(self):
        with self.assertRaises(ValueError): parse_ics(calendar('RRULE:FREQ=WEEKLY;COUNT=3'))
    def test_invalid_interval(self):
        with self.assertRaises(ValueError): parse_ics(calendar(end='20260924T060000Z'))
    def test_folded_chinese(self):
        self.assertEqual(parse_ics(calendar().replace('测试课程','测试\n 课程'))[0]['name'], '测试课程')

if __name__ == '__main__': unittest.main()
