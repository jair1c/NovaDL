import os
import re
import subprocess
from pathlib import Path
from shutil import which
from typing import Callable, Optional

from core.constants import (
    AUDIO_FORMATS,
    AUTO_RETRY_COUNT,
    FFMPEG_PATH,
    YTDLP_PATH,
    OUTPUT_TEMPLATE_DEFAULT,
)
from core.models import QueueItem


# ---------------------------------------------------------------------------
# Helpers de proceso
# ---------------------------------------------------------------------------

def which_or_none(name: str) -> Optional[str]:
    return which(name)


def get_yt_dlp_cmd() -> str:
    if YTDLP_PATH.exists():
        return str(YTDLP_PATH)
    system = which_or_none("yt-dlp")
    if system:
        return system
    raise FileNotFoundError(
        f"No se encontró yt-dlp. Coloca yt-dlp.exe en la carpeta: {YTDLP_PATH.parent}"
    )


def get_ffmpeg_cmd() -> str:
    if FFMPEG_PATH.exists():
        return str(FFMPEG_PATH)
    system = which_or_none("ffmpeg")
    if system:
        return system
    raise FileNotFoundError(
        f"No se encontró ffmpeg. Coloca ffmpeg.exe en la carpeta: {FFMPEG_PATH.parent}"
    )


def safe_popen(args: list) -> subprocess.Popen:
    """Lanza un subproceso ocultando la ventana de consola en Windows."""
    startupinfo = None
    creationflags = 0
    if os.name == "nt":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        creationflags = subprocess.CREATE_NO_WINDOW

    return subprocess.Popen(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        startupinfo=startupinfo,
        creationflags=creationflags,
    )


def send_notification(title: str, message: str) -> None:
    """Envía notificación del sistema usando plyer. Falla silenciosamente."""
    try:
        from plyer import notification
        notification.notify(
            title=title,
            message=message,
            app_name="NovaDL",
            timeout=5,
        )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Construcción del comando yt-dlp
# ---------------------------------------------------------------------------

def _audio_quality_value(value: str) -> str:
    return {"Mejor calidad": "0", "320K": "320K", "192K": "192K", "128K": "128K"}.get(value, "0")


def _video_height_value(value: str) -> Optional[str]:
    return {
        "2160p": "2160", "1440p": "1440", "1080p": "1080",
        "720p": "720",   "480p": "480",   "360p": "360",
    }.get(value)


def _rate_limit_value(value: str) -> Optional[str]:
    return {
        "Sin límite": None, "Sin limite": None,
        "5 MB/s": "5M", "2 MB/s": "2M", "1 MB/s": "1M",
        "500 KB/s": "500K", "250 KB/s": "250K",
    }.get(value)


def build_download_command(item: QueueItem) -> list:
    """
    Construye el comando yt-dlp completo para un QueueItem.

    v0.6.4:
      - La plantilla de salida se toma de item.output_template (o default).
      - Las cookies y cualquier arg extra vienen en item.extra_args.
      - Ya no acepta cookies_file como parámetro separado (retrocompatibilidad
        mantenida: si extra_args está vacío el comportamiento es idéntico al anterior).
    """
    # ── Plantilla de salida ─────────────────────────────────────────────────
    tpl = (item.output_template or OUTPUT_TEMPLATE_DEFAULT).strip()

    # Para playlists añadimos el índice al frente si la plantilla no lo incluye
    if item.download_playlist and "%(playlist_index)s" not in tpl:
        tpl = "%(playlist_index)s - " + tpl

    # BUG 2 FIX: evitar doble extensión si el usuario incluyó .ext en la plantilla
    _known_exts = {".mp3", ".m4a", ".wav", ".flac", ".mp4", ".mkv", ".webm", ".opus"}
    tpl_path = Path(tpl)
    if tpl_path.suffix.lower() in _known_exts:
        tpl = str(tpl_path.with_suffix(""))

    ext = item.format_type.lower()
    output_template = os.path.join(item.output_dir, tpl + "." + ext)

    cmd = [
        get_yt_dlp_cmd(),
        "--newline", "--progress",
        "-P", item.output_dir,
        "-o", output_template,
        "--ffmpeg-location", str(Path(get_ffmpeg_cmd()).parent),
    ]

    # ── Args extra (cookies, etc.) ───────────────────────────────────────────
    if item.extra_args:
        cmd += item.extra_args

    # ── Proxy (v1.2) ─────────────────────────────────────────────────────────
    if item.proxy and item.proxy.strip():
        cmd += ["--proxy", item.proxy.strip()]

    # ── Subtítulos (v1.2) ────────────────────────────────────────────────────
    if item.subtitle_lang and item.subtitle_lang != "Ninguno":
        cmd += [
            "--write-subs",
            "--write-auto-subs",
            "--sub-lang", item.subtitle_lang,
            "--embed-subs",
        ]

    # ── Velocidad ───────────────────────────────────────────────────────────
    rate_limit = _rate_limit_value(item.rate_limit)
    if rate_limit:
        cmd += ["--limit-rate", rate_limit]

    # ── Playlist ────────────────────────────────────────────────────────────
    if not item.download_playlist:
        cmd.append("--no-playlist")

    # ── Formato ─────────────────────────────────────────────────────────────
    if item.format_type in AUDIO_FORMATS:
        ffmpeg_audio_map = {"MP3": "mp3", "M4A": "m4a", "WAV": "wav", "FLAC": "flac"}
        cmd += ["-x", "--audio-format", ffmpeg_audio_map[item.format_type]]
        if item.format_type == "MP3":
            cmd += ["--audio-quality", _audio_quality_value(item.quality)]
        if item.add_thumbnail:
            cmd += ["--embed-thumbnail", "--add-metadata"]
    else:
        max_height = _video_height_value(item.quality)
        fmt = (
            "bv*[height<=" + max_height + "]+ba/b[height<=" + max_height + "]/b"
            if max_height else "bv*+ba/b"
        )
        merge_target = "mkv" if item.format_type == "MKV" else "mp4"
        cmd += ["-f", fmt, "--merge-output-format", merge_target]
        if item.add_thumbnail:
            cmd += ["--embed-metadata"]

    cmd.append(item.url)
    return cmd


