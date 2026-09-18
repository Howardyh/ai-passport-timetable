<p align="right"><strong>简体中文</strong> · <a href="windows-installer.md">English</a></p>

# Windows 课程表安装助手

`PassportTimetable.exe` 是 Windows x64 单文件程序，用户无需安装 Python、Node.js
或 ESP-IDF，也不需要联网。程序内置固件模板、字体、转换工具和串口烧录工具。

## 使用方法

1. 打开 EXE，选择 ICS 或 UTF-8 CSV 课表，检查预览中的日期、时间、课程和地点。
   点击课程行可查看完整备注。
2. 用 USB 数据线连接 AI Passport 并保持开机，选择对应串口；没有出现时点击“刷新设备”。
3. 点击“一键安装课程表”，等待完成。程序依次在本地生成课表和字库，检查 ESP32-C3、
   8 MB Flash、安全设置和分区，烧录并校验，启动课程表，核对课表指纹并同步电脑时间。

不连接设备也能加载虚构示例、保存 CSV 模板和预览个人课表。
CSV 每行填写一次课；循环 ICS 需先展开。当前最多支持 1024 次课程，课表与字库共用
1 MB 空间。文字不受支持或数据过大时，会在写入设备前报错。时区为北京时间 UTC+8。

“仅同步时间”也兼容旧版课程表。完全断电后时钟会标为未校准，重新连接电脑校时即可。

## 安装会改变什么

分区布局与现有课程表程序保持一致。兼容设备上的原厂程序、图片、身份卡和音频分区
保持原位。原厂功能仍是独立应用，可通过设备工具菜单切换，并非合并进课程表界面。
启用安全启动、Flash 加密或分区不兼容的设备会被拒绝。

仅写入引导程序、分区表、课程表区域和启动选择信息，不整片擦除，也不整包烧录 full.bin。
写入过程中断电可能导致安装中断；重新连接后再次运行安装即可。
若写入已经完成但启动确认失败，会明确提示；可以重启设备，再点击“仅同步时间”检查。

课表、预览和生成的固件都只在本机处理，临时个人固件在操作正常退出时删除。
EXE 仅内置虚构示例。不要公开个人固件、设备截图或日志。
程序没有遥测、云端转换、自动上传或自动更新固件功能。

## 从源码构建

使用激活后的 ESP-IDF 5.5.3 Windows 环境、Python 3.12（含 Tcl/Tk）：

```sh
python -m pip install -r desktop/requirements.txt
python tools/build_desktop.py
```

脚本在 `build/desktop/firmware` 单独构建模板，执行现有固件校验与归档，再用 PyInstaller
打包界面。模板始终从 `examples/timetable.ics` 的虚构课表生成。
输出为 `dist/PassportTimetable.exe`，所有生成文件均被 Git 忽略。
`--firmware-only` 只构建模板，`--package-only` 只执行 EXE 打包。

```sh
python tests/test_desktop.py
dist/PassportTimetable.exe --self-test private/exe-self-test.json
dist/PassportTimetable.exe --esptool version
```

界面自检导入虚构课表、验证资源并生成固件，不打开串口。
烧录工具通过独立子进程运行，输出重定向到界面日志。

## 固件格式

桌面版构建定义 `PASSPORT_DESKTOP_TEMPLATE`，在 Flash 中预留 1 MB 数组，存放带版本的
课程记录、UTF-8 文本、14/16/20 像素三套 8 位灰度字库、CRC32 与课表 SHA-256 指纹。
设备使用前检查边界、数量、时间区间、排序和 CRC。仅课程指针表占用 RAM，字形位图留在 Flash。

EXE 在校验过的 ESP32-C3 镜像中定位唯一预留区，仅替换其中的数据，重新计算 ESP 段异或校验和
镜像 SHA-256，再次验证。可执行代码、段大小和地址保持不变。
模板 ELF 单独归档用于调试；个人固件的数据与校验值不同，不能将它当作未经修改的模板二进制。

当前 EXE 未做 Authenticode 代码签名，其他电脑可能出现 Windows 信誉检查提示。
中文实际显示、物理按键、USB 驱动可用性和续航仍需针对设备进行验证。
