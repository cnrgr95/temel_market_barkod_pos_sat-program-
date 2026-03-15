@echo off
setlocal
chcp 65001 >nul

set "ROOT=%~dp0"
cd /d "%ROOT%"

set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" (
    echo HATA: Inno Setup Compiler bulunamadi.
    echo Beklenen yol: "%ISCC%"
    echo Inno Setup yuklemek icin:
    echo winget install --id JRSoftware.InnoSetup -e --accept-package-agreements --accept-source-agreements
    pause
    exit /b 1
)

echo ============================================
echo   1/2 EXE build (PyInstaller)
echo ============================================
python -m PyInstaller --noconfirm --windowed --onedir --name TemelMarket --icon assets\temelmarket.ico --distpath dist_final --workpath build_final --specpath . --add-data "assets\temelmarket_icon.png;assets" --add-data "assets\temelmarket.ico;assets" --collect-all flet --collect-all flet_desktop main.py
if errorlevel 1 (
    echo HATA: EXE build basarisiz.
    pause
    exit /b 1
)

echo ============================================
echo   2/2 Setup.exe build (Inno Setup)
echo ============================================
"%ISCC%" "%ROOT%installer.iss"
if errorlevel 1 (
    echo HATA: Setup olusturulamadi.
    pause
    exit /b 1
)

echo.
echo Basarili: installer\TemelMarket-Setup.exe
echo.
pause
exit /b 0
