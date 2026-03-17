import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Callable, Optional

import requests

from core.constants import (
    APP_EXE_NAME,
    APP_RELEASES_API,
    APP_VERSION,
    FFMPEG_PATH,
    FFMPEG_WINDOWS_ZIP_URL,
    APP_DIR,
)
from core.downloader import get_yt_dlp_cmd, safe_popen


def update_ytdlp(
    on_log: Callable[[str], None],
    on_status: Callable[[str], None],
) -> None:
    """
    Actualiza yt-dlp usando su propio flag -U.
    on_status recibe claves de STATUS_COLORS ('actualizando', 'listo', 'error').
    """
    try:
        on_status("actualizando")
        proc = safe_popen([get_yt_dlp_cmd(), "-U"])

        if proc.stdout is None:
            raise RuntimeError("No se pudo obtener stdout del proceso")

        for line in proc.stdout:
            on_log(line.rstrip())

        rc = proc.wait()
        if rc == 0:
            on_log("✓ yt-dlp actualizado")
            on_status("listo")
        else:
            on_log(f"✗ No se pudo actualizar yt-dlp (código {rc})")
            on_status("error")
    except Exception as e:
        on_log(f"✗ Error al actualizar yt-dlp: {e}")
        on_status("error")


def update_ffmpeg(
    on_log: Callable[[str], None],
    on_status: Callable[[str], None],
    on_progress: Callable[[float, str], None],
) -> None:
    """
    Descarga y reemplaza ffmpeg.exe (solo Windows).
    on_progress recibe (fracción 0-1, etiqueta '%').
    """
    if os.name != "nt":
        on_log("✗ La actualización automática de FFmpeg está preparada solo para Windows")
        on_status("error")
        return

    try:
        on_status("actualizando")
        on_progress(0.0, "0%")
        on_log("ℹ Descargando FFmpeg...")

        temp_dir = APP_DIR / "temp_ffmpeg_update"
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
        temp_dir.mkdir(parents=True, exist_ok=True)

        zip_path = temp_dir / "ffmpeg-release-essentials.zip"

        with requests.get(FFMPEG_WINDOWS_ZIP_URL, stream=True, timeout=90) as r:
            r.raise_for_status()
            total = int(r.headers.get("content-length", 0))
            downloaded = 0
            with open(zip_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 256):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total > 0:
                            pct = int(downloaded * 100 / total)
                            on_progress(pct / 100, f"{pct}%")

        on_log("ℹ Extrayendo FFmpeg...")
        extract_dir = temp_dir / "extracted"
        extract_dir.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extract_dir)

        candidates = list(extract_dir.rglob("ffmpeg.exe"))
        if not candidates:
            raise RuntimeError("No se encontró ffmpeg.exe dentro del ZIP descargado")

        source = candidates[0]
        if FFMPEG_PATH.exists():
            shutil.copy2(FFMPEG_PATH, FFMPEG_PATH.with_suffix(".exe.bak"))

        shutil.copy2(source, FFMPEG_PATH)
        on_progress(1.0, "100%")
        on_log("✓ FFmpeg actualizado correctamente")
        on_status("listo")
        shutil.rmtree(temp_dir, ignore_errors=True)

    except Exception as e:
        on_log(f"✗ Error al actualizar FFmpeg: {e}")
        on_status("error")


def check_app_update(
    on_log: Callable[[str], None],
    on_status: Callable[[str], None],
    on_progress: Callable[[float, str], None],
    on_show_dialog: Callable[[str, str], None],
) -> Optional[str]:
    """
    Comprueba si hay una versión nueva en GitHub y la descarga si aplica.
    on_show_dialog recibe (título, mensaje) para mostrarlo desde la UI.
    Retorna la URL de descarga manual si el binario no puede auto-actualizarse.
    """
    if not APP_RELEASES_API:
        on_log("ℹ Configura APP_RELEASES_API para habilitar el autoupdate")
        on_status("error")
        return None

    try:
        on_status("buscando")
        response = requests.get(APP_RELEASES_API, timeout=15)
        response.raise_for_status()
        release = response.json()

        latest_version = str(release.get("tag_name", "")).lstrip("v")
        if not latest_version:
            raise RuntimeError("La API no devolvió tag_name")

        if latest_version == APP_VERSION:
            on_log(f"✓ Ya tienes la última versión de la app: {APP_VERSION}")
            on_status("listo")
            return None

        assets = release.get("assets", [])
        download_url = next(
            (a.get("browser_download_url") for a in assets if a.get("name") == APP_EXE_NAME),
            None
        )

        if not download_url:
            raise RuntimeError(f"No se encontró {APP_EXE_NAME} en los assets del release")

        on_log(f"✓ Nueva versión detectada: {latest_version}")

        current_exe = Path(sys.executable)
        if current_exe.suffix.lower() != ".exe":
            on_log("ℹ Estás ejecutando NovaDL desde Python. El autoupdate funciona con el .exe compilado.")
            on_log(f"ℹ Descarga manual: {download_url}")
            on_status("listo")
            return download_url

        on_log("ℹ Descargando nueva versión...")
        on_status("actualizando")

        temp_exe = current_exe.with_name(f"{current_exe.stem}_new.exe")
        with requests.get(download_url, stream=True, timeout=60) as r:
            r.raise_for_status()
            total = int(r.headers.get("content-length", 0))
            downloaded = 0
            with open(temp_exe, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 256):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total > 0:
                            pct = int(downloaded * 100 / total)
                            on_progress(pct / 100, f"{pct}%")

        # Escribir bat de reemplazo
        updater_bat = current_exe.with_name("update_novadl.bat")
        bat = (
            f'@echo off\nchcp 65001 >nul\nsetlocal\nping 127.0.0.1 -n 3 >nul\n'
            f':waitloop\nmove /Y "{temp_exe}" "{current_exe}" >nul 2>&1\n'
            f'if errorlevel 1 (\n    ping 127.0.0.1 -n 2 >nul\n    goto waitloop\n)\nexit /b 0\n'
        )
        updater_bat.write_text(bat, encoding="utf-8")
        subprocess.Popen([str(updater_bat)], shell=True)

        on_log("✓ Actualización descargada e instalada.")
        on_log("ℹ Cierra y abre NovaDL manualmente para usar la nueva versión.")
        on_status("actualizado")
        on_show_dialog(
            "Actualización instalada",
            "La nueva versión de NovaDL ya fue instalada.\n\n"
            "Cierra esta ventana y abre NovaDL nuevamente de forma manual."
        )
        return None

    except Exception as e:
        on_log(f"✗ Error buscando/instalando update: {e}")
        on_status("error")
        return None
