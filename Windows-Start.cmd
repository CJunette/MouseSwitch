@echo off
setlocal
pushd "%~dp0"
if errorlevel 1 goto folder_error
if not exist "follow.py" goto files_missing
if not exist ".venv\Scripts\python.exe" (
    echo Local Python environment not found. Running first-time setup...
    call "Windows-Setup.cmd"
    if errorlevel 1 goto end
)
if not exist ".venv\Scripts\python.exe" goto environment_missing
echo Waiting for keyboard and mouse on Windows channel 1. Keep this window open.
echo Wait for Armed before pressing Fn+2. Ctrl+C stops the watcher.
".venv\Scripts\python.exe" follow.py watch --target 2
goto end
:files_missing
echo ERROR: follow.py is missing. Extract the entire ZIP before running this file.
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
