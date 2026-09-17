import binascii
import struct
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from device_boot import boot_bytes, check_table, PROTECTED
import hashlib

def table(changed=False):
    entries=dict(PROTECTED)
    entries['otadata']=(1,0,0x4fa000,0x2000)
    entries['courses']=(0,0x10,0x500000,0x300000)
    if changed: entries['factory']=(0,0,0x10000,0x7f0000)
    data=b''.join(struct.pack('<HBBII16sI',0x50aa,*value,name.encode(),0) for name,value in entries.items())
    data+=b'\xeb\xeb'+b'\xff'*14+hashlib.md5(data).digest()
    return data.ljust(4096,b'\xff')

class BootTests(unittest.TestCase):
    def test_matching_original_ranges(self):
        self.assertEqual(check_table(table(),True)['courses'][2],0x500000)
    def test_refuse_incompatible_layout(self):
        with self.assertRaises(ValueError): check_table(table(True),True)
    def test_redundant_boot_records(self):
        data=boot_bytes('courses')
        for offset in (0,4096):
            self.assertEqual(struct.unpack_from('<I',data,offset)[0],1)
            self.assertEqual(struct.unpack_from('<I',data,offset+24)[0],2)
            self.assertEqual(struct.unpack_from('<I',data,offset+28)[0],binascii.crc32(data[offset:offset+4],0xffffffff)&0xffffffff)
        self.assertEqual(boot_bytes('factory'),b'\xff'*8192)

if __name__=='__main__': unittest.main()
