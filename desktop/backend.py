"""Desktop workflow. Serial writes occur only through the explicit install action."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

from import_timetable import parse_ics
from csv_to_ics import convert
from device_boot import check_table, boot_bytes, PROTECTED
from payload import build_bundle, personalize, identity, verify_image


def resource_dir():
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS) / 'resources'
    return Path(__file__).resolve().parents[1] / 'build/desktop/resources'


def read_calendar(path):
    path = Path(path)
    if path.stat().st_size > 5 * 1024 * 1024:
        raise ValueError('课表文件不能超过 5 MB')
    text = path.read_text(encoding='utf-8-sig')
    if path.suffix.lower() == '.csv': text = convert(text)
    elif path.suffix.lower() != '.ics': raise ValueError('请选择 .ics 或 UTF-8 .csv 文件')
    return parse_ics(text)


def ports():
    from serial.tools.list_ports import comports
    return [(p.device, p.description, p.vid == 0x303A and p.pid == 0x1001) for p in comports()]


def verify_resources(root):
    root = Path(root)
    manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
    required = {'app.bin', 'bootloader.bin', 'partition-table.bin', 'NotoSansCJKsc-Regular.otf', 'ui_chars.json'}
    if set(manifest['files']) != required or manifest['format'] != 1:
        raise ValueError('安装程序资源清单无效，请重新下载程序')
    for name in required:
        if hashlib.sha256((root / name).read_bytes()).hexdigest() != manifest['files'][name]:
            raise ValueError('内置资源校验失败：' + name)
    check_table((root / 'partition-table.bin').read_bytes(), upgraded=True)
    verify_image((root / 'app.bin').read_bytes())
    return manifest


def prepare(events, destination, root=None):
    root = Path(root or resource_dir())
    verify_resources(root)
    bundle = build_bundle(events, root / 'NotoSansCJKsc-Regular.otf',
                          json.loads((root / 'ui_chars.json').read_text()))
    app = personalize((root / 'app.bin').read_bytes(), bundle)
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    images = [(0, root / 'bootloader.bin'), (0x8000, root / 'partition-table.bin'),
              (0x500000, destination / 'courses.bin')]
    images[2][1].write_bytes(app)
    validate_writes(images)
    return images


def validate_writes(images):
    allowed = {0: 0x8000, 0x8000: 0x9000, 0x4FA000: 0x4FC000, 0x500000: 0x800000}
    for offset, path in images:
        size = Path(path).stat().st_size
        end = (offset + size + 4095) & ~4095
        if not size or offset not in allowed or end > allowed[offset]:
            raise ValueError('固件写入地址或大小不符合安全分区布局')
        if any(offset < start + length and end > start for _, _, start, length in PROTECTED.values()):
            raise ValueError('拒绝覆盖原厂程序或原厂数据')


def tool_command():
    if getattr(sys, 'frozen', False): return [sys.executable, '--esptool']
    return [sys.executable, '-m', 'esptool']


def run_esptool(port, args, log, after='hard_reset'):
    command = tool_command() + ['--chip', 'esp32c3', '--port', port, '--baud', '460800', '--after', after] + list(map(str, args))
    options = {'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}
    output = []
    with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True, encoding='utf-8', errors='replace', **options) as process:
        for line in process.stdout:
            line = line.strip()
            if line:
                output.append(line)
                log(line)
        if process.wait() != 0:
            raise RuntimeError('设备操作失败。请保持亮屏，检查 USB 数据线及串口占用后重试。')
    return '\n'.join(output)


def synchronize(port, expected=None, count=None, timeout=25):
    import serial
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            dev = serial.Serial(port=None, baudrate=115200, timeout=0.3)
            dev.dtr = False; dev.rts = False; dev.port = port
            dev.open()
            with dev:
                dev.reset_input_buffer()
                for _ in range(4):
                    dev.write((json.dumps({'cmd': 'time', 'epoch': int(time.time())}) + '\n').encode())
                    dev.write(b'{"cmd":"status"}\n')
                    end = min(deadline, time.monotonic() + 1.5)
                    while time.monotonic() < end:
                        line = dev.readline().decode('utf-8', errors='replace')
                        marker = 'COURSE STATUS '
                        if marker not in line: continue
                        try: status = json.loads(line.split(marker, 1)[1])
                        except ValueError: continue
                        if status.get('time_valid') and abs(status.get('epoch', 0) - time.time()) < 10:
                            if expected is not None and (status.get('source') != expected or status.get('total_events') != count):
                                continue
                            return status
        except (OSError, serial.SerialException):
            time.sleep(0.5)
    raise RuntimeError('未确认课程表启动和校时。若刚完成烧录，请重新开机，再点击“同步时间”检查设备。')


def install(events, port, progress, log, root=None):
    progress(5, '正在生成课程数据与中文字库…')
    with tempfile.TemporaryDirectory(prefix='passport-timetable-') as tmp:
        tmp = Path(tmp)
        images = prepare(events, tmp, root)
        progress(25, '正在检查设备芯片与安全设置…')
        info = run_esptool(port, ['get_security_info'], log)
        if 'Secure Boot: Disabled' not in info or 'Flash Encryption: Disabled' not in info:
            raise RuntimeError('未确认设备关闭安全启动和 Flash 加密，已停止烧录。')
        info = run_esptool(port, ['flash_id'], log)
        if 'Detected flash size: 8MB' not in info:
            raise RuntimeError('此版本仅支持 8 MB Flash 的 AI Passport，已停止烧录。')
        progress(35, '正在验证原厂分区兼容性…')
        table = tmp / 'current-partitions.bin'
        run_esptool(port, ['read_flash', '0x8000', '0x1000', table], log)
        check_table(table.read_bytes())
        progress(45, '正在烧录，请保持 USB 连接…')
        pairs = [v for offset, path in images for v in (hex(offset), path)]
        run_esptool(port, ['write_flash', '--flash_mode', 'dio', '--flash_freq', '80m', '--flash_size', '8MB', *pairs], log, 'no_reset')
        progress(78, '正在校验写入内容…')
        run_esptool(port, ['verify_flash', *pairs], log, 'no_reset')
        selector = tmp / 'selection.bin'; selector.write_bytes(boot_bytes('courses'))
        validate_writes([(0x4FA000, selector)])
        progress(88, '正在启动课程表…')
        run_esptool(port, ['write_flash', '0x4fa000', selector], log)
        progress(94, '正在校时并确认课程表…')
        status = synchronize(port, identity(events), len(events))
        progress(100, '安装完成，已确认课表启动并同步时间')
        return status
