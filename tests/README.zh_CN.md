<p align="right"><strong>简体中文</strong> · <a href="README.md">English</a></p>

# 自动化测试

| 文件 | 作用 |
| --- | --- |
| [test_desktop.py](test_desktop.py) | 验证桌面数据包、镜像校验、容量边界和不兼容设备的拒绝写入逻辑，不连接真实设备。 |
| [test_template.py](test_template.py) | 验证 CSV 转换、特殊字符转义、示例一致性和隐私路径保护。 |
| [test_import_timetable.py](test_import_timetable.py) | 验证 ICS 时间、时区转换、折行文本，以及对不支持的循环规则的处理。 |
| [test_timetable.c](test_timetable.c) | 验证不依赖硬件的按日查课、课程时间和月历计算。 |
| [test_device_boot.py](test_device_boot.py) | 验证原厂分区保护范围和冗余启动选择记录。 |

其他测试覆盖保留的板级逻辑与构建工具。完整主机检查命令为 `./tools/validate.sh --static`。这些检查通过，不代表屏幕显示、物理按键或真实 USB 烧录已经验收。
