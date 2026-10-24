@echo off
rem Build the whole game into one file: dist\WheelsAndBones.exe
rem (ASCII only + CRLF line endings on purpose: cmd misreads UTF-8/LF batch files)
cd /d "%~dp0"

python -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
  echo PyInstaller not found - installing from PyPI ^(pip install pyinstaller^)...
  python -m pip install pyinstaller
  if errorlevel 1 (
    echo.
    echo ERROR: could not install PyInstaller. Check the internet connection and run again.
    pause
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
  pause
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
  pause
  exit /b 1
)
echo.
echo Done: dist\WheelsAndBones.exe
pause
