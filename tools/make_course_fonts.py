"""Generate all UI sizes from the actual course/application Unicode inventory."""
import argparse
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--node', required=True)
    p.add_argument('--converter', required=True)
    args=p.parse_args()
    source=(ROOT/'main/course_app.c').read_text(encoding='utf-8')
    source+=(ROOT/'main/timetable_data.c').read_text(encoding='utf-8')
    chars=sorted({ord(c) for c in source if ord(c)>127} | set(range(32,127)))
    # Inventory includes comments as a conservative superset of UI text.
    ranges=','.join(hex(c) for c in chars)
    folder=ROOT/'assets/fonts'
    (ROOT/'private/font-inventory.json').write_text(json.dumps(chars),encoding='utf-8')
    (folder/'course_glyphs.h').write_text('#pragma once\n#include <stdint.h>\nstatic const uint32_t course_glyphs[] = {'+ranges+'};\n',encoding='utf-8')
    for size in (14,16,20):
        subprocess.run([args.node,args.converter,'--font',str(folder/'NotoSansCJKsc-Regular.otf'),
                        '--range',ranges,'--size',str(size),'--bpp','4','--format','lvgl',
                        '--no-compress','--no-kerning','--lv-font-name',f'course_font_{size}',
                        '--lv-include','lvgl.h','--output',str(folder/f'course_font_{size}.c')],check=True)
    print(f'Generated {len(chars)} glyphs at 14/16/20 px; firmware verifies descriptors on boot.')

if __name__=='__main__': main()
