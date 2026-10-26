@echo off
rem Build the whole game into one file: dist\WheelsAndBones.exe
rem (ASCII only + CRLF line endings on purpose: cmd misreads UTF-8/LF batch files)
rem Double-click in Explorer: the window waits at the end (pause). From a terminal or a script
rem (cmd /c build_exe.bat, Claude, CI): no pause. Force either way: set WNB_PAUSE=1 or set WNB_NOPAUSE=1.
cd /d "%~dp0"
rem Explorer starts a batch file as: cmd /c ""<path>"" - so a doubled quote in %cmdcmdline% means double-click.
setlocal enabledelayedexpansion
set "c=!cmdcmdline!"
set "c2=!c:""=!"
set "dbl="
if not "!c!"=="!c2!" set "dbl=1"
endlocal & set "WNB_DBL=%dbl%"
if not defined WNB_PAUSE if defined WNB_DBL set WNB_PAUSE=1
if defined WNB_NOPAUSE set WNB_PAUSE=

python -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
  echo PyInstaller not found - installing from PyPI ^(pip install pyinstaller^)...
  python -m pip install pyinstaller
  if errorlevel 1 (
    echo.
    echo ERROR: could not install PyInstaller. Check the internet connection and run again.
    if defined WNB_PAUSE pause
    exit /b 1
  )
)

rem speech for blind players: Tolk (NVDA/JAWS) + Windows voices (pywin32)
python -m pip install --quiet cytolk pywin32

echo.
echo Preparing assets for the exe (without full 3D models and seat bodies)...
python exe_assets.py
if errorlevel 1 (
  echo.
  echo ERROR: exe_assets.py failed.
  if defined WNB_PAUSE pause
  exit /b 1
)

echo.
echo Building WheelsAndBones.exe ^(1-3 minutes^)...
python -m PyInstaller --noconfirm --clean --onefile --windowed ^
  --name WheelsAndBones --icon assets\icon.ico ^
  --add-data "build\exe_assets;assets" ^
  --exclude-module tkinter ^
  --hidden-import moderngl --hidden-import glcontext --hidden-import glcontext.wgl --hidden-import glcontext.empty ^
  --collect-all cytolk --hidden-import win32com.client --hidden-import pythoncom --hidden-import pywintypes ^
  game.py
if errorlevel 1 (
  echo.
  echo BUILD ERROR - see the messages above.
  if defined WNB_PAUSE pause
  exit /b 1
)
echo.
echo Done: dist\WheelsAndBones.exe
if defined WNB_PAUSE pause
