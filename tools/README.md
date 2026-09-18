<p align="right"><a href="README.zh_CN.md">简体中文</a> · <strong>English</strong></p>

# Conversion, build and device utilities

| File | Purpose |
| --- | --- |
| [prepare_timetable.py](prepare_timetable.py) | Imports an ICS/CSV calendar and generates course data and font subsets for a source build. |
| [csv_to_ics.py](csv_to_ics.py) | Converts each CSV lesson row into an explicit ICS calendar event locally. |
| [import_timetable.py](import_timetable.py) | Parses explicit ICS events, converts time zones and generates local course source data. |
| [make_course_fonts.py](make_course_fonts.py) | Generates font subsets for the ordinary ESP-IDF source-build workflow. |
| [build_desktop.py](build_desktop.py) | Builds and verifies a fictional firmware template, then packages the standalone Windows EXE. |
| [build-course.ps1](build-course.ps1) | Builds and archives the ordinary course firmware in an activated Windows ESP-IDF environment. |
| [device_boot.py](device_boot.py) | Checks partition compatibility and installs segmented firmware or switches the boot target. |
| [course_usb.py](course_usb.py) | Synchronizes device time, queries status and optionally configures Wi-Fi for time synchronization. |
| [capture_course.py](capture_course.py) | Captures the device display over USB for local layout inspection. |
| [validate.sh](validate.sh) | Runs repository checks, host tests and/or firmware verification. |
| [check_public_files.py](check_public_files.py) | Rejects private calendars and generated firmware accidentally added to Git. |
| [verify_firmware.py](verify_firmware.py) | Checks image contents, configured write offsets, partition bounds and image sizes. |
| [archive_firmware.py](archive_firmware.py) | Archives matching firmware/debugging files and verifies their recorded hashes. |

Other scripts provide upstream repository validation and development-environment support. Normal EXE users do not need to run these commands. Never flash a merged image when you need to preserve factory partitions.
