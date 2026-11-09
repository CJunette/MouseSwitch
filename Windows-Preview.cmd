@echo off
setlocal
pushd "%~dp0"
if errorlevel 1 goto folder_error
if not exist ".venv\Scripts\python.exe" goto environment_missing
if not exist "follow.py" goto environment_missing
".venv\Scripts\python.exe" follow.py watch --target 2 --dry-run
goto end
:environment_missing
echo ERROR: Extract the entire ZIP and run Windows-Setup.cmd successfully first.
:end
popd
pause
exit /b
:folder_error
echo ERROR: Cannot access the program folder. Extract the ZIP to a local folder first.
pause
