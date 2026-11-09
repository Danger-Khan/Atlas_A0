@echo off
rem Author: Imaad Ullah Khan Yameen
rem Email: yameenimaad@gmail.com
rem This code is not for sale.
rem Windows launcher: creates a private virtualenv on first run, then opens the AtlasA0 window.
cd /d "%~dp0"
if not exist .venv (
  py -3 -m venv .venv || goto :err
  .venv\Scripts\python -m pip install --upgrade pip
  .venv\Scripts\python -m pip install -r requirements.txt || goto :err
)
.venv\Scripts\python run_gui.py %*
exit /b 0
:err
echo Setup failed. Install Python 3.10+ from python.org and try again.
pause
