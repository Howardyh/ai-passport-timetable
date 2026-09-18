"""Build a fictional, verified firmware template and standalone Windows EXE."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'desktop'))
from payload import build_bundle, verify_image, MAGIC, CAPACITY
from import_timetable import parse_ics


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--firmware-only', action='store_true')
    p.add_argument('--package-only', action='store_true')
    args = p.parse_args()
    build = ROOT / 'build/desktop/firmware'
    resources = ROOT / 'build/desktop/resources'
    build.mkdir(parents=True, exist_ok=True); resources.mkdir(parents=True, exist_ok=True)
    def run(command): subprocess.run(list(map(str, command)), cwd=ROOT, check=True)
    if not args.package_only:
        if not os.environ.get('IDF_PATH'): p.error('Activate ESP-IDF 5.5.3 first')
        source = (ROOT / 'main/course_app.c').read_text(encoding='utf-8')
        chars = sorted({ord(c) for c in source if ord(c) > 127})
        # Explicitly use the committed fictional example, never private/.
        sample = parse_ics((ROOT / 'examples/timetable.ics').read_text(encoding='utf-8'))
        bundle = build_bundle(sample, ROOT / 'assets/fonts/NotoSansCJKsc-Regular.otf', chars)
        used = int.from_bytes(bundle[36:40], 'little')
        code = '#include <stdint.h>\nconst uint8_t desktop_blob[1048576] __attribute__((aligned(4))) = {\n'
        code += '\n'.join(','.join(str(v) for v in bundle[i:min(i+32, used)]) + ',' for i in range(0, used, 32)) + '\n};\n'
        (build / 'desktop_blob.c').write_text(code, encoding='utf-8')
        idf = Path(os.environ['IDF_PATH']) / 'tools/idf.py'
        run([sys.executable, idf, '-B', build, '-D', f'SDKCONFIG={build}/sdkconfig',
             '-D', 'PASSPORT_DESKTOP_TEMPLATE=ON', 'build'])
        run([sys.executable, idf, '-B', build, 'merge-bin', '-o', build / 'FoloToy-AI-Passport-full.bin'])
        run([sys.executable, ROOT / 'tools/verify_firmware.py', build])
        run([sys.executable, ROOT / 'tools/archive_firmware.py', 'create', build,
             '--archive-root', ROOT / 'build/desktop/archives'])
        app = (build / 'FoloToy-AI-Passport.bin').read_bytes()
        verify_image(app)
        assert app.count(MAGIC) == 1 and app.find(MAGIC) + CAPACITY < len(app)
        for src, dest in [('FoloToy-AI-Passport.bin', 'app.bin'), ('bootloader/bootloader.bin', 'bootloader.bin'),
                          ('partition_table/partition-table.bin', 'partition-table.bin')]:
            shutil.copyfile(build / src, resources / dest)
        shutil.copyfile(ROOT / 'assets/fonts/NotoSansCJKsc-Regular.otf', resources / 'NotoSansCJKsc-Regular.otf')
        (resources / 'ui_chars.json').write_text(json.dumps(chars), encoding='utf-8')
        names = ['app.bin', 'bootloader.bin', 'partition-table.bin', 'NotoSansCJKsc-Regular.otf', 'ui_chars.json']
        commit = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        (resources / 'manifest.json').write_text(json.dumps({'format': 1, 'source_commit': commit, 'files': {
            n: hashlib.sha256((resources / n).read_bytes()).hexdigest() for n in names}}, indent=2))
        shutil.copyfile(ROOT / 'examples/timetable.csv', resources / 'example.csv')
        shutil.copyfile(ROOT / 'examples/timetable.ics', resources / 'example.ics')
        shutil.copyfile(ROOT / 'LICENSE', resources / 'LICENSE.txt')
        shutil.copyfile(ROOT / 'assets/fonts/OFL.txt', resources / 'OFL.txt')
    if not args.firmware_only:
        from backend import verify_resources
        manifest = verify_resources(resources)
        commit = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        if manifest.get('source_commit') != commit:
            raise RuntimeError('Rebuild the template from this source commit before packaging.')
        import importlib.metadata
        license_dir=resources/'licenses'; license_dir.mkdir(exist_ok=True)
        for name in ['esptool','pyserial','Pillow','fonttools','pyinstaller']:
            distribution=importlib.metadata.distribution(name)
            for file in distribution.files or []:
                if any(word in str(file).lower() for word in ['license','copying']) and distribution.locate_file(file).is_file():
                    shutil.copyfile(distribution.locate_file(file), license_dir/(name+'-'+Path(file).name))
        from PIL import Image, ImageDraw
        icon = Image.new('RGBA', (256,256), (0,0,0,0))
        draw = ImageDraw.Draw(icon)
        draw.rounded_rectangle((8,8,248,248), radius=52, fill='#087f8c')
        draw.rounded_rectangle((50,59,206,205), radius=22, fill='#ffffff')
        draw.rectangle((50,92,206,105), fill='#c9e9ed')
        for x in (86,170): draw.rounded_rectangle((x-6,43,x+6,77), radius=6, fill='#ffffff')
        for x,y in ((77,126),(112,126),(147,126),(77,163),(112,163)):
            draw.rounded_rectangle((x,y,x+22,y+22), radius=5, fill='#087f8c')
        draw.rounded_rectangle((147,163,169,185), radius=5, fill='#efb667')
        icon_path=ROOT/'build/desktop/timetable.ico'
        icon.save(icon_path, sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])
        run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--onefile', '--windowed',
             '--name', 'PassportTimetable', '--icon', icon_path, '--distpath', ROOT / 'dist', '--workpath', ROOT / 'build/desktop/pyinstaller',
             '--specpath', ROOT / 'build/desktop', '--paths', ROOT / 'tools', '--paths', ROOT / 'desktop',
             '--add-data', f'{resources}{os.pathsep}resources', '--collect-all', 'esptool',
             '--collect-submodules', 'fontTools.ttLib.tables', ROOT / 'desktop/app.py'])


if __name__ == '__main__': main()
