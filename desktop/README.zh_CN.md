<p align="right"><strong>简体中文</strong> · <a href="README.md">English</a></p>

# Windows 图形安装助手

| 文件 | 作用 |
| --- | --- |
| [app.py](app.py) | 界面入口：选择并预览课表、显示串口、开始安装、同步时间，并展示进度和错误。 |
| [backend.py](backend.py) | 安装流程：校验内置资源、检查芯片和分区、分段烧录、验证写入内容，并确认课表启动和校时。 |
| [payload.py](payload.py) | 数据转换：把课程文字与中文字形编码到固件预留区，重新计算镜像校验值；不需要用户安装编译环境。 |
| [requirements.txt](requirements.txt) | 开发依赖及版本：仅从源码打包 EXE 的开发者需要安装，普通用户不需要。 |

普通用户直接从 [Releases](https://github.com/Howardyh/ai-passport-timetable/releases) 下载 EXE，无需逐个运行这些源码文件。操作步骤和设备兼容条件见[安装助手说明](../docs/windows-installer.zh_CN.md)。
