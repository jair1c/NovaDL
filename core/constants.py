import os
import sys
from pathlib import Path

APP_NAME = "NovaDL"
APP_VERSION = "1.2.0"

if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent.parent

APP_DIR = Path.home() / ".novadl"
BIN_DIR = BASE_DIR / "bin"
DOWNLOAD_DIR = Path.home() / "Downloads" / "NovaDL"

SETTINGS_FILE     = APP_DIR / "settings.json"
HISTORY_FILE      = APP_DIR / "download_history.json"
ERROR_HISTORY_FILE = APP_DIR / "error_history.json"

YTDLP_PATH = BIN_DIR / ("yt-dlp.exe" if os.name == "nt" else "yt-dlp")
FFMPEG_PATH = BIN_DIR / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")

APP_RELEASES_API      = "https://api.github.com/repos/jair1c/NovaDL/releases/latest"
APP_EXE_NAME          = "NovaDL.exe"
FFMPEG_WINDOWS_ZIP_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"

DEFAULT_WINDOW_GEOMETRY = "1280x820+40+20"
MAX_HISTORY_ITEMS  = 100
AUTO_RETRY_COUNT   = 2          # reintentos automáticos por descarga
SPLASH_MS          = 1200
MAX_LOG_LINES      = 500        # líneas máximas antes de recortar el log
LOG_TRIM_LINES     = 100        # líneas que quedan tras recorte
COOKIES_FILE_KEY   = "cookies_file"

# v0.6.4 — descargas paralelas
MAX_PARALLEL_DOWNLOADS = 4      # techo absoluto de workers simultáneos

# v0.6.4 — plantillas de nombre predefinidas
OUTPUT_TEMPLATE_DEFAULT  = "%(title)s [%(id)s]"
OUTPUT_TEMPLATES = {
    "Título [ID]":              "%(title)s [%(id)s]",
    "Título":                   "%(title)s",
    "Canal - Título":           "%(uploader)s - %(title)s",
    "Canal - Título [ID]":      "%(uploader)s - %(title)s [%(id)s]",
    "Fecha - Título":           "%(upload_date)s - %(title)s",
    "Playlist# - Título [ID]":  "%(playlist_index)s - %(title)s [%(id)s]",
    "Personalizado…":           "",
}

AUDIO_FORMATS = {"MP3", "M4A", "WAV", "FLAC"}

# v1.1 — carpetas automáticas por formato
FORMAT_SUBFOLDERS = {
    "MP3":  "Música",
    "M4A":  "Música",
    "WAV":  "Música",
    "FLAC": "Música",
    "MP4":  "Videos",
    "MKV":  "Videos",
}

# v1.1 — cola persistente
QUEUE_FILE = APP_DIR / "pending_queue.json"

# v1.2 — idiomas de subtítulos disponibles
SUBTITLE_LANGS = [
    "Ninguno", "es", "en", "pt", "fr", "de",
    "it", "ja", "ko", "zh", "ru", "ar",
]

# v1.2 — temas disponibles
THEMES = ["dark", "light"]

STATUS_COLORS = {
    "listo":        "#1a1a1a",   # gris oscuro neutro — no azul
    "descargando":  "#e63333",   # rojo Nexus activo
    "completado":   "#1a6632",   # verde oscuro
    "error":        "#7a1a1a",   # rojo oscuro
    "cancelado":    "#7a1a1a",
    "actualizando": "#7a4a00",   # naranja oscuro
    "escaneando":   "#7a4a00",
    "buscando":     "#7a4a00",
    "cancelando":   "#7a4a00",
    "reintentando": "#7a4a00",
    "actualizado":  "#1a6632",
}

# Crear directorios necesarios al importar
APP_DIR.mkdir(parents=True, exist_ok=True)
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
BIN_DIR.mkdir(parents=True, exist_ok=True)
