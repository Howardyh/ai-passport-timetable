"""Offline calendar/font bundle and ESP image personalization. No network calls."""
import hashlib
import json
import struct
import zlib
from pathlib import Path

MAGIC = b'PASSPORT-TIMETABLE-BUNDLE-V1'.ljust(32, b'\0')
CAPACITY = 1024 * 1024
MAX_EVENTS = 1024
HEADER = 136
EVENT = struct.Struct('<iHHIII')
GLYPH = struct.Struct('<IIHHHhhH')


def identity(events):
    return hashlib.sha256(json.dumps(events, sort_keys=True, ensure_ascii=False,
                                    separators=(',', ':')).encode()).hexdigest()


def build_bundle(events, font_path, ui_chars):
    from PIL import Image, ImageDraw, ImageFont
    from fontTools.ttLib import TTFont
    if not 1 <= len(events) <= MAX_EVENTS:
        raise ValueError(f'课表需要包含 1–{MAX_EVENTS} 次课程')
    chars = set(ui_chars) | set(range(32, 127))
    for e in events:
        if not 0 <= e['start'] < e['end'] < 1440:
            raise ValueError('课程起止时间无效')
        for key in ('name', 'location', 'description'):
            if len(e[key].encode()) > 384 or '\0' in e[key]:
                raise ValueError('课程文字过长或含无效字符')
            chars.update(ord(c) for c in e[key] if c not in '\r\n\t')
    chars = sorted(chars)
    if len(chars) > 4096:
        raise ValueError('不同字符超过 4096 个，请减少课程备注或分学期导入')
    with TTFont(font_path, lazy=True) as font:
        cmap = font.getBestCmap()
        missing = [c for c in chars if c not in cmap]
    if missing:
        raise ValueError('字库不支持这些字符：' + ' '.join(f'U+{c:04X}' for c in missing[:12]))
    data = bytearray(HEADER + len(events) * EVENT.size)
    strings = {}
    def string(value):
        if value not in strings:
            strings[value] = len(data)
            data.extend(value.encode('utf-8') + b'\0')
        return strings[value]
    for i, e in enumerate(events):
        offsets = [string(e[k]) for k in ('name', 'location', 'description')]
        EVENT.pack_into(data, HEADER + i * EVENT.size, e['day'], e['start'], e['end'], *offsets)
    fonts = []
    for size in (14, 16, 20):
        while len(data) % 4: data.append(0)
        fonts.append(len(data))
        records = len(data) + 16
        data.extend(struct.pack('<IIII', len(chars), records, size + 6, 6))
        data.extend(bytes(GLYPH.size * len(chars)))
        font = ImageFont.truetype(str(font_path), size)
        for i, cp in enumerate(chars):
            ch = chr(cp)
            left, top, right, bottom = font.getbbox(ch, anchor='ls')
            width, height = right - left, bottom - top
            if width > 64 or height > 64:
                raise ValueError('字形尺寸超出设备限制')
            bitmap = Image.new('L', (max(1, width), max(1, height)))
            ImageDraw.Draw(bitmap).text((-left, -top), ch, font=font, fill=255, anchor='ls')
            offset = len(data)
            if width and height: data.extend(bitmap.tobytes())
            if len(data) > CAPACITY:
                raise ValueError('课表或中文字库过大，请减少课程文字后重试')
            GLYPH.pack_into(data, records + i * GLYPH.size, cp, offset, width, height,
                            round(font.getlength(ch)), left, -bottom, 0)
    if len(data) > CAPACITY:
        raise ValueError('课表或中文字库过大，请减少课程文字后重试')
    data[:32] = MAGIC
    struct.pack_into('<10I', data, 32, 1, len(data), 0, len(events), HEADER,
                     HEADER + len(events) * EVENT.size, *fonts, 0)
    data[72:136] = identity(events).encode('ascii')
    struct.pack_into('<I', data, 40, zlib.crc32(data[44:]))
    return bytes(data).ljust(CAPACITY, b'\0')


def image_segments(image):
    if len(image) < 24 or image[0] != 0xE9 or not 1 <= image[1] <= 16 or image[23] != 1:
        raise ValueError('不支持的固件镜像格式')
    if struct.unpack_from('<H', image, 12)[0] != 5:
        raise ValueError('固件目标不是 ESP32-C3')
    pos, segments, checksum = 24, [], 0xEF
    for _ in range(image[1]):
        if pos + 8 > len(image): raise ValueError('固件段头损坏')
        _, size = struct.unpack_from('<II', image, pos)
        pos += 8
        if pos + size > len(image): raise ValueError('固件段越界')
        segments.append((pos, size))
        for value in image[pos:pos + size]: checksum ^= value
        pos += size
    checksum_pos = pos | 15
    if len(image) != checksum_pos + 33:
        raise ValueError('固件尾部长度无效，拒绝修改签名或未知镜像')
    return segments, checksum_pos, checksum


def verify_image(image):
    segments, pos, checksum = image_segments(image)
    if image[pos] != checksum or hashlib.sha256(image[:pos + 1]).digest() != image[pos + 1:]:
        raise ValueError('固件校验失败')
    return segments


def personalize(template, bundle):
    segments = verify_image(template)
    if len(bundle) != CAPACITY or bundle[:32] != MAGIC:
        raise ValueError('课表数据包格式错误')
    count = template.count(MAGIC)
    offset = template.find(MAGIC)
    if count != 1 or not any(start <= offset and offset + CAPACITY <= start + size
                             for start, size in segments):
        raise ValueError('固件不包含唯一且完整的课程数据区域')
    result = bytearray(template)
    result[offset:offset + CAPACITY] = bundle
    _, pos, checksum = image_segments(result)
    result[pos] = checksum
    result[pos + 1:] = hashlib.sha256(result[:pos + 1]).digest()
    verify_image(result)
    return bytes(result)
