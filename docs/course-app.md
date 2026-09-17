<p align="right"><a href="course-app.zh_CN.md">简体中文</a> · <strong>English</strong></p>

# Personal course timetable

This application starts directly in a redesigned daily timetable, using the
official BSP from upstream commit `25add0044cb3e8ce2319c258ae96551f0ffcc2df`.
It imports explicit ICS events, converts UTC to Shanghai time and keeps names,
rooms and descriptions offline. It does not infer holidays or modify the source
calendar. Unsupported recurrence rules fail import instead of losing events.

## Controls

- Up/down: select a lesson. OK: show details or return.
- Hold up/down: previous/next day. Hold OK: tools menu or return.
- Tools: today, previous/next day, manual date/time, optional network time,
  brightness, screen off, help and original factory application.
- Display dims after 20 seconds and turns off after 45 seconds. A key wakes it
  without activating the key action. CPU remains awake; battery life is unmeasured.

Run `Sync-Time.cmd` after a complete power-off, or set date/time using the tools
menu. A saved timestamp is only a browsing hint and is explicitly marked
unverified at every boot. `Configure-WiFi.cmd` optionally stores a 2.4 GHz network
for SNTP time synchronization on subsequent boots. No cloud account is required.
Passwords are prompted locally and never logged. Network attempts are bounded.

## Preserve the original application

This layout was checked against the connected 8 MB device. Original partitions
remain at their original offsets, including the factory application from
`0x10000` to `0x310000` and all following image/card/audio data through `0x4fa000`.
New OTA metadata occupies `0x4fa000..0x4fc000`; courses occupy the 3 MB OTA slot
at `0x500000`. CMake redirects the course image in all flash descriptors.

`tools/device_boot.py --port COMx --install --build build/verified` verifies the
current/new layout and the firmware, then writes only the bootloader, partition
table, new course program and OTA selection. It refuses overlaps with preserved
partitions. **Never flash the merged full image to a device whose original
program/data should remain:** padding would erase the preserved regions.
The merged image is a validation artifact only for this project.

Choose original factory functions in the tools menu and confirm on the device.
To return to courses, connect USB and run `Switch-To-Courses.cmd`; it changes
only OTA selection and then synchronizes time. The original program is retained
as a separate application, not reimplemented or merged into the course UI.
Do not install a different partition layout through a community flasher if you
want to retain this arrangement.

## Rebuild and test

Use ESP-IDF 5.5.3. Import ICS with `python tools/import_timetable.py path.ics`,
then regenerate fonts with `tools/make_course_fonts.py --node NODE --converter
LV_FONT_CONV_JS`. On native Windows, `tools/build-course.ps1` executes the same
isolated build, merge, verification and artifact archive as the firmware gate.
The POSIX gate is `tools/validate.sh`; native Windows may fail its symlink tests
without OS permissions. Never report those failures as passing tests.

Personal files live under ignored `private/`, `main/timetable_data.c` and font
subsets. Do not upload binaries, screenshots, raw logs or device headers:
they may contain personal data. Only fictional examples are included in the public repository.

Device acceptance includes real glyph coverage, day/detail/menu navigation,
clock setup, empty days, sleep/wake display behavior, optional Wi-Fi and factory
switching. `tools/capture_course.py` captures actual LVGL output via USB for
layout review, but does not prove panel color or physical button operation.
