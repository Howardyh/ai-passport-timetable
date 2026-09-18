<p align="right"><a href="README.zh_CN.md">简体中文</a> · <strong>English</strong></p>

# Automated checks

| File | Purpose |
| --- | --- |
| [test_desktop.py](test_desktop.py) | Tests desktop bundle encoding, firmware checksums, bounds and refusal of unsafe write sequences without connecting a device. |
| [test_template.py](test_template.py) | Checks CSV conversion, escaping, sample consistency and private-path protection. |
| [test_import_timetable.py](test_import_timetable.py) | Checks ICS timestamps, time-zone conversion, folded text and unsupported recurrence handling. |
| [test_timetable.c](test_timetable.c) | Checks the device-independent date lookup and lesson timing calculations. |
| [test_device_boot.py](test_device_boot.py) | Checks preserved partition ranges and redundant boot-selection records. |

Other tests cover the inherited board and build infrastructure. Run the complete host gate with `./tools/validate.sh --static`. Passing these checks does not prove physical display, button or USB behavior.
