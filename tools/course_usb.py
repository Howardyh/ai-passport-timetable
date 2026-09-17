"""Set time, configure optional Wi-Fi, or inspect the course device over USB."""
import argparse
import getpass
import json
import time
import serial
from serial.tools.list_ports import comports

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--port')
    p.add_argument('--wifi', action='store_true')
    p.add_argument('--status-only', action='store_true')
    args=p.parse_args()
    candidates=[port.device for port in comports() if port.vid==0x303A]
    if not args.port and len(candidates)!=1:
        p.error('Connect one ESP32 device or specify --port COMx')
    port=args.port or candidates[0]
    dev=serial.Serial(port=None,baudrate=115200,timeout=0.2)
    dev.dtr=False; dev.rts=False; dev.port=port; dev.open()
    with dev:
        def send(obj): dev.write((json.dumps(obj,ensure_ascii=False)+'\n').encode())
        if not args.status_only: send(dict(cmd='time',epoch=int(time.time())))
        if args.wifi:
            ssid=input('2.4 GHz Wi-Fi SSID (empty to clear): ')
            password=getpass.getpass('Wi-Fi password: ') if ssid else ''
            send(dict(cmd='wifi',ssid=ssid,password=password))
        send(dict(cmd='status'))
        deadline=time.monotonic()+5
        confirmed=args.status_only
        while time.monotonic()<deadline:
            text=dev.readline().decode('utf-8',errors='replace').strip()
            if 'COURSE ' in text:
                text=text[text.index('COURSE '):]
                print(text)
                confirmed=confirmed or text=='COURSE TIME OK'
                if text.startswith('COURSE STATUS '):
                    status=json.loads(text[len('COURSE STATUS '):])
                    confirmed=confirmed or (status.get('time_valid') and abs(status.get('epoch',0)-time.time())<10)
        if not confirmed: raise SystemExit('No time acknowledgement received; device may need a restart.')

if __name__=='__main__': main()
