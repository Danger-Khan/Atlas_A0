@echo off
rem Author: Imaad Ullah Khan Yameen
rem Email: yameenimaad@gmail.com
rem This code is not for sale.
rem Builds dist\AtlasA0\AtlasA0.exe and (if Inno Setup is installed) Output\AtlasA0-Setup-<version>.exe
rem Run from anywhere:  installer\build_windows.bat      Needs: Windows, Python 3.10-3.12 on PATH, internet for pip.
setlocal
cd /d "%~dp0\.."

if not exist .build-venv (
  python -m venv .build-venv || goto :fail
)
call .build-venv\Scripts\activate.bat || goto :fail
python -m pip install --upgrade pip || goto :fail
python -m pip install -r requirements.txt -r installer\requirements-build.txt -r requirements-dev.txt || goto :fail

echo.
echo === 1/3 tests ===
python -m pytest -q || goto :fail

echo.
echo === 2/3 AtlasA0.exe (PyInstaller) ===
pyinstaller installer\atlasa0.spec --noconfirm --clean || goto :fail

for /f %%v in ('python -c "from atlasa0 import __version__; print(__version__)"') do set VERSION=%%v

echo.
echo === 3/3 Setup.exe (Inno Setup) ===
set ISCC=
where iscc >nul 2>nul && set ISCC=iscc
if not defined ISCC if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe
if not defined ISCC if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe
if not defined ISCC (
  echo Inno Setup 6 not found - skipping Setup.exe. Install it from https://jrsoftware.org/isdl.php and run again.
  echo The program folder is ready:  dist\AtlasA0\AtlasA0.exe
  goto :done
)
"%ISCC%" /DMyAppVersion=%VERSION% installer\atlasa0.iss || goto :fail
echo Installer: Output\AtlasA0-Setup-%VERSION%.exe

:done
echo.
echo Next: open dist\AtlasA0\AtlasA0.exe once and make a small map before you share anything.
exit /b 0

:fail
echo.
echo BUILD FAILED - see the messages above.
exit /b 1
