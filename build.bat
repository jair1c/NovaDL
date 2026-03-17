@echo off
title NovaDL Builder
chcp 65001 > nul

echo.
echo ===================================
echo    NovaDL Builder  by DARK-CODE
echo ===================================
echo.

:: Leer version desde constants.py
set APP_VERSION=unknown
for /f "tokens=3 delims= " %%v in ('findstr "APP_VERSION" core\constants.py') do set RAW_VER=%%v
set APP_VERSION=%RAW_VER:"=%
echo Version detectada: v%APP_VERSION%
echo.

:: 1 - Limpiar builds anteriores
echo [1/6] Limpiando builds anteriores...
if exist build     rmdir /s /q build
if exist dist      rmdir /s /q dist
if exist installer rmdir /s /q installer
if exist NovaDL.spec del /q NovaDL.spec
echo       OK
echo.

:: 2 - Dependencias
echo [2/6] Instalando dependencias...
pip install psutil customtkinter pillow requests pyinstaller --quiet
if errorlevel 1 goto :error
echo       OK
echo.

:: 3 - Compilar PyInstaller
echo [3/6] Compilando ejecutable...
pyinstaller --noconfirm --onefile --windowed --icon assets\icon.ico --name NovaDL --add-data "core;core" --add-data "ui;ui" --add-data "assets;assets" --hidden-import psutil --hidden-import PIL --hidden-import PIL.Image --hidden-import PIL.ImageDraw main.py
if errorlevel 1 goto :error
if not exist dist\NovaDL.exe goto :error
echo       OK
echo.

:: 4 - Copiar bin
echo [4/6] Copiando yt-dlp y ffmpeg...
if not exist dist\bin mkdir dist\bin
if exist bin\yt-dlp.exe copy bin\yt-dlp.exe dist\bin\ > nul
if exist bin\ffmpeg.exe  copy bin\ffmpeg.exe dist\bin\ > nul
echo       OK
echo.

:: 5 - Portable ZIP
echo [5/6] Empaquetando portable...
if not exist dist\portable mkdir dist\portable
if not exist dist\portable\NovaDL mkdir dist\portable\NovaDL
copy dist\NovaDL.exe dist\portable\NovaDL\NovaDL.exe > nul
if not exist dist\portable\NovaDL\bin mkdir dist\portable\NovaDL\bin
if exist dist\bin\yt-dlp.exe copy dist\bin\yt-dlp.exe dist\portable\NovaDL\bin\ > nul
if exist dist\bin\ffmpeg.exe copy dist\bin\ffmpeg.exe dist\portable\NovaDL\bin\ > nul
if exist README.md copy README.md dist\portable\NovaDL\ > nul

powershell -NoProfile -Command "Compress-Archive -Path 'dist\portable\NovaDL' -DestinationPath 'dist\NovaDL_Portable_v%APP_VERSION%.zip' -Force"
if errorlevel 1 (
    echo       AVISO: No se pudo crear el ZIP con PowerShell
) else (
    echo       OK  --  NovaDL_Portable_v%APP_VERSION%.zip
)
echo.

:: 6 - Instalador Inno Setup
echo [6/6] Generando instalador...
set ISCC=
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist "C:\Program Files\Inno Setup 6\ISCC.exe"       set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"

if "%ISCC%"=="" (
    echo       AVISO: Inno Setup 6 no encontrado. Se omite el instalador.
    echo       Descargalo en: https://jrsoftware.org/isinfo.php
    goto :end
)

if not exist installer mkdir installer
"%ISCC%" /DAppVersion=%APP_VERSION% NovaDL.iss
if errorlevel 1 (
    echo       AVISO: Error al compilar NovaDL.iss
    goto :end
)
echo       OK  --  NovaDL_Setup_v%APP_VERSION%.exe
echo.

:end
echo.
echo ===================================
echo        Build completado
echo ===================================
echo.
echo Archivos generados:
if exist "dist\NovaDL_Portable_v%APP_VERSION%.zip"   echo   dist\NovaDL_Portable_v%APP_VERSION%.zip
if exist "installer\NovaDL_Setup_v%APP_VERSION%.exe" echo   installer\NovaDL_Setup_v%APP_VERSION%.exe
echo.
echo Presiona cualquier tecla para cerrar...
pause > nul
exit /b 0

:error
echo.
echo ===================================
echo   ERROR en el paso anterior
echo ===================================
echo.
pause
exit /b 1
