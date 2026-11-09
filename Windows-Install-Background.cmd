@echo off
setlocal
pushd "%~dp0"
if errorlevel 1 goto folder_error
if not exist ".venv\Scripts\python.exe" (
    echo Local Python environment not found. Running first-time setup...
    call "Windows-Setup.cmd"
    if errorlevel 1 goto end
)
".venv\Scripts\python.exe" -c "import pystray, PIL" >nul 2>&1
if errorlevel 1 (
    call "Windows-Setup.cmd"
    if errorlevel 1 goto end
)
".venv\Scripts\python.exe" install_windows.py --install
if errorlevel 1 goto end
start "Mouse Follow" /b ".venv\Scripts\pythonw.exe" win_tray.py
echo Background startup is enabled. Look for Mouse Follow in the notification area.
:end
popd
pause
exit /b
:folder_error
echo ERROR: Cannot access the program folder.
pause
exit /b 1
