@echo off
REM Always operate from the folder this .bat file actually lives in
cd /d "%~dp0"

echo ============================================
echo   Building Glowva ERP.exe
echo ============================================
echo   Running from: %cd%
echo.

if not exist main.py (
    echo ERROR: main.py not found in this folder.
    echo Run this script from the SAME folder as main.py.
    pause
    exit /b 1
)

echo.
echo Installing dependencies...
echo.

py -m pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo ============================================
    echo   ERROR installing requirements
    echo ============================================
    echo.
    echo Please check requirements.txt
    echo.
    pause
    exit /b 1
)

echo.
echo Installing PyInstaller...
echo.

py -m pip install pyinstaller

if errorlevel 1 (
    echo.
    echo ============================================
    echo   ERROR installing PyInstaller
    echo ============================================
    pause
    exit /b 1
)

echo.
echo Checking PyInstaller...
echo.

py -m PyInstaller --version

if errorlevel 1 (
    echo.
    echo ============================================
    echo   ERROR: PyInstaller is not available
    echo ============================================
    pause
    exit /b 1
)

echo.
echo Building the .exe file - this takes a minute or two...
echo.

py -m PyInstaller --onefile --windowed --name GlowvaERP --collect-all customtkinter --clean --distpath dist main.py

if not exist dist\GlowvaERP.exe (
    echo.
    echo ============================================
    echo   Something went wrong - GlowvaERP.exe was NOT created.
    echo   Scroll up to see the actual error from PyInstaller.
    echo ============================================
    pause
    exit /b 1
)

echo.
echo ============================================
echo   Done!
echo   Find GlowvaERP.exe inside the "dist" folder
echo ============================================
pause