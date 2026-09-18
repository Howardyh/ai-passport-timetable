"""Offline installer boundary tests; never opens a serial port."""
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'desktop'), str(ROOT / 'tools')]
from payload import build_bundle, personalize, verify_image, MAGIC, CAPACITY, identity
from backend import read_calendar, validate_writes, install


class DesktopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.events = read_calendar(ROOT / 'examples/timetable.ics')
        cls.bundle = build_bundle(cls.events, ROOT / 'assets/fonts/NotoSansCJKsc-Regular.otf', [])

    def test_bundle_offsets_crc_and_utf8(self):
        b = self.bundle
        self.assertEqual(len(MAGIC), 32)
        self.assertEqual(len(b), CAPACITY)
        version, used, crc, count, off = struct.unpack_from('<5I', b, 32)
        self.assertEqual((version, count, off), (1, 3, 136))
        self.assertEqual(crc, zlib.crc32(b[44:used]))
        self.assertEqual(b[72:136].decode(), identity(self.events))
        name = struct.unpack_from('<I', b, off+8)[0]
        self.assertEqual(b[name:].split(b'\0', 1)[0].decode(), self.events[0]['name'])

    def test_patch_preserves_code_and_image_checksums(self):
        # One synthetic ESP32-C3 segment containing a complete reserved bundle.
        header = bytearray(24); header[0]=0xe9; header[1]=1; header[12]=5; header[23]=1
        body = b'code-before' + self.bundle + b'code-after'
        image = header + struct.pack('<II', 0x3c000020, len(body)) + body
        checksum=0xef
        for value in body: checksum ^= value
        image.extend(bytes((len(image) | 15)-len(image)))
        image.append(checksum); image.extend(hashlib.sha256(image).digest())
        verify_image(image)
        changed = list(self.events); changed[0] = {**changed[0], 'name':'另一门课程'}
        bundle = build_bundle(changed, ROOT / 'assets/fonts/NotoSansCJKsc-Regular.otf', [])
        result = personalize(bytes(image), bundle)
        self.assertEqual(result[32:43], b'code-before')
        self.assertEqual(result[43+CAPACITY:53+CAPACITY], b'code-after')
        self.assertEqual(len(result), len(image)); verify_image(result)
        broken=bytearray(image); broken[-1]^=1
        with self.assertRaises(ValueError): personalize(broken,bundle)

    def test_limits_and_unsupported_glyphs(self):
        for events in [[], self.events*342, [{**self.events[0], 'name':'\0'}],
                       [{**self.events[0], 'name':chr(0x10ffff)}]]:
            with self.assertRaises(ValueError):
                build_bundle(events,ROOT/'assets/fonts/NotoSansCJKsc-Regular.otf',[])

    def test_flash_bounds(self):
        with tempfile.TemporaryDirectory() as tmp:
            file=Path(tmp)/'test.bin'; file.write_bytes(b'\0'*4096)
            validate_writes([(0x500000,file)])
            for offset in [0x10000,0x310000,0x9000,0x4fc000,0x800000]:
                with self.assertRaises(ValueError): validate_writes([(offset,file)])
            file.write_bytes(b'\0'*(0x300000+1))
            with self.assertRaises(ValueError): validate_writes([(0x500000,file)])

    def test_security_failure_never_writes(self):
        calls=[]
        def fake(port,args,log,after='hard_reset'):
            calls.append(args[0]); return 'Secure Boot: Enabled\nFlash Encryption: Disabled'
        with patch('backend.prepare',return_value=[]), patch('backend.run_esptool',side_effect=fake):
            with self.assertRaises(RuntimeError): install(self.events,'TEST',lambda *a:None,lambda *a:None)
        self.assertEqual(calls,['get_security_info'])

    def test_incompatible_partitions_never_write(self):
        calls=[]
        def fake(port,args,log,after='hard_reset'):
            calls.append(args[0])
            if args[0]=='get_security_info': return 'Secure Boot: Disabled\nFlash Encryption: Disabled'
            if args[0]=='flash_id': return 'Detected flash size: 8MB'
            if args[0]=='read_flash': Path(args[-1]).write_bytes(bytes(4096))
            return ''
        with patch('backend.prepare',return_value=[]), patch('backend.run_esptool',side_effect=fake):
            with self.assertRaises(ValueError): install(self.events,'TEST',lambda *a:None,lambda *a:None)
        self.assertNotIn('write_flash',calls)

    def test_startup_is_only_selected_after_verification(self):
        from test_device_boot import table
        calls=[]
        def fake(port,args,log,after='hard_reset'):
            calls.append((args[0],after))
            if args[0]=='get_security_info': return 'Secure Boot: Disabled\nFlash Encryption: Disabled'
            if args[0]=='flash_id': return 'Detected flash size: 8MB'
            if args[0]=='read_flash': Path(args[-1]).write_bytes(table())
            return ''
        with patch('backend.prepare',return_value=[]), patch('backend.run_esptool',side_effect=fake), \
             patch('backend.synchronize',return_value={'time_valid':True}) as sync:
            install(self.events,'TEST',lambda *a:None,lambda *a:None)
        self.assertEqual(calls[-3:],[('write_flash','no_reset'),('verify_flash','no_reset'),('write_flash','hard_reset')])
        sync.assert_called_once_with('TEST',identity(self.events),len(self.events))

    def test_c_parser_accepts_bundle_rejects_corruption(self):
        compiler=os.environ.get('CC','cc')
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp); bundle=tmp/'bundle.bin'; bundle.write_bytes(self.bundle)
            harness=tmp/'test.c'
            harness.write_text('''#include "desktop_bundle.h"
#include <stdio.h>
#include <stdlib.h>
int main(int argc,char **argv) {
    (void)argc; FILE *f=fopen(argv[1],"rb"); if(!f) return 2;
    unsigned char *b=malloc(DESKTOP_CAPACITY); if(!b) return 3;
    if(fread(b,1,DESKTOP_CAPACITY,f)!=DESKTOP_CAPACITY) return 4;
    fclose(f); timetable_event_t e[DESKTOP_MAX_EVENTS]; size_t n=0;
    if(!desktop_bundle_parse(b,DESKTOP_CAPACITY,e,&n) || n!=3) return 5;
    if(e[0].start!=480 || e[0].end!=570) return 6;
    b[150]^=1;
    if(desktop_bundle_parse(b,DESKTOP_CAPACITY,e,&n)) return 7;
    free(b); return 0;
}
''')
            exe=tmp/('parser.exe' if os.name=='nt' else 'parser')
            subprocess.run([compiler,'-std=c11','-Wall','-Wextra','-Werror','-I'+str(ROOT/'main'),
                            str(harness),str(ROOT/'main/desktop_bundle.c'),'-o',str(exe)],check=True)
            subprocess.run([str(exe),str(bundle)],check=True)


if __name__=='__main__': unittest.main()
