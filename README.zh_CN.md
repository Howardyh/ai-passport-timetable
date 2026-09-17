<p align="right"><strong>简体中文</strong> · <a href="README.md">English</a></p>

# AI Passport 个人课程表

为 FoloToy AI Passport（ESP32-C3、8 MB）开发的离线课程表，支持每日课程、
课程详情、日期切换、USB 校时与可选 Wi-Fi 校时。分区兼容时保留原厂程序，通过启动切换使用。

基于 [FoloToy/ai-passport](https://github.com/FoloToy/ai-passport)，上游版本
`25add0044cb3e8ce2319c258ae96551f0ffcc2df`。
代码采用 [MIT 协议](LICENSE)，随附 Noto 中文字体采用 [SIL OFL](assets/fonts/OFL.txt)。

## 在本地转换课表

需要 Python 3.10+、Node.js 20+、pnpm 10，编译需要 **ESP-IDF 5.5.3**。
没有 pnpm 时执行 `npm install --global pnpm@10.17.1`。

```sh
pnpm install --frozen-lockfile --ignore-scripts
python tools/prepare_timetable.py examples/timetable.ics
```

示例全部是虚构数据。自己的课表放入 `private/`，然后执行其中一个命令：

```sh
python tools/prepare_timetable.py private/my-calendar.ics
python tools/prepare_timetable.py private/my-calendar.csv
```

没有 ICS 时，将 [CSV 模板](examples/timetable.csv) **复制到 private/ 后再编辑**，
用表格软件填写并保存为 **UTF-8 CSV**：

| 字段 | 内容 | 示例 |
| --- | --- | --- |
| date | 日期 YYYY-MM-DD | 2027-03-01 |
| start | 开始时间 HH:MM | 08:00 |
| end | 结束时间 HH:MM | 09:30 |
| name | 课程名称 | 示例课程甲 |
| location | 地点，可留空 | 示例楼 101 |
| description | 教师或备注，可留空 | 示例老师 |

时间统一为北京时间 UTC+8。每次课单独一行，包括调课、补课。
工具不会自动推算教学周、节假日或重复课程。

只转换 CSV 为 ICS、不生成字库时：

```sh
python tools/csv_to_ics.py private/my-calendar.csv --output private/my-calendar.ics
```

ICS 支持明确列出每次课的事件，以及 UTC 或上海本地时间。
含 `RRULE`、`RDATE`、`EXDATE`、`RECURRENCE-ID` 的循环事件、全天或跨天课程会明确报错，
不会静默漏课。请先把循环课表展开为每次课一个事件。

## 编译与安装

生成课表与字库后，激活 ESP-IDF 5.5.3 环境：

```sh
./tools/validate.sh --static
./tools/validate.sh --firmware
```

原生 Windows 在 ESP-IDF 终端执行
`powershell -ExecutionPolicy Bypass -File tools/build-course.ps1`，验证后文件位于 `build/verified`。
POSIX 固件检查将验证后的文件归档到 `build/firmware/<sha256>/`。

**保留原厂程序和数据时，不能整包烧录合并后的 full.bin**，其中的填充会覆盖原厂区域。
使用带分区检查的分段安装工具，`--build` 指向验证后的构建或归档目录：

```sh
python tools/device_boot.py --port COMx --install --build build/verified
python tools/course_usb.py --port COMx
```

把 `COMx` 换成实际串口，只有一台设备时可省略 `--port`。
活动 Python 环境缺少依赖时安装 `pyserial` 和 `esptool>=4.12,<5`。
分区不兼容时会拒绝安装。安装前阅读[使用说明](docs/course-app.zh_CN.md)。

## 操作方法

- 上下键选择课程，确定键进入或退出详情。
- 长按上下键切换日期，长按确定键打开工具菜单。
- 工具菜单包含校时、亮度、回到今天和原厂应用切换。
- 完全断电后，用 `python tools/course_usb.py` 同步电脑时间。
- `python tools/course_usb.py --wifi` 可选配网，用于网络校时。
- 返回课表：`python tools/device_boot.py --mode courses`。

## 隐私与开源

个人输入放在 `private/`，不要把真实数据写入受 Git 跟踪的示例。
生成的课程数据、字体子集、构建产物、日志及示例以外的 ICS 均已忽略。
固件和截图也可能包含课程信息，不能上传个人构建或设备截图。

推送前执行 `python tools/check_public_files.py`。CI 同样检查，即使用 `git add -f`
强制加入受限路径也会报错。它只检查路径，无法识别任意文件中的隐私文字，
仍须审阅 `git diff --cached`。CI 只编译虚构示例，不发布固件和调试产物。

上游工程文档保留供参考；本项目的课表导入、分区、安装方式以本 README 和使用说明为准。
可选 Wi-Fi、长期续航与各项原厂功能需要分别在设备上验证。