# ---------------------------------------------------------------------------
# Parsing de progreso
# ---------------------------------------------------------------------------

def parse_progress_line(line: str) -> dict:
    result = {}

    m = re.search(r"\[download\]\s+(\d+(?:\.\d+)?)%", line)
    if m:
        result["percent"] = float(m.group(1)) / 100.0
        result["percent_label"] = m.group(1) + "%"

    m = re.search(r"of\s+([~\d.\wBi/]+)", line)
    if m:
        result["size"] = "Tamaño: " + m.group(1)

    m = re.search(r"at\s+([~\d.\wBi/]+/s)", line)
    if m:
        result["speed"] = "Velocidad: " + m.group(1)

    m = re.search(r"ETA\s+([\d:]+)", line)
    if m:
        result["eta"] = "ETA: " + m.group(1)

    if any(k in line for k in ("Destination:", "Merging formats", "Post-process")):
        result["nudge"] = True

    return result


# ---------------------------------------------------------------------------
# Ejecución de un ítem de cola
# ---------------------------------------------------------------------------

def run_queue_item(
    item: QueueItem,
    on_log: Callable[[str], None],
    on_progress: Callable[[dict], None],
    cancel_flag: Callable[[], bool],
    set_process: Callable[[Optional[subprocess.Popen]], None],
    # Mantenido por retrocompatibilidad; preferir item.extra_args
    cookies_file: Optional[str] = None,
) -> None:
    # Si se pasa cookies_file por el camino viejo, lo inyectamos en extra_args
    if cookies_file and Path(cookies_file).exists():
        if "--cookies" not in item.extra_args:
            item.extra_args = ["--cookies", cookies_file] + list(item.extra_args)

    cmd = build_download_command(item)
    on_log("$ " + " ".join('"' + x + '"' if " " in x else x for x in cmd))

    last_error: Optional[str] = None

    # BUG 1 FIX: leer en tiempo de ejecución para respetar cambios desde la UI
    import core.constants as _cc
    max_retries = _cc.AUTO_RETRY_COUNT

    for attempt in range(1, max_retries + 2):
        if attempt > 1:
            on_log(f"↺ Reintento {attempt - 1}/{max_retries}: {item.url}")
            on_progress({"status": "reintentando", "attempt": attempt})
        else:
            on_progress({"status": "descargando"})

        proc = safe_popen(cmd)
        set_process(proc)

        if proc.stdout is None:
            raise RuntimeError("No se pudo obtener stdout del proceso")

        for line in proc.stdout:
            on_log(line.rstrip())
            on_progress(parse_progress_line(line))

        rc = proc.wait()
        set_process(None)

        if cancel_flag():
            on_log("✗ Descarga cancelada por el usuario")
            on_progress({"status": "cancelado"})
            raise RuntimeError("Descarga cancelada")

        if rc == 0:
            on_progress({"percent": 1.0, "percent_label": "100%", "status": "completado"})
            on_log("✓ Descarga completada")
            # BUG 3 FIX: notificación eliminada aquí — app.py la maneja con
            # control del toggle notify_var para evitar notificación doble.
            return

        last_error = f"La descarga terminó con código {rc}"
        if attempt <= max_retries:
            on_log(f"✗ Falló el intento {attempt}. Reintentando...")

    # BUG 3 FIX: notificación de error también eliminada — app.py la maneja.
    raise RuntimeError(last_error or "Error desconocido")
