@echo off
title NovaDL GitHub Setup
chcp 65001 > nul

echo.
echo ===================================
echo    NovaDL GitHub Setup
echo ===================================
echo.

if not exist main.py (
    echo ERROR: Ejecuta desde la carpeta raiz de NovaDL
    pause & exit /b 1
)

git --version > nul 2>&1
if errorlevel 1 (
    echo ERROR: Git no instalado. Descargalo en https://git-scm.com
    pause & exit /b 1
)

echo Directorio: %CD%
echo.

echo [1/4] Creando .gitignore...
echo bin/ > .gitignore
echo dist/ >> .gitignore
echo build/ >> .gitignore
echo installer/ >> .gitignore
echo pkg/ >> .gitignore
echo __pycache__/ >> .gitignore
echo *.spec >> .gitignore
echo *.pyc >> .gitignore
echo .novadl/ >> .gitignore
echo .vscode/ >> .gitignore
echo Thumbs.db >> .gitignore
echo desktop.ini >> .gitignore
echo       OK

echo [2/4] Creando .github\workflows...
if not exist .github mkdir .github
if not exist .github\workflows mkdir .github\workflows
echo       OK

echo [3/4] Buscando release.yml...
set RELEASE_YML=
if exist "%CD%\release.yml" set RELEASE_YML=%CD%\release.yml
if exist "%USERPROFILE%\Downloads\release.yml" set RELEASE_YML=%USERPROFILE%\Downloads\release.yml
if exist "%USERPROFILE%\Desktop\release.yml" set RELEASE_YML=%USERPROFILE%\Desktop\release.yml

if "%RELEASE_YML%"=="" (
    echo       No encontrado automaticamente.
    set /p RELEASE_YML="       Escribe la ruta al release.yml: "
)

if not exist "%RELEASE_YML%" (
    echo       AVISO: release.yml no encontrado. Copialo manualmente a .github\workflows\release.yml
) else (
    copy "%RELEASE_YML%" .github\workflows\release.yml > nul
    echo       OK
)

echo [4/4] Subiendo a GitHub...
echo.
echo Archivos detectados:
echo ----------------------------------------
git status --short
echo ----------------------------------------
echo.
set /p CONFIRM="Continuar con push? S/N: "
if /i "%CONFIRM%" neq "S" (
    echo Cancelado.
    goto :end
)

git add .
git commit -m "ci: workflow automatico y gitignore v1.2.0"
git push origin main
if errorlevel 1 (
    echo ERROR en git push. Verifica conexion y credenciales.
    pause & exit /b 1
)

:end
echo.
echo ===================================
echo         Completado
echo ===================================
echo.
echo Para publicar v1.2.0:
echo   git tag v1.2.0
echo   git push origin v1.2.0
echo.
pause
