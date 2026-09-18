<p align="right"><strong>简体中文</strong> · <a href="README.md">English</a></p>

# 转换、构建与设备工具

| 文件 | 作用 |
| --- | --- |
| [prepare_timetable.py](prepare_timetable.py) | 传统源码构建入口：读取 ICS/CSV，生成课程数据和所需的中文字体子集。 |
| [csv_to_ics.py](csv_to_ics.py) | 把 CSV 每一行转换成一次明确的 ICS 课程事件，全程在本地处理。 |
| [import_timetable.py](import_timetable.py) | 解析 ICS、转换为北京时间，并生成本地课程数据；遇到不支持的循环规则会报错。 |
| [make_course_fonts.py](make_course_fonts.py) | 为传统 ESP-IDF 源码构建生成字体子集；Windows EXE 使用自己的离线字库生成方式。 |
| [build_desktop.py](build_desktop.py) | 构建并校验虚构课表固件模板，再把界面、字体与烧录工具封装为 Windows EXE。 |
| [build-course.ps1](build-course.ps1) | 在已激活的 Windows ESP-IDF 环境中构建、校验和归档传统课程表固件。 |
| [device_boot.py](device_boot.py) | 检查分区兼容性，分段安装固件，或在课表与原厂应用之间切换启动目标。 |
| [course_usb.py](course_usb.py) | 通过 USB 同步时间、读取状态；也可选配 Wi-Fi 用于网络校时。 |
| [capture_course.py](capture_course.py) | 通过 USB 获取设备画面，用于本地排版检查；截图可能含个人课表，不应公开上传。 |
| [validate.sh](validate.sh) | 统一检查入口：运行仓库规范检查、主机测试或固件构建校验。 |
| [check_public_files.py](check_public_files.py) | 检查 Git 跟踪文件，拦截误加入仓库的个人课表、生成固件和其他受限文件。 |
| [verify_firmware.py](verify_firmware.py) | 检查固件内容、写入偏移、分区边界和镜像大小。 |
| [archive_firmware.py](archive_firmware.py) | 归档相互匹配的固件与调试文件，并校验文件哈希，方便追溯具体构建。 |

其他脚本负责上游仓库检查和开发环境辅助。使用 EXE 的普通用户不需要运行这些命令。需要保留原厂分区时，不要整包烧录合并镜像。
