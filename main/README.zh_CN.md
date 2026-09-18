<p align="right"><strong>简体中文</strong> · <a href="README.md">English</a></p>

# 设备端课程表固件

| 文件 | 作用 |
| --- | --- |
| [course_app.c](course_app.c) | 设备程序入口：每日课表、课程详情、工具菜单、USB 指令、校时，以及切换原厂应用。 |
| [timetable.c](timetable.c) | 课程计算逻辑：按日期查课、判断课程是否开始或结束、处理北京时间和月历。 |
| [timetable.h](timetable.h) | 定义课程记录结构，以及界面与课程计算模块共用的接口。 |
| [desktop_bundle.c](desktop_bundle.c) | 读取 EXE 生成的数据包，检查数量、边界、排序与 CRC，防止无效数据进入界面。 |
| [desktop_bundle.h](desktop_bundle.h) | 定义数据区容量、课程数量上限和数据包读取接口。 |
| [desktop_font.c](desktop_font.c) | 把随课表生成的中文字形提供给 LVGL，字形保存在 Flash 中，减少 RAM 占用。 |
| [CMakeLists.txt](CMakeLists.txt) | 构建配置：选择传统的源码生成课表，或适合 Windows EXE 个性化处理的通用固件模板。 |

其余 `demo_*` 和 `ui_pixel*` 文件是保留的上游硬件示例，便于开发参考；课程表实际从 `course_app.c` 启动。生成的 `timetable_data.c` 含个人课程数据，只保存在本地，不提交到仓库。
