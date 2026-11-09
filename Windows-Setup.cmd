@echo off
setlocal
pushd "%~dp0"
if errorlevel 1 goto folder_error
echo Program folder: %CD%
if not exist "follow.py" goto files_missing
if not exist "requirements-windows.txt" goto files_missing
py -3.12 -c "import sys; assert sys.version_info >= (3,10)" >nul 2>&1
if not errorlevel 1 goto use_py312
py -3.11 -c "import sys; assert sys.version_info >= (3,10)" >nul 2>&1
if not errorlevel 1 goto use_py311
py -3.10 -c "import sys; assert sys.version_info >= (3,10)" >nul 2>&1
if not errorlevel 1 goto use_py310
python -c "import sys; assert sys.version_info >= (3,10)" >nul 2>&1
if errorlevel 1 goto python_missing
python -m venv .venv
goto created
:use_py312
py -3.12 -m venv .venv
goto created
:use_py311
py -3.11 -m venv .venv
goto created
:use_py310
py -3.10 -m venv .venv
:created
if errorlevel 1 goto failed
if not exist ".venv\Scripts\python.exe" goto failed
".venv\Scripts\python.exe" -m pip install -r requirements-windows.txt
if errorlevel 1 goto failed
".venv\Scripts\python.exe" follow.py status
if errorlevel 1 goto failed
".venv\Scripts\python.exe" follow.py probe
if errorlevel 1 goto failed
echo Setup and read-only probe completed. No watcher has been started.
popd
pause
exit /b 0
:python_missing
echo ERROR: Python 3.10 or newer was not found via py or python.
echo Install Python for Windows from https://www.python.org/downloads/windows/
echo Enable the Python launcher and/or Add python.exe to PATH during installation.
echo Then close this window and run Windows-Setup.cmd again.
goto failed
:files_missing
echo ERROR: follow.py or requirements-windows.txt is missing.
echo Extract the entire ZIP into a folder. Do not run directly inside the ZIP viewer.
goto failed
:failed
echo Setup or probe failed. Copy the error above.
echo For the probe, switch BOTH keyboard and mouse to Windows channel 1 first.
popd
pause
exit /b 1
:folder_error
echo ERROR: Cannot access the program folder. Extract the ZIP to a local folder first.
pause
exit /b 1
