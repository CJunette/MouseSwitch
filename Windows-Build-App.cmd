@echo off
setlocal
pushd "%~dp0"
if errorlevel 1 goto folder_error
if not exist ".venv\Scripts\python.exe" (
    call "Windows-Setup.cmd"
    if errorlevel 1 goto end
)
".venv\Scripts\python.exe" -m pip install -r requirements-windows-build.txt
if errorlevel 1 goto end
".venv\Scripts\python.exe" build_windows.py
:end
popd
pause
exit /b
:folder_error
echo ERROR: Cannot access the program folder.
pause
exit /b 1
