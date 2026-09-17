@echo off
python "%~dp0tools\device_boot.py" --mode courses
if errorlevel 1 goto done
timeout /t 3 /nobreak >nul
python "%~dp0tools\course_usb.py"
:done
pause
