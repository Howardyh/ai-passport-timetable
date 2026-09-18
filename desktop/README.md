<p align="right"><a href="README.zh_CN.md">简体中文</a> · <strong>English</strong></p>

# Windows graphical installer

| File | Purpose |
| --- | --- |
| [app.py](app.py) | Builds the window, imports calendars for preview, lists serial ports and displays installation progress. |
| [backend.py](backend.py) | Coordinates local conversion, resource verification, device checks, segmented flashing and startup confirmation. |
| [payload.py](payload.py) | Encodes course records and Chinese glyphs, personalizes the reserved firmware area and updates image checksums. |
| [requirements.txt](requirements.txt) | Pins the Python dependencies used to build the Windows executable. |

End users should download the EXE from [Releases](https://github.com/Howardyh/ai-passport-timetable/releases). See the [Windows guide](../docs/windows-installer.md) for usage and compatibility.
