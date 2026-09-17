import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from csv_to_ics import convert
from import_timetable import parse_ics
from check_public_files import forbidden


class TemplateTests(unittest.TestCase):
    def test_sample_roundtrip(self):
        root = Path(__file__).resolve().parents[1]
        events = parse_ics(convert((root / 'examples/timetable.csv').read_text(encoding='utf-8')))
        self.assertEqual(len(events), 3)
        self.assertEqual(events[0]['start'], 480)
        self.assertEqual(events[0]['name'], '示例课程甲')
        self.assertEqual(events, parse_ics((root / 'examples/timetable.ics').read_text(encoding='utf-8')))

    def test_escaping_and_folding(self):
        name = '课程' * 35 + ',;\\'
        text = 'date,start,end,name,location,description\n2027-03-01,08:00,09:00,"' + name + '",教室,"第一行\n第二行"\n'
        ics = convert(text)
        self.assertTrue(all(len(line.encode()) <= 75 for line in ics.split('\r\n')))
        event = parse_ics(ics)[0]
        self.assertEqual(event['name'], name)
        self.assertEqual(event['description'], '第一行\n第二行')

    def test_invalid_csv(self):
        for text in ['date,name\n2027-03-01,错误',
                     'date,start,end,name,location,description\n',
                     'date,start,end,name,location,description\n2027-03-01,20:00,08:00,错误,,\n']:
            with self.assertRaises(ValueError):
                convert(text)

    def test_private_paths(self):
        for path in ['private/a.json', 'main/timetable_data.c', 'x.ics', 'build/app.bin',
                     'assets/fonts/course_font_14.c', 'a.log', '.env.local', 'my-calendar.csv']:
            self.assertTrue(forbidden(path), path)
        for path in ['examples/timetable.ics', 'examples/timetable.csv', 'partitions.csv', 'main/course_app.c', 'assets/fonts/OFL.txt']:
            self.assertFalse(forbidden(path), path)


if __name__ == '__main__':
    unittest.main()
