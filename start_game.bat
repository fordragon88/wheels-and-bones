@echo off
cd /d "%~dp0"
py game.py %*
if errorlevel 1 pause
