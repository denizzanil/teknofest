@echo off
cd /d "%~dp0"
if exist dist\gui.exe (
    start "" "%~dp0dist\gui.exe"
) else (
    echo dist\gui.exe not found. Run build.bat first.
    pause
)
