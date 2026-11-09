@echo off
setlocal
pushd "%~dp0"
if errorlevel 1 goto folder_error
if not exist "win_tray.py" goto files_missing
if not exist ".venv\Scripts\python.exe" (
    echo Local Python environment not found. Running first-time setup...
    call "Windows-Setup.cmd"
    if errorlevel 1 goto end
)
if not exist ".venv\Scripts\python.exe" goto environment_missing
".venv\Scripts\python.exe" -c "import pystray, PIL" >nul 2>&1
if errorlevel 1 (
    echo The Windows background interface is not installed yet. Running setup...
    call "Windows-Setup.cmd"
    if errorlevel 1 goto end
)
echo Starting Mouse Follow in the notification area...
start "Mouse Follow" /b ".venv\Scripts\pythonw.exe" win_tray.py
goto end
:files_missing
echo ERROR: win_tray.py is missing. Extract the entire ZIP before running this file.
goto end
:environment_missing
echo ERROR: .venv\Scripts\python.exe is missing. Run Windows-Setup.cmd successfully first.
:end
popd
pause
exit /b
:folder_error
echo ERROR: Cannot access the program folder. Extract the ZIP to a local folder first.
pause
exit /b 1
