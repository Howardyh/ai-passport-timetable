<p align="right"><a href="README.zh_CN.md">简体中文</a> · <strong>English</strong></p>

# AI Passport Timetable

[Download the Windows installer (preview)](https://github.com/Howardyh/ai-passport-timetable/releases/tag/v0.1.0-windows-installer)
· [Windows guide](docs/windows-installer.md)

An offline daily timetable for FoloToy AI Passport (ESP32-C3, 8 MB). Browse
lessons and details, change dates, set the clock over USB, or optionally use
Wi-Fi time synchronization. Compatible factory firmware remains available
through a separate boot option.

Based on [FoloToy/ai-passport](https://github.com/FoloToy/ai-passport), commit
`25add0044cb3e8ce2319c258ae96551f0ffcc2df`. Code uses the [MIT license](LICENSE);
the bundled Noto CJK font uses [SIL OFL](assets/fonts/OFL.txt).

## Repository map

To install a timetable, download the Windows EXE linked above. The directories below are for reading the source, modifying features and building your own package. Each linked directory guide explains its individual files.

GitHub's file list shows the most recent commit message for each file or directory and truncates long messages. That column is not a permanent file description; use this table and the directory READMEs for complete explanations.

| Directory or file | Purpose |
| --- | --- |
| [desktop/](desktop/README.md) | Windows installer: calendar import and preview, device detection, flashing and clock synchronization. |
| [main/](main/README.md) | Device application: daily lessons, lesson details, date navigation, tools and font loading. |
| [components/bsp/](components/bsp/) | AI Passport drivers and board interfaces for the display, buttons and other hardware. |
| [examples/](examples/README.md) | Reusable CSV and ICS templates containing fictional lessons only. |
| [tools/](tools/README.md) | Source-workflow utilities for calendar conversion, fonts, compilation, EXE packaging, image checks and device debugging. |
| [tests/](tests/README.md) | Automated checks for calendar parsing, data bundles, date calculations and installation safeguards. |
| [assets/](assets/) | Fonts, font licenses and static application resources. |
| [docs/](docs/README.md) | User instructions, hardware references, development conventions and release procedures. |
| [.github/](.github/) | GitHub automated checks, issue templates, contribution and security information. |
| [skills/](skills/README.md) | Development, build, debugging and device-test guidance for AI coding assistants. |
| [CMakeLists.txt](CMakeLists.txt) / [sdkconfig.defaults](sdkconfig.defaults) | ESP-IDF project entry point and default build settings; EXE users do not need to edit these. |
| [partitions.csv](partitions.csv) | Flash addresses and sizes for factory regions, boot selection and the timetable application. |
| [dependencies.lock](dependencies.lock) | Locked ESP-IDF component versions for reproducible dependencies. |
| [package.json](package.json) / [pnpm-lock.yaml](pnpm-lock.yaml) | Node.js development dependencies, including font conversion tools, and their locked versions. |
| [Sync-Time.cmd](Sync-Time.cmd) / [Configure-WiFi.cmd](Configure-WiFi.cmd) / [Switch-To-Courses.cmd](Switch-To-Courses.cmd) | Windows shortcuts for the source workflow: USB clock sync, Wi-Fi configuration and timetable boot selection; require the corresponding Python environment. |
| [AGENTS.md](AGENTS.md) / [CLAUDE.md](CLAUDE.md) | Project rules and documentation entry points for AI coding assistants. |
| [.gitignore](.gitignore) / [.gitattributes](.gitattributes) | Git exclusion and text handling rules that help keep personal calendars and generated files out of the source repository. |
| [LICENSE](LICENSE) | MIT license for project code; fonts have their own license in the font directory. |

## Local conversion

For the standalone Windows GUI, see the [Windows installer guide](docs/windows-installer.md).
It imports, previews and flashes calendars locally without an end-user development environment.

Requires Python 3.10+, Node.js 20+, pnpm 10 and **ESP-IDF 5.5.3** to compile.
Install pnpm if needed with `npm install --global pnpm@10.17.1`.

```sh
pnpm install --frozen-lockfile --ignore-scripts
python tools/prepare_timetable.py examples/timetable.ics
```

All examples are fictional. Place your own files in `private/`, then use either:

```sh
python tools/prepare_timetable.py private/my-calendar.ics
python tools/prepare_timetable.py private/my-calendar.csv
```

Copy [the CSV template](examples/timetable.csv) into `private/` before editing
it. Save as UTF-8 CSV. Columns are `date,start,end,name,location,description`;
date uses `YYYY-MM-DD`, times use `HH:MM` in China Standard Time (UTC+8).
Each row is one actual lesson. List all occurrences and make-up lessons;
the converter does not infer holidays or weekly recurrence.

For CSV to ICS conversion without font generation:

```sh
python tools/csv_to_ics.py private/my-calendar.csv --output private/my-calendar.ics
```

ICS accepts explicit timed events, UTC and Shanghai-local timestamps.
Recurrence (`RRULE`, `RDATE`, `EXDATE`, `RECURRENCE-ID`), all-day and overnight
events are rejected rather than silently omitted. Expand recurring calendars first.

## Build and installation

Prepare the calendar above, then activate ESP-IDF 5.5.3:

```sh
./tools/validate.sh --static
./tools/validate.sh --firmware
```

Native Windows: run `powershell -ExecutionPolicy Bypass -File tools/build-course.ps1`
in an ESP-IDF terminal; verified files are in `build/verified`. The POSIX firmware
gate archives its verified files in `build/firmware/<sha256>/`.

**Do not flash the merged full image when preserving factory firmware/data.**
Its padding overlaps those regions. Use the guarded segmented installer, with
`--build` pointing to the verified build or archive:

```sh
python tools/device_boot.py --port COMx --install --build build/verified
python tools/course_usb.py --port COMx
```

Replace `COMx` with the actual port, or omit `--port` to detect one device.
Install `pyserial` and `esptool>=4.12,<5` in your active Python environment if
missing. Incompatible partition layouts are refused. Read the
[application guide](docs/course-app.md) before installing.

## Controls

- Up/down selects a lesson; OK opens/closes details.
- Hold up/down to change date; hold OK for tools.
- Tools include clock setting, brightness, today and the factory application.
- After complete power-off: `python tools/course_usb.py` synchronizes time.
- `python tools/course_usb.py --wifi` optionally configures network time.
- `python tools/device_boot.py --mode courses` returns from the factory app.

## Privacy

Keep real input under `private/`; never replace tracked examples with personal
data. Generated course data, font subsets, build outputs, logs and other ICS
files are ignored. Firmware and screenshots can expose your timetable, too.

Run `python tools/check_public_files.py` before pushing. CI also rejects
forbidden paths, including force-added files. This is a path guard, not a
general secret detector: review `git diff --cached` as well. CI builds only the
fictional sample and does not publish firmware or debugging artifacts.

Upstream engineering documents are retained as reference. This README and the
application guide define this derivative's import, partition and installation
workflow. Optional Wi-Fi, battery endurance and individual factory features
require separate device validation.
