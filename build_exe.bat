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

echo.
echo Building WheelsAndBones.exe ^(1-3 minutes^)...
python -m PyInstaller --noconfirm --clean --onefile --windowed ^
  --name WheelsAndBones --icon assets\icon.ico ^
  --add-data "assets;assets" ^
  --exclude-module tkinter ^
  --hidden-import moderngl --hidden-import glcontext --hidden-import glcontext.wgl --hidden-import glcontext.empty ^
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
