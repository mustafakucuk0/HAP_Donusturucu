@echo off
rem HAP Donusturucu - Windows baslatici. Cift tiklayin; tarayicida arayuz acilir.
rem Yazar: Mustafa Kucuk - MIT Lisansi
chcp 65001 >nul
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
  py -3 hapq_server.py
  goto son
)
python -c "import sys" >nul 2>nul
if %errorlevel%==0 (
  python hapq_server.py
  goto son
)
where uv >nul 2>nul
if %errorlevel%==0 (
  uv run --no-project python hapq_server.py
  goto son
)
echo Python bulunamadi.
echo https://www.python.org/downloads/ adresinden kurun (kurulumda "Add python.exe to PATH" kutusunu isaretleyin)
echo ya da PowerShell'de:  winget install Python.Python.3.12
:son
pause
