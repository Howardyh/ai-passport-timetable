"""Install verified course firmware without overwriting the original application/data.

Use --mode courses/factory to switch existing applications. --install additionally
requires --build and writes only bootloader, partition table and the course slot.
The entire-Flash merged image must NEVER be used to preserve this device.
"""
import argparse
import binascii
import hashlib
import json
import struct
import subprocess
import sys
import tempfile
from pathlib import Path
from verify_firmware import parse_partition_table, parse_flash_args

ROOT=Path(__file__).resolve().parents[1]
PROTECTED={
    'nvs':(1,2,0x9000,0x6000), 'phy_init':(1,1,0xf000,0x1000),
    'factory':(0,0,0x10000,0x300000), 'imgstore':(1,0x82,0x310000,0x20000),
    'imgframe':(1,0x82,0x330000,0x26000), 'cardid':(1,2,0x356000,0x4000),
    'imguser':(1,0x82,0x35a000,0x20000), 'audio':(1,0x82,0x37a000,0x80000),
    'imgava':(1,0x82,0x3fa000,0x100000),
}

def check_table(raw, upgraded=False):
    parts, md5=parse_partition_table(raw)
    if not md5: raise ValueError('Partition MD5 required')
    actual={p.label:(p.kind,p.subtype,p.offset,p.size) for p in parts}
    for name,expected in PROTECTED.items():
        if actual.get(name)!=expected: raise ValueError(f'Incompatible original partition: {name}')
    extra=set(actual)-set(PROTECTED)
    if extra-set(('otadata','courses')): raise ValueError('Unexpected partitions; do not overwrite')
    if upgraded or extra:
        if actual.get('otadata')!=(1,0,0x4fa000,0x2000): raise ValueError('Unexpected OTA metadata')
        if actual.get('courses')!=(0,0x10,0x500000,0x300000): raise ValueError('Unexpected courses slot')
    return actual

def boot_bytes(mode):
    data=bytearray(b'\xff'*8192)
    if mode=='courses':
        seq=struct.pack('<I',1)
        crc=binascii.crc32(seq,0xffffffff)&0xffffffff
        for offset in (0,4096):
            data[offset:offset+4]=seq
            data[offset+24:offset+28]=struct.pack('<I',2) # ESP_OTA_IMG_VALID
            data[offset+28:offset+32]=struct.pack('<I',crc)
    return data

def main():
    from serial.tools.list_ports import comports
    p=argparse.ArgumentParser()
    p.add_argument('--port')
    p.add_argument('--mode',choices=['courses','factory'],default='courses')
    p.add_argument('--install',action='store_true')
    p.add_argument('--build',type=Path)
    args=p.parse_args()
    if not args.port:
        candidates=[port.device for port in comports() if port.vid==0x303A and port.pid==0x1001]
        if len(candidates)!=1: p.error('Connect one AI Passport or specify --port COMx')
        args.port=candidates[0]
    def tool(*params):
        subprocess.run([sys.executable,'-m','esptool','--chip','esp32c3','--port',args.port,
                        '--baud','460800',*map(str,params)],check=True)
    with tempfile.TemporaryDirectory(prefix='passport-device-') as tmp:
        tmp=Path(tmp)
        old=tmp/'partitions.bin'
        tool('read_flash','0x8000','0x1000',old)
        check_table(old.read_bytes(),upgraded=not args.install)
        selector=tmp/'boot.bin'; selector.write_bytes(boot_bytes(args.mode))
        if args.install:
            if not args.build: p.error('--install requires --build')
            build=args.build.resolve()
            subprocess.run([sys.executable,str(ROOT/'tools/verify_firmware.py'),str(build)],check=True)
            check_table((build/'partition_table/partition-table.bin').read_bytes(),upgraded=True)
            offsets=parse_flash_args((build/'flash_args').read_text())
            if offsets.get('FoloToy-AI-Passport.bin')!=0x500000: raise ValueError('Wrong app offset')
            images=[(0,build/'bootloader/bootloader.bin'),(0x8000,build/'partition_table/partition-table.bin'),
                    (0x500000,build/'FoloToy-AI-Passport.bin'),(0x4fa000,selector)]
            manifest=[dict(offset=hex(offset),size=file.stat().st_size,
                           sha256=hashlib.sha256(file.read_bytes()).hexdigest()) for offset,file in images]
            # Erase sectors must not overlap any existing program or data partition.
            for offset,file in images:
                end=(offset+file.stat().st_size+4095)&~4095
                if any(offset<start+size and end>start for _,_,start,size in PROTECTED.values()):
                    raise ValueError('Write would overlap preserved data')
            (ROOT/'private').mkdir(exist_ok=True)
            (ROOT/'private/install-manifest.json').write_text(json.dumps(manifest,indent=2))
            tool('write_flash','--flash_mode','dio','--flash_freq','80m','--flash_size','8MB',
                 *[v for offset,file in images for v in (hex(offset),file)])
        else:
            tool('write_flash','0x4fa000',selector)
    print('Selected:',args.mode)

if __name__=='__main__': main()
