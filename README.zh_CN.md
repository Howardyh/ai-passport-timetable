<p align="right"><strong>简体中文</strong> · <a href="README.md">English</a></p>

# AI Passport 个人课程表

[下载 Windows 安装助手（预览版）](https://github.com/Howardyh/ai-passport-timetable/releases/tag/v0.1.0-windows-installer)
· [图形界面使用说明](docs/windows-installer.zh_CN.md)

为 FoloToy AI Passport（ESP32-C3、8 MB）开发的离线课程表，支持每日课程、
课程详情、日期切换、USB 校时与可选 Wi-Fi 校时。分区兼容时保留原厂程序，通过启动切换使用。

基于 [FoloToy/ai-passport](https://github.com/FoloToy/ai-passport)，上游版本
`25add0044cb3e8ce2319c258ae96551f0ffcc2df`。
代码采用 [MIT 协议](LICENSE)，随附 Noto 中文字体采用 [SIL OFL](assets/fonts/OFL.txt)。

## 仓库文件说明

只想安装课程表时，下载页面顶部链接中的 Windows EXE 即可。下面的目录主要供查看源码、修改功能和自行打包使用；点击目录说明可继续查看每个文件的用途。

GitHub 文件列表右侧显示的是该文件或目录的最近一次提交说明，较长的文字会被截断。它不是固定的文件简介；完整用途请看下表和各目录中的 README。

| 目录或文件 | 用途 |
| --- | --- |
| [desktop/](desktop/README.zh_CN.md) | Windows 安装助手：导入与预览个人课表、检测设备、烧录和同步时间。 |
| [main/](main/README.zh_CN.md) | 设备上运行的程序：每日课程、课程详情、日期切换、工具菜单及字库加载。 |
| [components/bsp/](components/bsp/) | AI Passport 硬件驱动与板级接口，供程序调用屏幕、按键等设备能力。 |
| [examples/](examples/README.zh_CN.md) | 可复制的 CSV 和 ICS 课表模板，内容均为虚构示例。 |
| [tools/](tools/README.zh_CN.md) | 从源码转换课表、生成字体、编译、打包 EXE、校验固件及调试设备的工具。 |
| [tests/](tests/README.zh_CN.md) | 自动化测试：课表解析、数据封装、日期计算和安装流程保护。 |
| [assets/](assets/) | 字体、字体许可和应用使用的静态资源。 |
| [docs/](docs/README.zh_CN.md) | 操作说明、硬件资料、开发约定及发布流程。 |
| [.github/](.github/) | GitHub 自动检查流程，以及问题反馈、贡献和安全说明。 |
| [skills/](skills/README.zh_CN.md) | 供 AI 开发助手使用的开发、编译、调试及设备测试工作指南。 |
| [CMakeLists.txt](CMakeLists.txt) / [sdkconfig.defaults](sdkconfig.defaults) | ESP-IDF 工程入口与默认编译配置；普通 EXE 用户无需修改。 |
| [partitions.csv](partitions.csv) | Flash 分区地址与大小，决定原厂区域、启动选择和课程表固件的存放位置。 |
| [dependencies.lock](dependencies.lock) | ESP-IDF 组件版本锁定，帮助开发者复现依赖环境。 |
| [package.json](package.json) / [pnpm-lock.yaml](pnpm-lock.yaml) | 字体转换等开发工具的 Node.js 依赖及锁定版本。 |
| [Sync-Time.cmd](Sync-Time.cmd) / [Configure-WiFi.cmd](Configure-WiFi.cmd) / [Switch-To-Courses.cmd](Switch-To-Courses.cmd) | 源码工作流的 Windows 快捷入口，分别用于 USB 校时、配置 Wi-Fi、切回课表；需要相应 Python 环境。 |
| [AGENTS.md](AGENTS.zh_CN.md) / [CLAUDE.md](CLAUDE.zh_CN.md) | 给 AI 编程助手看的项目规则与文档入口。 |
| [.gitignore](.gitignore) / [.gitattributes](.gitattributes) | Git 忽略规则与文本处理约定，避免个人课表和构建产物误入源码仓库。 |
| [LICENSE](LICENSE) | 本项目代码的 MIT 开源许可；字体许可单独列在字体目录。 |

## 在本地转换课表

Windows 图形界面版见[安装助手说明](docs/windows-installer.zh_CN.md)：
选择课表、预览、一键烧录，使用者无需安装开发环境。

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
