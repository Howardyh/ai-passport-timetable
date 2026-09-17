"""Capture actual LVGL output from the board; save an RGB PNG."""
import argparse
import json
import time
from pathlib import Path
import serial

def capture(port,output):
    from PIL import Image
    rows={}
    device=serial.Serial(port=None,baudrate=115200,timeout=0.5)
    device.dtr=False; device.rts=False; device.port=port; device.open()
    with device:
        device.reset_input_buffer()
        device.write(b'{"cmd":"screen"}\n')
        deadline=time.monotonic()+30
        received=bytearray()
        while time.monotonic()<deadline:
            received.extend(device.read(device.in_waiting or 1))
            if b'COURSE SCREEN END\n' in received or b'COURSE ERROR' in received: break
        # Bulk reads avoid dropping bytes in Windows' receive queue while readline
        # processes individual characters of this 300 KB diagnostic stream.
        for raw in received.splitlines():
            line=raw.decode('ascii',errors='replace').strip()
            if line.startswith('COURSE PIX '):
                _,_,row,hex_data=line.split(' ',3)
                data=bytes.fromhex(hex_data)
                if len(data)!=480: raise RuntimeError('Incomplete pixel row')
                rows[int(row)]=data
            if line.startswith('COURSE ERROR'): raise RuntimeError(line)
    if set(rows)!=set(range(320)): raise RuntimeError(f'Incomplete screenshot: {len(rows)}/320 rows')
    pixels=bytearray()
    for y in range(320):
        for x in range(240):
            value=int.from_bytes(rows[y][x*2:x*2+2],'little')
            pixels.extend((((value>>11)&31)*255//31,((value>>5)&63)*255//63,(value&31)*255//31))
    Image.frombytes('RGB',(240,320),bytes(pixels)).save(output)
    print('Saved',output)

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--port',required=True); p.add_argument('output',type=Path)
    args=p.parse_args(); capture(args.port,args.output)
