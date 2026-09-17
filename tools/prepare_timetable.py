"""Import a local ICS/CSV and generate the firmware's Chinese font subsets."""
import argparse
from pathlib import Path
import subprocess
import sys
from csv_to_ics import convert
from import_timetable import generate

ROOT = Path(__file__).resolve().parents[1]

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('calendar', type=Path)
    p.add_argument('--node', default='node')
    p.add_argument('--converter', type=Path, default=ROOT / 'node_modules/lv_font_conv/lv_font_conv.js')
    args = p.parse_args()
    if not args.converter.is_file():
        p.error('Run pnpm install --frozen-lockfile first, or specify --converter /path/to/lv_font_conv.js')
    source = args.calendar.resolve()
    if source.suffix.lower() == '.csv':
        data = convert(source.read_text(encoding='utf-8-sig'))
        source = ROOT / 'private/converted.ics'
        source.parent.mkdir(exist_ok=True)
        source.write_bytes(data.encode('utf-8'))
    elif source.suffix.lower() != '.ics':
        p.error('Input must be an ICS or CSV file')
    generate(source, ROOT)
    subprocess.run([sys.executable, str(ROOT / 'tools/make_course_fonts.py'), '--node', args.node,
                    '--converter', str(args.converter.resolve())], check=True)
