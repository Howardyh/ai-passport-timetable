<p align="right"><a href="README.zh_CN.md">简体中文</a> · <strong>English</strong></p>

# Firmware running on the device

| File | Purpose |
| --- | --- |
| [course_app.c](course_app.c) | Implements the daily timetable, details, tools menu, USB commands, clock and factory-app switching. |
| [timetable.c](timetable.c) | Implements day lookup, lesson timing and calendar calculations independently of the display. |
| [timetable.h](timetable.h) | Declares the course record structure and public timetable interfaces. |
| [desktop_bundle.c](desktop_bundle.c) | Validates the desktop-generated course/font bundle and loads course references. |
| [desktop_bundle.h](desktop_bundle.h) | Defines bundle capacity, maximum lesson count and bundle parsing interfaces. |
| [desktop_font.c](desktop_font.c) | Lets LVGL draw the imported Chinese glyphs directly from mapped flash. |
| [CMakeLists.txt](CMakeLists.txt) | Selects the ordinary source-generated build or the desktop-personalizable template. |

Other `demo_*` and `ui_pixel*` files are upstream hardware examples retained for reference. The timetable starts in `course_app.c`. Generated `timetable_data.c` is local-only and must not be committed.
