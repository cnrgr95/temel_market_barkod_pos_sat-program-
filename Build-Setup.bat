@echo off
setlocal
chcp 65001 >nul

set "ROOT=%~dp0"
cd /d "%ROOT%"

set "PYTHON_EXE=%ROOT%.venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=python"
"%PYTHON_EXE%" --version >nul 2>nul
if errorlevel 1 (
    echo HATA: Python yorumlayici bulunamadi.
    echo Beklenen yol: %ROOT%.venv\Scripts\python.exe
    echo Cozum: once sanal ortami olusturup bagimliliklari kurun.
    if not "%TEMELMARKET_NO_PAUSE%"=="1" pause
    exit /b 1
)

set "APP_VERSION="
set "APP_VERSION_FILE=%TEMP%\temelmarket_app_version.txt"
"%PYTHON_EXE%" "%ROOT%tools\read_app_version.py" > "%APP_VERSION_FILE%"
if exist "%APP_VERSION_FILE%" (
    set /p APP_VERSION=<"%APP_VERSION_FILE%"
    del "%APP_VERSION_FILE%" >nul 2>nul
)
if not defined APP_VERSION (
    echo HATA: APP_VERSION bilgisi flet_pos\app.py dosyasindan okunamadi.
    if not "%TEMELMARKET_NO_PAUSE%"=="1" pause
    exit /b 1
)

set "OUTPUT_ROOT=%ROOT%out"
if not exist "%OUTPUT_ROOT%" mkdir "%OUTPUT_ROOT%"
set "BUILD_ID=%RANDOM%%RANDOM%"
set "DIST_DIR=%OUTPUT_ROOT%\dist_v%APP_VERSION%_%BUILD_ID%"
set "WORK_DIR=%OUTPUT_ROOT%\build_v%APP_VERSION%_%BUILD_ID%"

set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" (
    for /f "delims=" %%I in ('where ISCC.exe 2^>nul') do (
        set "ISCC=%%I"
        goto :iscc_found
    )
)
:iscc_found
if not exist "%ISCC%" (
    echo HATA: Inno Setup Compiler bulunamadi.
    echo Inno Setup yuklemek icin:
    echo winget install --id JRSoftware.InnoSetup -e --accept-package-agreements --accept-source-agreements
    if not "%TEMELMARKET_NO_PAUSE%"=="1" pause
    exit /b 1
)

if not exist "%ROOT%installer\install_webview2.ps1" (
    echo HATA: installer\install_webview2.ps1 dosyasi eksik.
    if not "%TEMELMARKET_NO_PAUSE%"=="1" pause
    exit /b 1
)

if not exist "%ROOT%installer" mkdir "%ROOT%installer"

echo ============================================
echo   1/2 EXE build (PyInstaller)
echo ============================================
"%PYTHON_EXE%" -m PyInstaller --clean --noconfirm --distpath "%DIST_DIR%" --workpath "%WORK_DIR%" "TemelMarket.spec"
if errorlevel 1 (
    echo HATA: EXE build basarisiz.
    if not "%TEMELMARKET_NO_PAUSE%"=="1" pause
    exit /b 1
)

echo ============================================
echo   2/2 Setup.exe build (Inno Setup)
echo ============================================
"%ISCC%" "/DMyAppVersion=%APP_VERSION%" "/DMyDistDir=%DIST_DIR%\TemelMarket" "%ROOT%installer.iss"
if errorlevel 1 (
    echo HATA: Setup olusturulamadi.
    if not "%TEMELMARKET_NO_PAUSE%"=="1" pause
    exit /b 1
)

echo.
echo Basarili: installer\TemelMarket-Setup-%APP_VERSION%.exe
echo.
if not "%TEMELMARKET_NO_PAUSE%"=="1" pause
exit /b 0
