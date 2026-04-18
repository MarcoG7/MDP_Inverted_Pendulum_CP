@echo off
REM Build script for Windows
REM Run from the repo root: packaging\build.bat
setlocal enabledelayedexpansion

echo =^> Building Angular frontend...
cd frontend\pendulum-cp-ui
call npm run build -- --configuration production
if errorlevel 1 (echo Angular build failed & exit /b 1)
cd ..\..

echo =^> Running PyInstaller...
call backend\.venv\Scripts\activate.bat
pip install pyinstaller --quiet
pyinstaller packaging\pendulum.spec --distpath packaging\dist --workpath packaging\build --noconfirm
if errorlevel 1 (echo PyInstaller failed & exit /b 1)

echo =^> Building Windows installer...
REM Requires Inno Setup to be installed: https://jrsoftware.org/isdl.php
set ISCC="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist %ISCC% (
    %ISCC% packaging\windows\installer.iss
    echo Installer created at: packaging\windows\Output\
) else (
    echo Inno Setup not found — skipping installer creation.
    echo Install from: https://jrsoftware.org/isdl.php
)

echo.
echo Done! App is at: packaging\dist\InvertedPendulumCP\
