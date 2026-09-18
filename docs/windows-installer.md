<p align="right"><a href="windows-installer.zh_CN.md">简体中文</a> · <strong>English</strong></p>

# Windows timetable installer

`PassportTimetable.exe` is a standalone Windows x64 application. End users do
not need Python, Node.js, ESP-IDF or an internet connection. The executable
includes the firmware template, font, calendar converter and serial tools.

## Use

1. Open the EXE and select an ICS or UTF-8 CSV calendar. Check dates, times,
   course names and locations in the preview; select a row to see its notes.
2. Connect one AI Passport with a USB data cable, keep it powered on, and
   select its serial port. Use Refresh if it does not appear immediately.
3. Click **Install timetable**. Keep the cable connected until completion.
   The installer creates the course data/font locally, checks the ESP32-C3,
   8 MB flash, security settings and partition layout, writes and verifies
   the firmware, selects the course app, then confirms its data hash and time.

You can save a fictional CSV template or load a fictional sample without a
device. Each CSV row represents one occurrence. Recurring ICS events need to
be expanded before import. The current limit is 1,024 occurrences and a 1 MB
combined data/font area. Unsupported characters and oversized imports fail
before any device write. The time zone is UTC+8.

The **Sync time** button also works with the previous course firmware. Full
power-off loses clock validity; reconnect and synchronize it afterward.

## What installation changes

The layout is unchanged from the existing course application. The original
factory application and its image/card/audio partitions stay in place on
compatible devices. This does not mean the factory features are merged into
the timetable: they remain a separate boot option in the device tools menu.
Secure boot/encrypted devices and incompatible layouts are refused.

Only the bootloader, partition table, course slot and OTA selector are written.
There is no full-chip erase or merged-image flash. Power loss during a write
can interrupt installation; reconnect and rerun the installer. If writing
completed but startup confirmation failed, the app reports that distinction
and you can restart the device and synchronize time.

Calendars, previews and generated firmware stay on the computer. Temporary
personalized images are deleted when the operation exits normally. The EXE
contains only fictional sample courses. Do not publish a personalized image,
device capture or log. The application has no telemetry, cloud conversion,
automatic upload or automatic firmware update.

## Build from source

Use an activated ESP-IDF 5.5.3 Windows environment with Python 3.12 and Tcl/Tk:

```sh
python -m pip install -r desktop/requirements.txt
python tools/build_desktop.py
```

The script builds a separate template in `build/desktop/firmware`, runs the
existing firmware verification/archive tools, and packages the GUI with
PyInstaller. It always seeds the template from `examples/timetable.ics`.
The output is `dist/PassportTimetable.exe`; these generated files are ignored.
Use `--firmware-only` or `--package-only` for the corresponding phase.

```sh
python tests/test_desktop.py
dist/PassportTimetable.exe --self-test private/exe-self-test.json
dist/PassportTimetable.exe --esptool version
```

The GUI self-test imports the fictional sample, validates bundled resources
and personalizes an image without opening a serial port. The esptool entry
point is also used by isolated worker processes with redirected output.

## Firmware format

The desktop build defines `PASSPORT_DESKTOP_TEMPLATE`. A 1 MB, flash-resident
array contains a versioned bundle: event records, UTF-8 strings, three indexed
8-bit glyph tables at 14/16/20 px, CRC32 and a calendar SHA-256 identity. The
device checks bounds, counts, intervals, sorting and CRC before using it.
Only event pointers occupy RAM; glyph bitmaps remain in mapped flash.

The EXE locates that unique reserved area inside a verified ESP32-C3 image.
It replaces only that area, recomputes the ESP segment XOR checksum and image
SHA-256, and verifies the result. Executable code, segment sizes and addresses
remain unchanged. The template ELF is archived for debugging; personalized
images have different data and checksums and must not be represented as the
unmodified template binary.

The EXE currently has no Authenticode signature. Windows reputation checks may
appear on other computers. Display rendering, physical keys, USB driver
availability and battery behavior still require device-specific testing.
