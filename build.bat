@echo off
rem Build the standalone executable using the project virtual environment.
cd /d "%~dp0"
if not exist ".\.venv\Scripts\python.exe" (
    echo ERROR: virtual environment not found.
    pause
    exit /b 1
)
".\.venv\Scripts\python.exe" -m PyInstaller --noconfirm --onefile --windowed gui.py
if exist dist\gui.exe (
    echo Build complete: dist\gui.exe
) else (
    echo Build failed, check PyInstaller output.
)
pause
