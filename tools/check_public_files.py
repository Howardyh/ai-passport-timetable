"""Reject private/generated paths in the Git index, including force-added files.

This is a path guard, not a general secret detector. Review source diffs too.
"""
from pathlib import PurePosixPath
import subprocess
import sys


def forbidden(name):
    path = PurePosixPath(name.lower())
    if any(p in {'private', 'build', 'node_modules', '__pycache__', 'managed_components'} for p in path.parts):
        return True
    if str(path) == 'main/timetable_data.c' or path.name.startswith('course_font_') or path.name == 'course_glyphs.h':
        return True
    if path.suffix in {'.bin', '.elf', '.map', '.log', '.pem', '.key', '.p12'}:
        return True
    if path.name == '.env' or path.name.startswith('.env.'):
        return True
    if path.suffix == '.ics' and str(path) != 'examples/timetable.ics':
        return True
    if path.suffix == '.csv' and str(path) not in {'partitions.csv', 'examples/timetable.csv'}:
        return True
    return False


if __name__ == '__main__':
    names = subprocess.check_output(['git', 'ls-files', '-z']).decode('utf-8').split('\0')
    blocked = [n for n in names if n and forbidden(n)]
    for name in blocked:
        print('Blocked private/generated path:', name, file=sys.stderr)
    if blocked:
        sys.exit(1)
    print('Public path guard: PASS (review content separately)')
