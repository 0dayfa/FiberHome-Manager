@echo off
REM ========================================================================
REM   FiberHome Manager - Beta : smart build pipeline
REM   Verifies the environment, only installs what's missing, then bundles.
REM   Run from anywhere — the script auto-jumps into its own directory.
REM ========================================================================
setlocal enabledelayedexpansion

REM Always operate from the directory this script lives in, not the
REM caller's CWD. Solves "Could not open requirements.txt" when the
REM user runs build.bat by double-clicking from another folder.
pushd "%~dp0"

echo.
echo  =========================================================
echo    FiberHome Manager - Beta  ::  build pipeline
echo  =========================================================
echo.

REM -----------------------------------------------------------------
REM  STEP 1 :: Verify Python on PATH
REM -----------------------------------------------------------------
echo [1/5] Checking Python...
where python >nul 2>nul
if errorlevel 1 (
    echo  [X] Python is NOT on PATH.
    echo      Install Python 3.10+ from https://www.python.org/downloads/
    echo      Make sure to tick "Add Python to PATH" during install.
    goto :fail
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo  [+] Python !PYVER! detected
REM Refuse anything older than 3.10 — we use modern type hints + walrus.
for /f "tokens=1,2 delims=." %%a in ("!PYVER!") do (
    set PYMAJ=%%a
    set PYMIN=%%b
)
if !PYMAJ! LSS 3 goto :pyold
if !PYMAJ! EQU 3 if !PYMIN! LSS 10 goto :pyold

REM -----------------------------------------------------------------
REM  STEP 2 :: Verify pip
REM -----------------------------------------------------------------
echo.
echo [2/5] Checking pip...
python -m pip --version >nul 2>nul
if errorlevel 1 (
    echo  [X] pip is missing. Re-install Python with the pip option enabled.
    goto :fail
)
echo  [+] pip OK

REM -----------------------------------------------------------------
REM  STEP 3 :: Check required project files exist
REM -----------------------------------------------------------------
echo.
echo [3/5] Checking project files...
if not exist "requirements.txt" (
    echo  [X] requirements.txt missing in %CD%
    echo      Make sure build.bat lives in the project root next to it.
    goto :fail
)
if not exist "FiberHomeManager.spec" (
    echo  [X] FiberHomeManager.spec missing.
    goto :fail
)
echo  [+] requirements.txt + FiberHomeManager.spec present

REM -----------------------------------------------------------------
REM  STEP 4 :: Install dependencies (only what's missing)
REM -----------------------------------------------------------------
echo.
echo [4/5] Verifying dependencies...

REM Each module-name corresponds to the Python import name (NOT the
REM pip package name) so we can detect it via `python -c "import X"`.
call :ensure PyQt5            PyQt5
call :ensure PyQt5.QtWebEngineWidgets   PyQtWebEngine
call :ensure websocket        websocket-client
call :ensure PyInstaller      pyinstaller
if errorlevel 1 goto :fail

REM -----------------------------------------------------------------
REM  STEP 5 :: Run PyInstaller
REM -----------------------------------------------------------------
echo.
echo [5/5] Building bundle (this can take ~30s)...
python -m PyInstaller FiberHomeManager.spec --noconfirm
if errorlevel 1 (
    echo.
    echo  [X] PyInstaller failed. Read the error above for details.
    echo      Common causes:
    echo        - Antivirus locked dist\
    echo        - Previous EXE still running ^(close it first^)
    echo        - Out of disk space
    goto :fail
)

echo.
echo  =========================================================
echo    Build complete.
echo.
echo    Folder :  dist\FiberHome Manager - Beta\
echo    Run    :  "dist\FiberHome Manager - Beta\FiberHome Manager - Beta.exe"
echo  =========================================================
echo.
popd
pause
exit /b 0


REM ========================================================================
REM   :ensure  <import_name>  <pip_package_name>
REM   Tests `python -c "import <import_name>"`.
REM   If it fails, runs `pip install <pip_package_name>` once.
REM   Returns 0 on success, 1 on failure (caller jumps to :fail).
REM ========================================================================
:ensure
set IMPORT_NAME=%~1
set PIP_NAME=%~2
python -c "import !IMPORT_NAME!" >nul 2>nul
if not errorlevel 1 (
    echo  [+] !PIP_NAME!  ^(already installed^)
    exit /b 0
)
echo  [~] !PIP_NAME!  not found, installing...
python -m pip install --quiet --disable-pip-version-check !PIP_NAME!
if errorlevel 1 (
    echo  [X] Failed to install !PIP_NAME!.
    echo      Try a manual:  python -m pip install !PIP_NAME!
    exit /b 1
)
REM Verify the install actually surfaced the import.
python -c "import !IMPORT_NAME!" >nul 2>nul
if errorlevel 1 (
    echo  [X] !PIP_NAME! installed but import !IMPORT_NAME! still fails.
    exit /b 1
)
echo  [+] !PIP_NAME!  ^(installed^)
exit /b 0


:pyold
echo  [X] Python !PYVER! is too old. Need 3.10 or newer.
echo      Upgrade from https://www.python.org/downloads/
goto :fail


:fail
echo.
echo  Build aborted.
echo.
popd
pause
exit /b 1
