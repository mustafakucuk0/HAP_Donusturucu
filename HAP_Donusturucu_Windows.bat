@echo off
rem HAP Donusturucu - Windows baslatici. Cift tiklayin; tarayicida arayuz acilir.
rem Yazar: Mustafa Kucuk - MIT Lisansi
chcp 65001 >nul
cd /d "%~dp0"

rem Once uv: Python yoksa ilk acilista kendisi indirir.
set "UV="
where uv >nul 2>nul && set "UV=uv"
if not defined UV if exist "%USERPROFILE%\.local\bin\uv.exe" set "UV=%USERPROFILE%\.local\bin\uv.exe"
if not defined UV if exist "%LOCALAPPDATA%\Microsoft\WinGet\Links\uv.exe" set "UV=%LOCALAPPDATA%\Microsoft\WinGet\Links\uv.exe"
if defined UV (
  "%UV%" run --no-project --python 3.12 hapq_server.py
  goto son
)

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

echo Python bulunamadi. En kolayi uv kurmak; PowerShell'de sunu calistirin:
echo   winget install --id=astral-sh.uv -e
echo ya da:
echo   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
echo Sonra bu dosyaya yeniden cift tiklayin.
:son
pause
