import json
import os
import queue
import re
import subprocess
import sys
import threading
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Optional

import customtkinter as ctk

from core.constants import (
    APP_NAME, APP_VERSION, AUDIO_FORMATS,
    AUTO_RETRY_COUNT, DEFAULT_WINDOW_GEOMETRY, DOWNLOAD_DIR,
    ERROR_HISTORY_FILE, HISTORY_FILE, LOG_TRIM_LINES, MAX_LOG_LINES,
    MAX_HISTORY_ITEMS, MAX_PARALLEL_DOWNLOADS, OUTPUT_TEMPLATE_DEFAULT,
    OUTPUT_TEMPLATES, SPLASH_MS, STATUS_COLORS,
    FORMAT_SUBFOLDERS, QUEUE_FILE,
    SUBTITLE_LANGS, THEMES,
)
from core.downloader import (
    build_download_command, get_yt_dlp_cmd,
    parse_progress_line, run_queue_item, safe_popen,
)
from core.models import ErrorHistoryItem, HistoryItem, QueueItem
from core.settings import HistoryStore, Settings
import core.updater as updater

from ui.splash import SplashScreen
from ui.widgets import load_thumbnail_from_url, make_ctk_thumbnail
from ui.tabs.download import build_download_tab
from ui.tabs.queue import build_queue_tab
from ui.tabs.history import build_history_tab
from ui.tabs.errors import build_errors_tab
from ui.tabs.tools import build_tools_tab
from ui.tabs.about import build_about_tab

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ── Paleta global Nexus ──────────────────────────────────────────────────────
_RED      = "#e63333"
_RED_DIM  = "#2a0a0a"
_BG_APP   = "#080808"
_BG_SIDE  = "#0d0d0d"
_BG_PANEL = "#0d0d0d"
_BORDER   = "#1e1e1e"
_TXT_DIM  = "#555555"
_TXT_MID  = "#aaaaaa"
_TXT_MAIN = "#ffffff"
_MONO     = "Courier New"

# ── Validación de URL ────────────────────────────────────────────────────────
URL_PATTERN = re.compile(
    r"^(https?://)?(www\.)?"
    r"(youtube\.com|youtu\.be|soundcloud\.com|bandcamp\.com|"
    r"vimeo\.com|dailymotion\.com|twitch\.tv|twitter\.com|"
    r"x\.com|instagram\.com|facebook\.com|tiktok\.com|"
    r"bilibili\.com|reddit\.com|rumble\.com|"
    r"[a-zA-Z0-9\-]+\.[a-zA-Z]{2,})"
    r"(/\S*)?$",
    re.IGNORECASE,
)


def _is_valid_url(url: str) -> bool:
    return bool(URL_PATTERN.match(url.strip()))


def _open_folder(path: str):
    if os.name == "nt":
        os.startfile(path)
    elif sys.platform == "darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


def _notify(title: str, message: str):
    """Notificación de escritorio multiplataforma. No bloquea."""
    try:
        if sys.platform == "darwin":
            script = f'display notification "{message}" with title "{title}"'
            subprocess.Popen(["osascript", "-e", script])
        elif os.name == "nt":
            try:
                from win10toast import ToastNotifier
                ToastNotifier().show_toast(title, message, duration=4, threaded=True)
            except ImportError:
                pass
        else:
            subprocess.Popen(["notify-send", "-t", "4000", title, message])
    except Exception:
        pass


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.withdraw()

        # ── Estado persistido ───────────────────────────────────────────────
        self.settings = Settings.load()
        self.history_items: list[HistoryItem] = HistoryStore.load(HISTORY_FILE, HistoryItem)
        self.error_history_items: list[ErrorHistoryItem] = HistoryStore.load(ERROR_HISTORY_FILE, ErrorHistoryItem)

        # ── Configuración de ventana ─────────────────────────────────────────
        self.title(f"{APP_NAME} {APP_VERSION}")
        self.geometry(self.settings.get("window_geometry", DEFAULT_WINDOW_GEOMETRY))
        self.minsize(1180, 760)

        # ── Variables CTk ────────────────────────────────────────────────────
        self.format_var          = ctk.StringVar(value=self.settings.get("format_type", "MP3"))
        self.playlist_var        = ctk.BooleanVar(value=self.settings.get("download_playlist", True))
        self.output_var          = ctk.StringVar(value=self.settings.get("output_dir", str(DOWNLOAD_DIR)))
        self.thumb_var           = ctk.BooleanVar(value=self.settings.get("add_thumbnail", True))
        self.rate_limit_var      = ctk.StringVar(value=self.settings.get("rate_limit", "Sin límite"))
        self.audio_quality_var   = ctk.StringVar(value=self.settings.get("audio_quality", "Mejor calidad"))
        self.video_quality_var   = ctk.StringVar(value=self.settings.get("video_quality", "Mejor calidad"))

        # cookies
        self.cookies_var         = ctk.StringVar(value=self.settings.get("cookies_path", ""))
        self.cookies_browser_var = ctk.StringVar(value=self.settings.get("cookies_browser", "Ninguno"))

        # notificaciones
        self.notify_var          = ctk.BooleanVar(value=self.settings.get("notifications", True))

        # v0.6.4 — plantilla de nombre
        saved_preset = self.settings.get("output_template_preset", "Título [ID]")
        self.output_template_preset_var = ctk.StringVar(value=saved_preset)
        self.output_template_var = ctk.StringVar(
            value=self.settings.get("output_template", OUTPUT_TEMPLATE_DEFAULT)
        )

        # v0.6.4 — reintentos configurables
        self.retry_count_var = ctk.StringVar(
            value=str(self.settings.get("retry_count", AUTO_RETRY_COUNT))
        )

        # v0.6.4 — descargas paralelas
        self.parallel_var = ctk.StringVar(
            value=str(self.settings.get("parallel_downloads", 1))
        )

        # v1.1 — carpetas automáticas por formato
        self.auto_subfolders_var = ctk.BooleanVar(
            value=self.settings.get("auto_subfolders", False)
        )

        # v1.1 — vista previa enriquecida
        self.views_var       = ctk.StringVar(value="-")
        self.upload_date_var = ctk.StringVar(value="-")
        self.filesize_var    = ctk.StringVar(value="-")
        self.formats_var     = ctk.StringVar(value="-")

        # v1.2 — proxy
        self.proxy_var = ctk.StringVar(value=self.settings.get("proxy", ""))

        # v1.2 — subtítulos
        self.subtitle_var = ctk.StringVar(
            value=self.settings.get("subtitle_lang", "Ninguno")
        )

        # v1.2 — tema claro/oscuro
        self.theme_var = ctk.StringVar(
            value=self.settings.get("theme", "dark")
        )
        # Aplicar tema guardado al arrancar
        ctk.set_appearance_mode(self.theme_var.get())

        # v1.2 — programador de descargas
        self._scheduler_timer: Optional[threading.Timer] = None
        self.scheduler_active_var = ctk.BooleanVar(value=False)

        # estado UI
        self.status_var            = ctk.StringVar(value="Listo")
        self.status_detail_var     = ctk.StringVar(value="Esperando acción")
        self.title_var             = ctk.StringVar(value="Sin escanear")
        self.channel_var           = ctk.StringVar(value="-")
        self.duration_var          = ctk.StringVar(value="-")
        self.playlist_info_var     = ctk.StringVar(value="No se detectó playlist")
        self.progress_label_var    = ctk.StringVar(value="0%")
        self.queue_count_var       = ctk.StringVar(value="En cola: 0")
        self.downloading_count_var = ctk.StringVar(value="Descargando: 0")
        self.completed_count_var   = ctk.StringVar(
            value=f"Completadas: {self.settings.get('completed_count', 0)}"
        )
        self.speed_var             = ctk.StringVar(value="Velocidad: -")
        self.size_var              = ctk.StringVar(value="Tamaño: -")
        self.eta_var               = ctk.StringVar(value="ETA: -")
        self.global_progress_var   = ctk.StringVar(value="")

        # ── Estado interno ───────────────────────────────────────────────────
        self.is_downloading      = False
        self.download_queue: queue.Queue[QueueItem] = queue.Queue()
        self.queue_items: list[QueueItem] = []
        self.current_process: Optional[subprocess.Popen] = None
        self._cancel_requested   = False
        self._queue_lock         = threading.Lock()
        self.completed_count     = self.settings.get("completed_count", 0)
        self.log_queue: queue.Queue[str] = queue.Queue()
        self._log_line_count     = 0

        # v0.6.4 — semáforo para descargas paralelas
        self._active_workers     = 0
        self._workers_lock       = threading.Lock()
        self._global_total       = 0
        self._global_done        = 0

        # ── UI ───────────────────────────────────────────────────────────────
        self._build_ui()
        self.update_format_ui()
        self.refresh_history_view()
        self.refresh_error_history_view()
        self.refresh_queue_view()
        self.update_counters()
        self.set_status("listo", "Esperando acción")

        # v1.1 — restaurar cola pendiente de sesión anterior
        self._restore_pending_queue()

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.after(120, self._process_log_queue)
        self.after(120, self._process_log_queue)

        self._splash = SplashScreen(self)
        self.after(SPLASH_MS, self._finish_startup)

    # =========================================================================
    # Startup / shutdown
    # =========================================================================

    def _finish_startup(self):
        try:
            self._splash.destroy()
        except Exception:
            pass
        self.deiconify()
        try:
            if os.name == "nt":
                self.state("zoomed")
            else:
                self.attributes("-zoomed", True)
        except Exception:
            pass
        self.lift()
        self.focus_force()

    def on_close(self):
        self._save_pending_queue()  # v1.1
        self.save_settings()
        self.destroy()

    # =========================================================================
    # Cola persistente  (v1.1)
    # =========================================================================

    def _save_pending_queue(self):
        """Guarda los ítems pendientes en cola al cerrar la app."""
        try:
            import json
            from dataclasses import asdict
            with self._queue_lock:
                items = list(self.queue_items)
            if items:
                QUEUE_FILE.write_text(
                    json.dumps([asdict(i) for i in items],
                               indent=2, ensure_ascii=False),
                    encoding="utf-8"
                )
                self.append_log(f"ℹ Cola guardada: {len(items)} ítem(s) pendiente(s)")
            else:
                # Si la cola está vacía, limpiar el archivo
                if QUEUE_FILE.exists():
                    QUEUE_FILE.unlink()
        except Exception as ex:
            self.append_log(f"⚠ No se pudo guardar la cola: {ex}")

    def _restore_pending_queue(self):
        """Restaura ítems pendientes de la sesión anterior al iniciar."""
        if not QUEUE_FILE.exists():
            return
        try:
            import json
            raw = json.loads(QUEUE_FILE.read_text(encoding="utf-8"))
            items = [QueueItem(**i) for i in raw]
            if not items:
                return
            with self._queue_lock:
                for item in items:
                    self.download_queue.put(item)
                    self.queue_items.append(item)
            self.refresh_queue_view()
            self.append_log(f"✓ Cola restaurada: {len(items)} ítem(s) de sesión anterior")
            self.set_status("listo", f"Cola restaurada: {len(items)} ítem(s) pendiente(s)")
            # Limpiar archivo — ya los tenemos en memoria
            QUEUE_FILE.unlink()
        except Exception as ex:
            self.append_log(f"⚠ No se pudo restaurar la cola: {ex}")

    # =========================================================================
    # Construcción UI
    # =========================================================================

    def _build_ui(self):
        self.configure(fg_color=_BG_APP)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ════════════════════════════════════════════════════════════════════
        # SIDEBAR IZQUIERDO
        # ════════════════════════════════════════════════════════════════════
        sidebar = ctk.CTkFrame(self, width=190, corner_radius=0,
                               fg_color=_BG_SIDE,
                               border_width=0)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        sidebar.grid_columnconfigure(0, weight=1)
        sidebar.grid_rowconfigure(20, weight=1)  # empuja footer al fondo

        # Logo
        logo_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        logo_frame.grid(row=0, column=0, sticky="ew", padx=14, pady=(20, 6))

        ctk.CTkLabel(
            logo_frame,
            text="⚡ NovaDL",
            font=ctk.CTkFont(family=_MONO, size=20, weight="bold"),
            text_color=_RED,
        ).pack(anchor="w")

        ctk.CTkLabel(
            logo_frame,
            text=f"v{APP_VERSION}",
            font=ctk.CTkFont(family=_MONO, size=10),
            text_color=_TXT_DIM,
        ).pack(anchor="w")

        # Separador rojo
        ctk.CTkFrame(sidebar, height=1, fg_color=_RED, corner_radius=0).grid(
            row=1, column=0, sticky="ew", padx=14, pady=(6, 14)
        )

        # STATUS MONITOR — funcional con psutil
        status_mon = ctk.CTkFrame(sidebar, fg_color="#0a0a0a",
                                  corner_radius=8,
                                  border_width=1, border_color=_BORDER)
        status_mon.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 14))
        status_mon.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            status_mon,
            text="STATUS MONITOR",
            font=ctk.CTkFont(family=_MONO, size=9, weight="bold"),
            text_color=_RED,
        ).grid(row=0, column=0, pady=(10, 6))

        # Grid de métricas 2x2
        metrics_grid = ctk.CTkFrame(status_mon, fg_color="transparent")
        metrics_grid.grid(row=1, column=0, padx=8, pady=(0, 10), sticky="ew")
        metrics_grid.grid_columnconfigure((0, 1), weight=1)

        def _metric_cell(parent, row, col, title):
            cell = ctk.CTkFrame(parent, fg_color="#111111",
                                corner_radius=6, border_width=1, border_color=_BORDER)
            cell.grid(row=row, column=col, padx=3, pady=3, sticky="ew")
            ctk.CTkLabel(cell, text=title,
                         font=ctk.CTkFont(family=_MONO, size=7, weight="bold"),
                         text_color=_TXT_DIM).pack(pady=(5, 1))
            val_lbl = ctk.CTkLabel(cell, text="--",
                                   font=ctk.CTkFont(family=_MONO, size=13, weight="bold"),
                                   text_color=_RED)
            val_lbl.pack(pady=(0, 5))
            return val_lbl

        self._mon_cpu  = _metric_cell(metrics_grid, 0, 0, "CPU")
        self._mon_ram  = _metric_cell(metrics_grid, 0, 1, "RAM")
        self._mon_disk = _metric_cell(metrics_grid, 1, 0, "DISCO")
        self._mon_net  = _metric_cell(metrics_grid, 1, 1, "RED")

        # Arrancar el loop de actualización
        self._start_status_monitor()

        # Separador
        ctk.CTkFrame(sidebar, height=1, fg_color=_BORDER, corner_radius=0).grid(
            row=3, column=0, sticky="ew", padx=14, pady=(0, 10)
        )

        # Botones de acción rápida
        for r, (txt, cmd) in enumerate([
            ("⬆  ACTUALIZAR",  self.check_app_update),
            ("☰  HISTORIAL",   lambda: self.tabs.set("Historial")),
        ], start=4):
            ctk.CTkButton(
                sidebar, text=txt,
                command=cmd,
                height=34, width=166,
                font=ctk.CTkFont(family=_MONO, size=11, weight="bold"),
                fg_color="#111111", hover_color="#1a1a1a",
                border_width=1, border_color="#2a2a2a",
                text_color=_TXT_MID, corner_radius=6,
            ).grid(row=r, column=0, padx=12, pady=(0, 6))

        # Separador
        ctk.CTkFrame(sidebar, height=1, fg_color=_BORDER, corner_radius=0).grid(
            row=6, column=0, sticky="ew", padx=14, pady=(4, 10)
        )

        # Módulos / pestañas de navegación
        _tab_map = [
            ("▶  DESCARGAR",    "Descargar"),
            ("♫  HERRAMIENTAS", "Herramientas"),
            ("☰  COLA",        "Cola"),
            ("◷  HISTORIAL",   "Historial"),
            ("✕  ERRORES",     "Errores"),
            ("ℹ  ACERCA DE",   "Acerca de"),
        ]

        for r, (label, tab_name) in enumerate(_tab_map, start=7):
            ctk.CTkButton(
                sidebar, text=label,
                command=lambda t=tab_name: self.tabs.set(t),
                height=32, width=166,
                font=ctk.CTkFont(family=_MONO, size=11),
                fg_color="transparent", hover_color=_RED_DIM,
                border_width=0,
                text_color=_TXT_MID, corner_radius=4,
                anchor="w",
            ).grid(row=r, column=0, padx=12, pady=(0, 2))

        # Footer sidebar
        ctk.CTkLabel(
            sidebar,
            text="BY  DARK-CODE",
            font=ctk.CTkFont(family=_MONO, size=8, weight="bold"),
            text_color="#2a2a2a",
        ).grid(row=20, column=0, padx=14, pady=(0, 14), sticky="sw")

        # ════════════════════════════════════════════════════════════════════
        # CONTENIDO PRINCIPAL — CTkTabview sin pestañas visibles
        # ════════════════════════════════════════════════════════════════════
        self.tabs = ctk.CTkTabview(
            self,
            fg_color=_BG_APP,
            border_width=0,
        )
        self.tabs.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)

        tab_download  = self.tabs.add("Descargar")
        tab_queue     = self.tabs.add("Cola")
        tab_history   = self.tabs.add("Historial")
        tab_errors    = self.tabs.add("Errores")
        tab_tools     = self.tabs.add("Herramientas")
        tab_about     = self.tabs.add("Acerca de")

        # Forzar fondo negro Nexus en todas las pestañas
        for _tab in [tab_download, tab_queue, tab_history,
                     tab_errors, tab_tools, tab_about]:
            _tab.configure(fg_color=_BG_APP)

        # Ocultar barra de pestañas DESPUÉS de todos los .add()
        # ya que cada .add() puede recrear el segmented button
        try:
            self.tabs._segmented_button.configure(height=0)
            self.tabs._segmented_button.grid_remove()
        except Exception:
            pass

        # Segundo intento con after() por si CTk lo restaura durante el layout
        self.after(50, self._hide_tab_bar)

        dl = build_download_tab(tab_download, self)
        self.url_entry            = dl["url_entry"]
        self.thumb_label          = dl["thumb_label"]
        self.placeholder_thumbnail = dl["placeholder_thumbnail"]
        self.format_combo         = dl["format_combo"]
        self.audio_quality_label  = dl["audio_quality_label"]
        self.audio_quality_combo  = dl["audio_quality_combo"]
        self.video_quality_label  = dl["video_quality_label"]
        self.video_quality_combo  = dl["video_quality_combo"]
        self.rate_limit_combo     = dl["rate_limit_combo"]
        self.progress             = dl["progress"]
        self.status_badge         = dl["status_badge"]
        self.playlist_info_label  = dl["playlist_info_label"]
        self.download_now_btn     = dl["download_now_btn"]
        self._mode_inner          = dl.get("mode_inner")
        self._mode_label          = dl.get("mode_label")
        self._mode_widgets        = dl.get("mode_widgets_ordered", [])

        q = build_queue_tab(tab_queue, self)
        self.queue_listbox = q["queue_listbox"]

        h = build_history_tab(tab_history, self)
        self.history_listbox      = h["history_listbox"]
        self.history_search_var   = h.get("history_search_var")
        self.history_result_label = h.get("history_result_label")

        e = build_errors_tab(tab_errors, self)
        self.error_listbox = e["error_listbox"]

        t = build_tools_tab(tab_tools, self)
        self.log_box = t["log_box"]

        build_about_tab(tab_about, self)

        # Forzar colores Nexus — CustomTkinter puede sobreescribirlos con el tema
        self.after(10, lambda: (
            self.configure(fg_color=_BG_APP),
            sidebar.configure(fg_color=_BG_SIDE),
            self.tabs.configure(fg_color=_BG_APP),
        ))

    def _hide_tab_bar(self):
        """Oculta la barra de pestañas del CTkTabview — la navegación va por el sidebar."""
        try:
            sb = self.tabs._segmented_button
            sb.configure(height=0, fg_color=_BG_APP,
                         unselected_color=_BG_APP,
                         selected_color=_BG_APP,
                         text_color=_BG_APP,
                         text_color_disabled=_BG_APP)
            sb.grid_remove()
        except Exception:
            pass

    def _start_status_monitor(self):
        """Inicia el loop de actualización del STATUS MONITOR cada 2 segundos."""
        try:
            import psutil
            self._psutil_available = True
        except ImportError:
            self._psutil_available = False
            # Sin psutil — mostrar N/A en todas las métricas
            for lbl in [self._mon_cpu, self._mon_ram,
                        self._mon_disk, self._mon_net]:
                lbl.configure(text="N/A", text_color=_TXT_DIM)
            return

        self._prev_net_bytes = None
        self._update_status_monitor()

    def _update_status_monitor(self):
        """Actualiza las métricas del STATUS MONITOR. Se llama cada 2s via after()."""
        try:
            import psutil

            # — CPU —
            cpu = psutil.cpu_percent(interval=None)
            cpu_color = "#e63333" if cpu > 80 else "#00cc44" if cpu < 50 else "#cc8800"
            self._mon_cpu.configure(text=f"{cpu:.0f}%", text_color=cpu_color)

            # — RAM —
            ram = psutil.virtual_memory().percent
            ram_color = "#e63333" if ram > 85 else "#00cc44" if ram < 60 else "#cc8800"
            self._mon_ram.configure(text=f"{ram:.0f}%", text_color=ram_color)

            # — Disco libre —
            disk = psutil.disk_usage("/")
            free_gb = disk.free / (1024 ** 3)
            disk_color = "#e63333" if free_gb < 2 else "#00cc44" if free_gb > 10 else "#cc8800"
            self._mon_disk.configure(
                text=f"{free_gb:.1f}G",
                text_color=disk_color,
            )

            # — Red activa/inactiva —
            net = psutil.net_io_counters()
            cur_bytes = net.bytes_sent + net.bytes_recv
            if self._prev_net_bytes is None:
                net_active = False
            else:
                net_active = (cur_bytes - self._prev_net_bytes) > 1024
            self._prev_net_bytes = cur_bytes
            net_color = "#00cc44" if net_active else _TXT_DIM
            net_text  = "ON" if net_active else "OFF"
            self._mon_net.configure(text=net_text, text_color=net_color)

        except Exception:
            pass

        # Reprogramar en 2 segundos
        self.after(2000, self._update_status_monitor)

    # =========================================================================
    # Status visual
    # =========================================================================

    def set_status(self, key: str, detail: str):
        color = STATUS_COLORS.get(key.lower(), STATUS_COLORS["listo"])
        self.status_var.set(key.capitalize())
        self.status_detail_var.set(detail)
        self.status_badge.configure(fg_color=color)

    def set_status_visual(self, title: str, detail: str, color: str):
        self.status_var.set(title)
        self.status_detail_var.set(detail)
        self.status_badge.configure(fg_color=color)

    # =========================================================================
    # Log  (auto-limpiar al superar MAX_LOG_LINES)
    # =========================================================================

    def append_log(self, text: str):
        self.log_queue.put(text.rstrip() + "\n")

    def _process_log_queue(self):
        lines = []
        while not self.log_queue.empty():
            try:
                lines.append(self.log_queue.get_nowait())
            except queue.Empty:
                break

        if lines:
            self.log_box.configure(state="normal")
            self.log_box.insert("end", "".join(lines))
            self._log_line_count += len(lines)

            if self._log_line_count > MAX_LOG_LINES:
                all_text = self.log_box.get("1.0", "end")
                kept = all_text.splitlines()[-LOG_TRIM_LINES:]
                self.log_box.delete("1.0", "end")
                self.log_box.insert("1.0", "— log recortado automáticamente —\n" + "\n".join(kept) + "\n")
                self._log_line_count = LOG_TRIM_LINES + 1

            self.log_box.see("end")
            self.log_box.configure(state="disabled")

        self.after(120, self._process_log_queue)

    def clear_log(self):
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")
        self._log_line_count = 0

    # =========================================================================
    # Formato
    # =========================================================================

    def on_format_change(self, _value=None):
        self.update_format_ui()
        self.save_settings()

    def update_format_ui(self):
        """
        Alterna calidad audio/video usando la lista ordenada _mode_widgets.
        Cada entrada es (widget, padx, solo_audio, solo_video).
        """
        if not self._mode_widgets:
            return

        fmt        = self.format_var.get().upper()
        audio_mode = fmt in AUDIO_FORMATS

        for widget, padx, only_audio, only_video in self._mode_widgets:
            widget.pack_forget()

        for widget, padx, only_audio, only_video in self._mode_widgets:
            if only_audio and not audio_mode:
                continue
            if only_video and audio_mode:
                continue
            widget.pack(side="left", padx=padx)

    # =========================================================================
    # Plantilla de nombre  (v0.6.4)
    # =========================================================================

    def on_template_preset_change(self, value: str):
        """Cuando el usuario elige un preset, actualiza el campo de plantilla."""
        tpl = OUTPUT_TEMPLATES.get(value, "")
        if value != "Personalizado…":
            self.output_template_var.set(tpl)
        self.save_settings()

    def _get_output_template(self) -> str:
        tpl = self.output_template_var.get().strip()
        return tpl if tpl else OUTPUT_TEMPLATE_DEFAULT

    # =========================================================================
    # Progreso individual
    # =========================================================================

    def apply_progress(self, data: dict):
        if not data:
            return
        if "percent" in data:
            self.progress.set(data["percent"])
        if "percent_label" in data:
            self.progress_label_var.set(data["percent_label"])
        if "size" in data:
            self.size_var.set(data["size"])
        if "speed" in data:
            self.speed_var.set(data["speed"])
        if "eta" in data:
            self.eta_var.set(data["eta"])
        if data.get("nudge"):
            current = self.progress.get()
            if current < 0.97:
                self.progress.set(min(current + 0.03, 0.97))

        status = data.get("status")
        if status == "descargando":
            self.set_status("descargando", "Procesando descarga actual")
        elif status == "reintentando":
            self.set_status("reintentando", f"Intento {data.get('attempt', 2)}")
        elif status == "completado":
            self.set_status("completado", "Descarga completada correctamente")
        elif status == "cancelado":
            self.set_status("cancelado", "La descarga fue cancelada")

    def reset_transfer_stats(self):
        self.progress.set(0)
        self.progress_label_var.set("0%")
        self.speed_var.set("Velocidad: -")
        self.size_var.set("Tamaño: -")
        self.eta_var.set("ETA: -")

    # =========================================================================
    # Progreso global de cola
    # =========================================================================

    def _start_global_progress(self, total: int):
        self._global_total = total
        self._global_done  = 0
        self._update_global_label()

    def _tick_global_progress(self):
        # BUG 6 FIX: _global_done accedido desde múltiples workers — usar lock
        with self._workers_lock:
            self._global_done += 1
        self._update_global_label()

    def _update_global_label(self):
        if self._global_total > 1:
            self.global_progress_var.set(f"Cola: {self._global_done}/{self._global_total}")
        else:
            self.global_progress_var.set("")

    def _reset_global_progress(self):
        self._global_total = 0
        self._global_done  = 0
        self.global_progress_var.set("")

    # =========================================================================
    # Contadores
    # =========================================================================

    def update_counters(self):
        with self._queue_lock:
            q_len = len(self.queue_items)
        with self._workers_lock:
            active = self._active_workers
        self.queue_count_var.set(f"En cola: {q_len}")
        self.downloading_count_var.set(f"Descargando: {active}")
        self.completed_count_var.set(f"Completadas: {self.completed_count}")

    # =========================================================================
    # Configuración
    # =========================================================================

    def save_settings(self):
        geom = self.geometry()
        try:
            if os.name == "nt" and self.state() == "zoomed":
                geom = DEFAULT_WINDOW_GEOMETRY
        except Exception:
            pass
        Settings.save({
            "format_type":            self.format_var.get(),
            "download_playlist":      self.playlist_var.get(),
            "output_dir":             self.output_var.get(),
            "add_thumbnail":          self.thumb_var.get(),
            "audio_quality":          self.audio_quality_var.get(),
            "video_quality":          self.video_quality_var.get(),
            "rate_limit":             self.rate_limit_var.get(),
            "window_geometry":        geom,
            "completed_count":        self.completed_count,
            "cookies_path":           self.cookies_var.get(),
            "cookies_browser":        self.cookies_browser_var.get(),
            "notifications":          self.notify_var.get(),
            # v0.6.4
            "output_template_preset": self.output_template_preset_var.get(),
            "output_template":        self.output_template_var.get(),
            "retry_count":            self._get_retry_count(),
            "parallel_downloads":     self._get_parallel_count(),
            # v1.1
            "auto_subfolders":        self.auto_subfolders_var.get(),
            # v1.2
            "proxy":                  self.proxy_var.get(),
            "subtitle_lang":          self.subtitle_var.get(),
            "theme":                  self.theme_var.get(),
        })

    def _get_retry_count(self) -> int:
        try:
            return max(0, int(self.retry_count_var.get()))
        except ValueError:
            return AUTO_RETRY_COUNT

    def _get_parallel_count(self) -> int:
        try:
            return max(1, min(MAX_PARALLEL_DOWNLOADS, int(self.parallel_var.get())))
        except ValueError:
            return 1

    # =========================================================================
    # URL helpers
    # =========================================================================

    def get_url_text(self) -> str:
        return self.url_entry.get("1.0", "end").strip()

    def set_url_text(self, value: str):
        self.url_entry.delete("1.0", "end")
        self.url_entry.insert("1.0", value)

    def _get_lines_from_url_box(self) -> list[str]:
        return [x.strip() for x in self.get_url_text().splitlines() if x.strip()]

    # =========================================================================
    # Validación de URL
    # =========================================================================

    def _validate_urls(self, urls: list[str]) -> tuple[list[str], list[str]]:
        valid   = [u for u in urls if _is_valid_url(u)]
        invalid = [u for u in urls if not _is_valid_url(u)]
        return valid, invalid

    def _check_and_warn_invalid_urls(self, urls: list[str]) -> list[str]:
        valid, invalid = self._validate_urls(urls)
        for u in invalid:
            self.append_log(f"⚠ URL inválida descartada: {u}")
        if invalid:
            self.set_status("error", f"{len(invalid)} URL(s) inválida(s) descartadas")
        return valid

    # =========================================================================
    # Carpeta destino
    # =========================================================================

    def pick_folder(self):
        folder = filedialog.askdirectory(initialdir=self.output_var.get() or str(DOWNLOAD_DIR))
        if folder:
            self.output_var.set(folder)
            self.save_settings()

    def open_output(self):
        path = self.output_var.get().strip() or str(DOWNLOAD_DIR)
        os.makedirs(path, exist_ok=True)
        _open_folder(path)

    # =========================================================================
    # Cookies
    # =========================================================================

    def pick_cookies_file(self):
        path = filedialog.askopenfilename(
            title="Selecciona archivo de cookies",
            filetypes=[("Netscape cookies", "*.txt"), ("Todos", "*.*")]
        )
        if path:
            self.cookies_var.set(path)
            self.cookies_browser_var.set("Ninguno")
            self.append_log(f"✓ Cookies cargadas desde archivo: {path}")
            self.save_settings()

    def _get_cookies_args(self) -> list[str]:
        browser = self.cookies_browser_var.get()
        file    = self.cookies_var.get().strip()
        if browser and browser != "Ninguno":
            return ["--cookies-from-browser", browser.lower()]
        if file and os.path.isfile(file):
            return ["--cookies", file]
        return []

    # =========================================================================
    # Miniatura
    # =========================================================================

    def set_thumbnail_from_url(self, image_url: str):
        img = load_thumbnail_from_url(image_url)
        if img is None:
            self.thumb_label.configure(image=self.placeholder_thumbnail, text="")
        else:
            ctk_img = make_ctk_thumbnail(img)
            self.thumb_label.configure(image=ctk_img, text="")
            self._current_thumbnail = ctk_img  # evitar GC

    # =========================================================================
    # Drag & drop / importar TXT
    # =========================================================================

    def on_drop(self, event):
        try:
            data = event.data.strip()
            if not data:
                return
            items = self.tk.splitlist(data)
            urls_to_add = []
            for item in items:
                p = item.strip("{}")
                if p.lower().endswith(".txt") and os.path.exists(p):
                    try:
                        text = Path(p).read_text(encoding="utf-8", errors="ignore")
                        urls_to_add.extend([x.strip() for x in text.splitlines() if x.strip()])
                    except Exception as ex:
                        self.append_log(f"✗ Error leyendo TXT arrastrado: {ex}")
                else:
                    urls_to_add.append(p)

            urls_to_add = self._check_and_warn_invalid_urls(urls_to_add)
            current = self.get_url_text()
            merged = "\n".join(x for x in [current, *urls_to_add] if x)
            self.set_url_text(merged)
            self.append_log(f"✓ Drag & drop: {len(urls_to_add)} elemento(s) añadido(s)")
            self.set_status("listo", f"Drag & drop añadió {len(urls_to_add)} elemento(s)")
        except Exception as ex:
            self.append_log(f"✗ Error en drag & drop: {ex}")

    def import_txt_links(self):
        path = filedialog.askopenfilename(
            title="Selecciona un archivo TXT",
            filetypes=[("Archivos de texto", "*.txt"), ("Todos los archivos", "*.*")]
        )
        if not path:
            return
        try:
            text = Path(path).read_text(encoding="utf-8", errors="ignore")
            links = [x.strip() for x in text.splitlines() if x.strip()]
            links = self._check_and_warn_invalid_urls(links)
            if not links:
                self.append_log("✗ El archivo TXT no contiene URLs válidas")
                self.set_status("error", "TXT sin URLs válidas")
                return
            current = self.get_url_text()
            merged = "\n".join(x for x in [current, *links] if x)
            self.set_url_text(merged)
            self.append_log(f"✓ Importados {len(links)} enlace(s) desde TXT")
            self.set_status("listo", f"Importados {len(links)} enlace(s)")
        except Exception as ex:
            self.append_log(f"✗ Error al importar TXT: {ex}")
            self.set_status("error", "No se pudo importar el TXT")

    # =========================================================================
    # Escanear URL
    # =========================================================================

    def scan_url(self):
        lines = self._get_lines_from_url_box()
        if not lines:
            self.append_log("✗ Pega una URL primero")
            self.set_status("error", "No hay URL para escanear")
            return

        valid, invalid = self._validate_urls(lines)
        for u in invalid:
            self.append_log(f"⚠ URL inválida: {u}")
        if not valid:
            self.set_status("error", "La URL no parece válida")
            return

        url = valid[0]
        self.title_var.set("Escaneando...")
        self.channel_var.set("-")
        self.duration_var.set("-")
        self.playlist_info_var.set("Analizando enlace...")
        self.playlist_info_label.configure(text_color="#c9d4e4")
        self.thumb_label.configure(image=self.placeholder_thumbnail)
        self.set_status("escaneando", "Obteniendo información del enlace")

        def worker():
            try:
                cmd = [get_yt_dlp_cmd(), "--dump-single-json", "--no-warnings"]
                cmd += self._get_cookies_args()
                cmd += [url]
                proc = safe_popen(cmd)
                out, _ = proc.communicate()

                if proc.returncode != 0:
                    raise RuntimeError(out.strip() or "No se pudo escanear la URL")

                info           = json.loads(out)
                title          = info.get("title", "Sin título")
                uploader       = info.get("uploader", "-")
                duration       = info.get("duration_string") or str(info.get("duration", "-"))
                thumb          = info.get("thumbnail", "")
                playlist_count = info.get("playlist_count")

                # v1.1 — datos extra para vista previa enriquecida
                view_count    = info.get("view_count")
                upload_date   = info.get("upload_date", "")   # "20240315"
                formats       = info.get("formats", [])

                # Formatear vistas
                views_str = "-"
                if view_count is not None:
                    if view_count >= 1_000_000:
                        views_str = f"{view_count / 1_000_000:.1f}M vistas"
                    elif view_count >= 1_000:
                        views_str = f"{view_count // 1_000}K vistas"
                    else:
                        views_str = f"{view_count} vistas"

                # Formatear fecha
                date_str = "-"
                if upload_date and len(upload_date) == 8:
                    date_str = f"{upload_date[6:8]}/{upload_date[4:6]}/{upload_date[:4]}"

                # Resoluciones disponibles únicas
                heights = sorted({
                    f.get("height") for f in formats
                    if f.get("height") and isinstance(f.get("height"), int)
                }, reverse=True)
                res_str = "  ".join(f"{h}p" for h in heights[:5]) if heights else "-"

                # Tamaño estimado del mejor formato
                best = max(
                    (f for f in formats if f.get("filesize")),
                    key=lambda f: f.get("filesize", 0),
                    default=None,
                )
                size_str = "-"
                if best and best.get("filesize"):
                    mb = best["filesize"] / (1024 * 1024)
                    size_str = f"~{mb:.0f} MB"

                # BUG 4 FIX: todas las mutaciones de widgets deben ir en hilo principal
                self.after(0, lambda t=title: self.title_var.set(t))
                self.after(0, lambda u=uploader: self.channel_var.set(u))
                self.after(0, lambda d=duration: self.duration_var.set(d))
                self.after(0, lambda th=thumb: self.set_thumbnail_from_url(th))
                self.after(0, lambda v=views_str: self.views_var.set(v))
                self.after(0, lambda d=date_str: self.upload_date_var.set(d))
                self.after(0, lambda r=res_str: self.formats_var.set(r))
                self.after(0, lambda s=size_str: self.filesize_var.set(s))
                self.append_log(f"✓ Título: {title}")
                self.append_log(f"✓ Canal: {uploader}")
                self.append_log(f"✓ Duración: {duration}")
                if res_str != "-":
                    self.append_log(f"✓ Resoluciones: {res_str}")
                if views_str != "-":
                    self.append_log(f"✓ Vistas: {views_str}")

                if playlist_count:
                    self.after(0, lambda pc=playlist_count: self.playlist_info_var.set(
                        f"Playlist detectada: {pc} videos"
                    ))
                    self.after(0, lambda: self.playlist_info_label.configure(text_color="#57C17B"))
                    self.append_log(f"✓ Playlist detectada: {playlist_count} videos")
                else:
                    self.after(0, lambda: self.playlist_info_var.set("Contenido individual detectado"))
                    self.after(0, lambda: self.playlist_info_label.configure(text_color="#c9d4e4"))

                if len(lines) > 1:
                    self.append_log(f"ℹ Hay {len(lines)} enlaces. Escaneé solo el primero.")

                self.after(0, lambda: self.set_status("listo", "Escaneo completado"))

            except Exception as ex:
                # BUG 4 FIX: usar after(0) para todas las mutaciones de widgets
                self.after(0, lambda: self.title_var.set("Sin escanear"))
                self.after(0, lambda: self.channel_var.set("-"))
                self.after(0, lambda: self.duration_var.set("-"))
                self.after(0, lambda: self.playlist_info_var.set("No se pudo analizar el enlace"))
                self.after(0, lambda: self.playlist_info_label.configure(text_color="#C74E4E"))
                self.after(0, lambda: self.thumb_label.configure(image=self.placeholder_thumbnail))
                # v1.1 — resetear datos enriquecidos
                self.after(0, lambda: self.views_var.set("-"))
                self.after(0, lambda: self.upload_date_var.set("-"))
                self.after(0, lambda: self.formats_var.set("-"))
                self.after(0, lambda: self.filesize_var.set("-"))
                self.append_log(f"✗ Error al escanear: {ex}")
                self.after(0, lambda: self.set_status("error", "Error al escanear"))

        threading.Thread(target=worker, daemon=True).start()

    # =========================================================================
    # Cola — helpers
    # =========================================================================

    def _make_queue_items_from_ui(self) -> list[QueueItem]:
        urls       = self._get_lines_from_url_box()
        urls       = self._check_and_warn_invalid_urls(urls)
        output_dir = self.output_var.get().strip() or str(DOWNLOAD_DIR)
        fmt        = self.format_var.get().upper()
        quality    = self.audio_quality_var.get() if fmt in AUDIO_FORMATS else self.video_quality_var.get()
        cookies    = self._get_cookies_args()
        tpl        = self._get_output_template()
        proxy      = self.proxy_var.get().strip() or None
        subtitle   = self.subtitle_var.get()

        # v1.1 — carpetas automáticas por formato
        if self.auto_subfolders_var.get():
            subfolder = FORMAT_SUBFOLDERS.get(fmt, "")
            if subfolder:
                output_dir = os.path.join(output_dir, subfolder)
                os.makedirs(output_dir, exist_ok=True)

        return [
            QueueItem(
                url=url, format_type=fmt, output_dir=output_dir,
                add_thumbnail=self.thumb_var.get(), quality=quality,
                download_playlist=self.playlist_var.get(),
                rate_limit=self.rate_limit_var.get(),
                extra_args=cookies,
                output_template=tpl,
                proxy=proxy,
                subtitle_lang=subtitle,
            )
            for url in urls
        ]

    def _selected_line_from(self, textbox: ctk.CTkTextbox) -> str:
        return textbox.get("insert linestart", "insert lineend").strip()

    def _rebuild_queue_from_items(self):
        new_q: queue.Queue[QueueItem] = queue.Queue()
        with self._queue_lock:
            for item in self.queue_items:
                new_q.put(item)
        self.download_queue = new_q
        self.update_counters()

    # =========================================================================
    # Cola — acciones UI
    # =========================================================================

    def refresh_queue_view(self):
        self.queue_listbox.configure(state="normal")
        self.queue_listbox.delete("1.0", "end")
        with self._queue_lock:
            items = list(self.queue_items)
        if not items:
            self.queue_listbox.insert("1.0", "(vacía)\n")
        else:
            for idx, item in enumerate(items, start=1):
                rate = item.rate_limit if item.rate_limit != "Sin límite" else "∞"
                mode = "playlist" if item.download_playlist else "single"
                self.queue_listbox.insert("end", f"{idx}. [{item.format_type} | {mode} | {rate}] {item.url}\n")
        self.queue_listbox.configure(state="disabled")
        self.update_counters()

    def add_to_queue(self):
        items = self._make_queue_items_from_ui()
        if not items:
            self.append_log("✗ Pega una URL válida primero")
            self.set_status("error", "No hay URL válida para agregar")
            return
        os.makedirs(self.output_var.get().strip() or str(DOWNLOAD_DIR), exist_ok=True)
        with self._queue_lock:
            for item in items:
                self.download_queue.put(item)
                self.queue_items.append(item)
        self.refresh_queue_view()
        self.append_log(f"✓ Añadidos a la cola: {len(items)} enlace(s)")
        self.set_status("listo", f"En cola: {len(self.queue_items)}")
        self.save_settings()
        self.tabs.set("Cola")

    def remove_selected_queue_item(self):
        try:
            raw = self._selected_line_from(self.queue_listbox)
            if not raw or raw == "(vacía)":
                self.append_log("✗ No hay un elemento válido seleccionado en la cola")
                return
            idx = int(raw.split(".", 1)[0].strip()) - 1
            with self._queue_lock:
                removed = self.queue_items.pop(idx)
            self._rebuild_queue_from_items()
            self.refresh_queue_view()
            self.append_log(f"✓ Eliminado de la cola: {removed.url}")
        except Exception:
            self.append_log("✗ Selecciona una línea de la cola colocando el cursor sobre ella")

    def clear_queue(self):
        with self._queue_lock:
            self.queue_items.clear()
        self._rebuild_queue_from_items()
        self.refresh_queue_view()
        self.append_log("✓ Cola limpiada")
        self.set_status("listo", "Cola vacía")

    # =========================================================================
    # Historial
    # =========================================================================

    def refresh_history_view(self):
        self.history_listbox.configure(state="normal")
        self.history_listbox.delete("1.0", "end")
        if not self.history_items:
            self.history_listbox.insert("1.0", "(sin historial)\n")
        else:
            for idx, item in enumerate(self.history_items[:MAX_HISTORY_ITEMS], start=1):
                self.history_listbox.insert("end", f"{idx}. [{item.format_type}] {item.url} | {item.output_dir}\n")
        self.history_listbox.configure(state="disabled")

    def add_to_history(self, item: QueueItem):
        self.history_items.insert(0, HistoryItem(
            url=item.url, format_type=item.format_type,
            output_dir=item.output_dir, download_playlist=item.download_playlist,
        ))
        self.history_items = self.history_items[:MAX_HISTORY_ITEMS]
        HistoryStore.save(HISTORY_FILE, self.history_items)
        self.after(0, self.refresh_history_view)

    def clear_history(self):
        self.history_items.clear()
        HistoryStore.save(HISTORY_FILE, self.history_items)
        self.refresh_history_view()
        self.append_log("✓ Historial limpiado")

    # v1.1 — búsqueda en tiempo real
    def filter_history(self, query: str, result_label=None):
        """Filtra el historial por query y actualiza la vista."""
        q = query.strip().lower()
        if not q:
            self.refresh_history_view()
            if result_label:
                result_label.configure(text="")
            return

        matches = [
            item for item in self.history_items
            if q in item.url.lower()
            or q in item.format_type.lower()
            or q in item.output_dir.lower()
        ]

        self.history_listbox.configure(state="normal")
        self.history_listbox.delete("1.0", "end")
        if not matches:
            self.history_listbox.insert("1.0", "(sin resultados)\n")
        else:
            for idx, item in enumerate(matches, start=1):
                self.history_listbox.insert(
                    "end",
                    f"{idx}. [{item.format_type}] {item.url} | {item.output_dir}\n"
                )
        self.history_listbox.configure(state="disabled")

        if result_label:
            result_label.configure(
                text=f"{len(matches)} resultado(s)",
                text_color="#e63333" if not matches else "#00cc44",
            )

    def reuse_history_item(self):
        try:
            raw = self._selected_line_from(self.history_listbox)
            if not raw or raw == "(sin historial)":
                self.append_log("✗ No hay un elemento válido en historial")
                return
            idx = int(raw.split(".", 1)[0].strip()) - 1
            item = self.history_items[idx]
            self.set_url_text(item.url)
            self.output_var.set(item.output_dir)
            self.format_var.set(item.format_type)
            self.playlist_var.set(item.download_playlist)
            self.update_format_ui()
            self.tabs.set("Descargar")
            self.append_log("✓ Enlace reutilizado desde historial")
        except Exception:
            self.append_log("✗ Selecciona una línea del historial colocando el cursor sobre ella")

    def open_history_folder(self):
        try:
            raw = self._selected_line_from(self.history_listbox)
            if not raw or raw == "(sin historial)":
                self.append_log("✗ No hay un elemento válido en historial")
                return
            idx = int(raw.split(".", 1)[0].strip()) - 1
            folder = self.history_items[idx].output_dir
            os.makedirs(folder, exist_ok=True)
            _open_folder(folder)
        except Exception:
            self.append_log("✗ No se pudo abrir la carpeta del historial")

    # =========================================================================
    # Errores
    # =========================================================================

    def refresh_error_history_view(self):
        self.error_listbox.configure(state="normal")
        self.error_listbox.delete("1.0", "end")
        if not self.error_history_items:
            self.error_listbox.insert("1.0", "(sin errores)\n")
        else:
            for idx, item in enumerate(self.error_history_items[:MAX_HISTORY_ITEMS], start=1):
                self.error_listbox.insert(
                    "end",
                    f"{idx}. [{item.format_type}] {item.url} | {item.error_message}\n"
                )
        self.error_listbox.configure(state="disabled")

    def add_to_error_history(self, item: QueueItem, error_message: str):
        self.error_history_items.insert(0, ErrorHistoryItem(
            url=item.url, format_type=item.format_type,
            error_message=error_message[:400],
        ))
        self.error_history_items = self.error_history_items[:MAX_HISTORY_ITEMS]
        HistoryStore.save(ERROR_HISTORY_FILE, self.error_history_items)
        self.after(0, self.refresh_error_history_view)

    def clear_error_history(self):
        self.error_history_items.clear()
        HistoryStore.save(ERROR_HISTORY_FILE, self.error_history_items)
        self.refresh_error_history_view()
        self.append_log("✓ Historial de errores limpiado")

    def retry_error_item(self):
        """
        v0.6.4 — Reencola el ítem seleccionado en la pestaña Errores.
        Preserva formato, carpeta y demás opciones guardadas en ErrorHistoryItem.
        """
        try:
            raw = self._selected_line_from(self.error_listbox)
            if not raw or raw == "(sin errores)":
                self.append_log("✗ No hay un elemento válido seleccionado en errores")
                return
            idx  = int(raw.split(".", 1)[0].strip()) - 1
            err  = self.error_history_items[idx]
            fmt  = err.format_type.upper()
            quality = (
                self.audio_quality_var.get() if fmt in AUDIO_FORMATS
                else self.video_quality_var.get()
            )
            item = QueueItem(
                url=err.url,
                format_type=fmt,
                output_dir=self.output_var.get().strip() or str(DOWNLOAD_DIR),
                add_thumbnail=self.thumb_var.get(),
                quality=quality,
                download_playlist=self.playlist_var.get(),
                rate_limit=self.rate_limit_var.get(),
                extra_args=self._get_cookies_args(),
                output_template=self._get_output_template(),
            )
            with self._queue_lock:
                self.download_queue.put(item)
                self.queue_items.append(item)
            self.refresh_queue_view()
            self.append_log(f"↺ Reintentando: {err.url}")
            self.set_status("listo", "Ítem añadido de nuevo a la cola")

            if not self.is_downloading:
                self._process_queue()
            else:
                self.tabs.set("Cola")

        except Exception as ex:
            self.append_log(f"✗ No se pudo reintentar: {ex}")

    # =========================================================================
    # Descarga
    # =========================================================================

    def start_download(self):
        items = self._make_queue_items_from_ui()
        if not items:
            self.append_log("✗ Pega una URL válida primero")
            self.set_status("error", "No hay URL válida para descargar")
            return
        os.makedirs(self.output_var.get().strip() or str(DOWNLOAD_DIR), exist_ok=True)
        with self._queue_lock:
            for item in items:
                self.download_queue.put(item)
                self.queue_items.append(item)
        self.refresh_queue_view()
        self.save_settings()

        if self.is_downloading:
            self.append_log(f"✓ Añadidos a cola: {len(items)} enlace(s)")
            self.set_status("listo", f"Añadidos {len(items)} enlace(s) a la cola")
            self.tabs.set("Cola")
            return

        self.tabs.set("Descargar")
        self._process_queue()

    def cancel_download(self):
        if not self.is_downloading:
            self.append_log("✗ No hay ninguna descarga activa para cancelar")
            self.set_status("error", "No hay descarga activa")
            return
        # BUG 7 FIX: con paralelas>1 puede haber varios procesos activos.
        # _cancel_requested detiene todos los workers en su próxima comprobación.
        # terminate() mata solo el proceso más reciente — limitación conocida.
        self._cancel_requested = True
        self.append_log("ℹ Cancelando descargas activas...")
        self.set_status("cancelando", "Intentando detener las descargas")
        try:
            if self.current_process is not None:
                self.current_process.terminate()
        except Exception as ex:
            self.append_log(f"✗ Error al cancelar proceso: {ex}")

    # =========================================================================
    # Procesador de cola  (v0.6.4 — paralelo con semáforo)
    # =========================================================================

    def _process_queue(self):
        """
        Dispatcher robusto para descargas secuenciales y paralelas.

        Diseño:
        - Un dispatcher central saca ítems de download_queue uno a uno.
        - Por cada ítem lanza un worker thread independiente.
        - Un semáforo limita cuántos workers corren a la vez.
        - Cuando todos terminan, limpia el estado global.
        """
        # BUG 8 FIX: guarda contra doble llamada (ej. doble clic en "Descargar")
        if self.is_downloading:
            return

        parallel = self._get_parallel_count()

        with self._queue_lock:
            total = len(self.queue_items)
        if total == 0:
            return

        self.is_downloading = True
        self.after(0, lambda t=total: self._start_global_progress(t))
        self.after(0, self.update_counters)

        # Aplicar retry_count desde UI antes de arrancar
        import core.constants as _cc
        _cc.AUTO_RETRY_COUNT = self._get_retry_count()

        # Semáforo que limita workers simultáneos
        sem = threading.Semaphore(parallel)
        # Contador de workers vivos para saber cuándo termina todo
        pending = threading.Semaphore(0)

        def _run_single(item: QueueItem):
            """Worker que descarga exactamente un ítem."""
            sem.acquire()
            try:
                # BUG 9 FIX: quitar por posición (FIFO), no por igualdad de objeto.
                # remove() con dataclasses iguales eliminaría siempre la primera ocurrencia.
                with self._queue_lock:
                    if self.queue_items:
                        self.queue_items.pop(0)
                self.after(0, self.refresh_queue_view)
                self.after(0, self.reset_transfer_stats)
                self.after(0, lambda i=item: (
                    self.set_url_text(i.url),
                    self.format_var.set(i.format_type),
                    self.output_var.set(i.output_dir),
                    self.thumb_var.set(i.add_thumbnail),
                    self.playlist_var.set(i.download_playlist),
                    self.update_format_ui(),
                ))
                self.append_log(f"▶ Iniciando descarga: {item.url}")

                with self._workers_lock:
                    self._active_workers += 1
                self.after(0, self.update_counters)

                try:
                    run_queue_item(
                        item=item,
                        on_log=self.append_log,
                        on_progress=lambda d: self.after(
                            0, lambda data=d: self.apply_progress(data)
                        ),
                        cancel_flag=lambda: self._cancel_requested,
                        set_process=lambda p: setattr(self, "current_process", p),
                    )
                    self._cancel_requested = False
                    # BUG 5 FIX: proteger completed_count con lock (acceso paralelo)
                    with self._workers_lock:
                        self.completed_count += 1
                    self.add_to_history(item)
                    self.after(0, self.update_counters)
                    self.after(0, self._tick_global_progress)
                    if self.notify_var.get():
                        _notify(APP_NAME, f"✓ Completado\n{item.url[:60]}")

                except RuntimeError as ex:
                    self._cancel_requested = False
                    if "cancelada" not in str(ex).lower():
                        self.add_to_error_history(item, str(ex))
                        self.after(0, lambda: self.set_status("error", "Falló la descarga"))
                        if self.notify_var.get():
                            _notify(APP_NAME, f"✗ Error\n{item.url[:60]}")
                    self.append_log(f"✗ {ex}")

                finally:
                    self.download_queue.task_done()
                    with self._workers_lock:
                        self._active_workers -= 1
                    self.append_log(f"ℹ Quedan en cola: {self.download_queue.qsize()}")
                    self.after(0, self.update_counters)

            finally:
                sem.release()
                pending.release()  # señala al dispatcher que este worker terminó

        def dispatcher():
            """Saca ítems de la cola y lanza un thread por cada uno."""
            launched = 0
            while True:
                try:
                    item = self.download_queue.get_nowait()
                except queue.Empty:
                    break
                threading.Thread(target=_run_single, args=(item,), daemon=True).start()
                launched += 1

            # Esperar a que todos los workers terminen
            for _ in range(launched):
                pending.acquire()

            # Cleanup final — solo cuando TODOS han terminado
            self.is_downloading = False
            self.current_process = None
            self._cancel_requested = False
            self.after(0, lambda: self.set_status("listo", "Cola completada"))
            self.after(0, self._reset_global_progress)
            self.after(0, self.update_counters)
            self.save_settings()

            if self.notify_var.get() and self._global_total > 1:
                _notify(APP_NAME, f"Cola completada: {self._global_done} descarga(s)")

        threading.Thread(target=dispatcher, daemon=True).start()

    # =========================================================================
    # Actualizaciones
    # =========================================================================

    def update_engine(self):
        def worker():
            updater.update_ytdlp(
                on_log=self.append_log,
                on_status=lambda k: self.set_status(k, {
                    "actualizando": "Actualizando yt-dlp",
                    "listo": "yt-dlp actualizado",
                    "error": "Error al actualizar yt-dlp",
                }.get(k, "")),
            )
        threading.Thread(target=worker, daemon=True).start()

    def update_ffmpeg(self):
        def worker():
            updater.update_ffmpeg(
                on_log=self.append_log,
                on_status=lambda k: self.set_status(k, {
                    "actualizando": "Actualizando FFmpeg",
                    "listo": "FFmpeg actualizado",
                    "error": "Error al actualizar FFmpeg",
                }.get(k, "")),
                on_progress=lambda frac, label: self.after(0, lambda f=frac, l=label: (
                    self.progress.set(f),
                    self.progress_label_var.set(l),
                )),
            )
        threading.Thread(target=worker, daemon=True).start()

    def check_app_update(self):
        """
        Busca actualizaciones y muestra ventanas emergentes estilo Nexus:
        - Si hay update: pregunta si actualizar, luego muestra "Actualizando... Reiniciando"
        - Si no hay update: informa que tiene la última versión
        - Si hay error: lo reporta en ventana emergente
        """
        def worker():
            self.append_log("ℹ Buscando actualizaciones...")
            self.after(0, lambda: self.set_status("buscando", "Comprobando nueva versión"))

            # Llamar al updater con callbacks que devuelven info al hilo principal
            result = {"status": None, "message": ""}

            def on_status(k):
                result["status"] = k
                self.after(0, lambda kk=k: self.set_status(kk, {
                    "buscando":     "Comprobando nueva versión",
                    "actualizando": "Descargando nueva versión",
                    "actualizado":  "Reiniciando aplicación...",
                    "listo":        "Ya tienes la última versión",
                    "error":        "Error al actualizar app",
                }.get(kk, "")))

            def on_show_dialog(title, msg):
                result["message"] = msg
                # No mostrar el diálogo por defecto — lo manejamos nosotros

            try:
                updater.check_app_update(
                    on_log=self.append_log,
                    on_status=on_status,
                    on_progress=lambda frac, label: self.after(0, lambda f=frac, l=label: (
                        self.progress.set(f),
                        self.progress_label_var.set(l),
                    )),
                    on_show_dialog=on_show_dialog,
                )
            except Exception as ex:
                self.append_log(f"✗ Error al buscar update: {ex}")
                self.after(0, lambda: self._show_update_dialog("error", str(ex)))
                return

            status = result["status"]
            if status == "listo":
                self.after(0, lambda: self._show_update_dialog("uptodate", result["message"]))
            elif status == "actualizado":
                self.after(0, lambda: self._show_update_dialog("restarting", result["message"]))
            elif status == "error":
                self.after(0, lambda: self._show_update_dialog("error", result["message"]))

        threading.Thread(target=worker, daemon=True).start()

    def _show_update_dialog(self, kind: str, message: str = ""):
        """Muestra ventana emergente estilo Nexus según el tipo de resultado."""
        import tkinter as tk

        win = ctk.CTkToplevel(self)
        win.grab_set()
        win.resizable(False, False)
        win.configure(fg_color="#080808")
        win.overrideredirect(False)

        # Centrar sobre la ventana principal
        self.update_idletasks()
        x = self.winfo_x() + self.winfo_width() // 2 - 220
        y = self.winfo_y() + self.winfo_height() // 2 - 120
        win.geometry(f"440x240+{x}+{y}")

        configs = {
            "found": {
                "title":    "///  ACTUALIZACIÓN DISPONIBLE",
                "icon":     "⚡",
                "body":     "Se encontró una nueva versión disponible.\n¿Deseas actualizarla ahora?",
                "color":    "#e63333",
                "buttons":  True,
            },
            "uptodate": {
                "title":    "///  SIN ACTUALIZACIONES",
                "icon":     "✓",
                "body":     "Ya tienes la última versión de NovaDL.\nNo se encontraron actualizaciones.",
                "color":    "#00cc44",
                "buttons":  False,
            },
            "updating": {
                "title":    "///  ACTUALIZANDO APLICACIÓN",
                "icon":     "⟳",
                "body":     "Descargando nueva versión...\nReiniciando NovaDL automáticamente.",
                "color":    "#e63333",
                "buttons":  False,
            },
            "restarting": {
                "title":    "///  ACTUALIZACIÓN COMPLETADA",
                "icon":     "⚡",
                "body":     "Actualización completada.\nReiniciando NovaDL...",
                "color":    "#e63333",
                "buttons":  False,
            },
            "error": {
                "title":    "///  ERROR",
                "icon":     "✕",
                "body":     message or "No se pudo verificar la actualización.",
                "color":    "#888888",
                "buttons":  False,
            },
        }

        # Si el updater encontró una nueva versión el mensaje lo indica
        if kind == "listo" and ("nueva" in message.lower() or "update" in message.lower()):
            kind = "found"
        cfg = configs.get(kind, configs["error"])

        # Header
        header = ctk.CTkFrame(win, fg_color="#0d0d0d",
                              corner_radius=0,
                              border_width=0)
        header.pack(fill="x")
        ctk.CTkFrame(header, height=2, fg_color=cfg["color"], corner_radius=0).pack(fill="x")

        ctk.CTkLabel(
            header,
            text=cfg["title"],
            font=ctk.CTkFont(family="Courier New", size=11, weight="bold"),
            text_color=cfg["color"],
        ).pack(anchor="w", padx=16, pady=(10, 8))

        # Cuerpo
        body_frame = ctk.CTkFrame(win, fg_color="transparent")
        body_frame.pack(fill="both", expand=True, padx=20, pady=10)

        ctk.CTkLabel(
            body_frame,
            text=cfg["icon"],
            font=ctk.CTkFont(size=36),
            text_color=cfg["color"],
        ).pack(side="left", padx=(0, 20))

        ctk.CTkLabel(
            body_frame,
            text=cfg["body"],
            font=ctk.CTkFont(family="Courier New", size=12),
            text_color="#aaaaaa",
            justify="left",
        ).pack(side="left", anchor="w")

        # Botones
        btn_frame = ctk.CTkFrame(win, fg_color="#0d0d0d", corner_radius=0)
        btn_frame.pack(fill="x", padx=20, pady=(0, 16))

        if cfg["buttons"]:
            # Preguntar si actualizar
            def do_update():
                win.destroy()
                self._show_update_dialog("updating")
                def run_update():
                    try:
                        updater.check_app_update(
                            on_log=self.append_log,
                            on_status=lambda k: self.after(0, lambda kk=k: self.set_status(kk, "")),
                            on_progress=lambda frac, label: self.after(0, lambda f=frac, l=label: (
                                self.progress.set(f),
                                self.progress_label_var.set(l),
                            )),
                            on_show_dialog=lambda t, m: None,
                        )
                    except Exception:
                        pass
                    # Reiniciar app
                    self.after(1500, self._restart_app)
                threading.Thread(target=run_update, daemon=True).start()

            ctk.CTkButton(
                btn_frame, text="ACTUALIZAR AHORA",
                command=do_update,
                width=180, height=36,
                font=ctk.CTkFont(family="Courier New", size=11, weight="bold"),
                fg_color="#e63333", hover_color="#cc0000",
                text_color="#ffffff", corner_radius=6,
            ).pack(side="left", padx=(0, 10))

            ctk.CTkButton(
                btn_frame, text="CANCELAR",
                command=win.destroy,
                width=120, height=36,
                font=ctk.CTkFont(family="Courier New", size=11, weight="bold"),
                fg_color="#111111", hover_color="#1a1a1a",
                border_width=1, border_color="#333333",
                text_color="#555555", corner_radius=6,
            ).pack(side="left")
        else:
            close_text = "CERRAR" if kind != "restarting" else "CERRANDO..."
            close_btn = ctk.CTkButton(
                btn_frame, text=close_text,
                command=win.destroy,
                width=120, height=36,
                font=ctk.CTkFont(family="Courier New", size=11, weight="bold"),
                fg_color="#111111", hover_color="#1a1a1a",
                border_width=1, border_color="#333333",
                text_color="#555555", corner_radius=6,
            )
            close_btn.pack(side="left")

            if kind == "restarting":
                self.after(2000, self._restart_app)

        win.title("")
        win.lift()
        win.focus_force()

    def _restart_app(self):
        """Reinicia la aplicación ejecutando de nuevo el proceso actual."""
        import sys, subprocess
        self.save_settings()
        try:
            subprocess.Popen([sys.executable] + sys.argv)
        except Exception as ex:
            self.append_log(f"✗ No se pudo reiniciar: {ex}")
        finally:
            self.destroy()

    # =========================================================================
    # Tema claro / oscuro  (v1.2)
    # =========================================================================

    def toggle_theme(self):
        """Alterna entre tema oscuro y claro y lo persiste."""
        current = self.theme_var.get()
        new_theme = "light" if current == "dark" else "dark"
        self.theme_var.set(new_theme)
        ctk.set_appearance_mode(new_theme)
        self.save_settings()
        self.append_log(f"✓ Tema cambiado a: {new_theme}")

    # =========================================================================
    # Programador de descargas  (v1.2)
    # =========================================================================

    def open_scheduler(self):
        """Abre la ventana emergente Nexus para programar una descarga."""
        win = ctk.CTkToplevel(self)
        win.grab_set()
        win.resizable(False, False)
        win.configure(fg_color="#080808")
        win.title("")

        self.update_idletasks()
        x = self.winfo_x() + self.winfo_width() // 2 - 240
        y = self.winfo_y() + self.winfo_height() // 2 - 160
        win.geometry(f"480x320+{x}+{y}")

        # Header
        hdr = ctk.CTkFrame(win, fg_color="#0d0d0d", corner_radius=0)
        hdr.pack(fill="x")
        ctk.CTkFrame(hdr, height=2, fg_color=_RED, corner_radius=0).pack(fill="x")
        ctk.CTkLabel(
            hdr, text="///  PROGRAMADOR DE DESCARGAS",
            font=ctk.CTkFont(family=_MONO, size=11, weight="bold"),
            text_color=_RED,
        ).pack(anchor="w", padx=16, pady=(10, 8))

        # Cuerpo
        body = ctk.CTkFrame(win, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=24, pady=10)

        ctk.CTkLabel(
            body,
            text="Iniciar la descarga automáticamente a una hora específica.\n"
                 "Las URLs y configuración actuales se usarán al ejecutar.",
            font=ctk.CTkFont(family=_MONO, size=11),
            text_color="#888888", justify="left",
        ).pack(anchor="w", pady=(0, 16))

        # Selector de hora
        time_row = ctk.CTkFrame(body, fg_color="transparent")
        time_row.pack(anchor="w")

        ctk.CTkLabel(time_row, text="HORA:",
                     font=ctk.CTkFont(family=_MONO, size=11, weight="bold"),
                     text_color=_RED).pack(side="left", padx=(0, 12))

        hour_var = ctk.StringVar(value="00")
        min_var  = ctk.StringVar(value="00")

        hours = [f"{h:02d}" for h in range(24)]
        mins  = [f"{m:02d}" for m in range(0, 60, 5)]

        ctk.CTkComboBox(
            time_row, variable=hour_var, values=hours,
            width=70, height=32,
            font=ctk.CTkFont(family=_MONO, size=13),
            fg_color="#0a0a0a", border_color="#1e1e1e",
            button_color=_RED, dropdown_fg_color="#0d0d0d",
            text_color="#ffffff",
        ).pack(side="left")

        ctk.CTkLabel(time_row, text=":",
                     font=ctk.CTkFont(family=_MONO, size=18, weight="bold"),
                     text_color="#ffffff").pack(side="left", padx=6)

        ctk.CTkComboBox(
            time_row, variable=min_var, values=mins,
            width=70, height=32,
            font=ctk.CTkFont(family=_MONO, size=13),
            fg_color="#0a0a0a", border_color="#1e1e1e",
            button_color=_RED, dropdown_fg_color="#0d0d0d",
            text_color="#ffffff",
        ).pack(side="left")

        # Estado del programador actual
        status_lbl = ctk.CTkLabel(
            body, text="",
            font=ctk.CTkFont(family=_MONO, size=10),
            text_color="#888888",
        )
        status_lbl.pack(anchor="w", pady=(12, 0))

        if self._scheduler_timer is not None:
            status_lbl.configure(
                text="⏱ Hay una descarga programada activa.",
                text_color="#e63333",
            )

        # Botones
        btn_row = ctk.CTkFrame(win, fg_color="#0d0d0d", corner_radius=0)
        btn_row.pack(fill="x", padx=24, pady=(0, 16))

        def _schedule():
            try:
                import datetime
                now   = datetime.datetime.now()
                h, m  = int(hour_var.get()), int(min_var.get())
                target = now.replace(hour=h, minute=m, second=0, microsecond=0)
                if target <= now:
                    target += datetime.timedelta(days=1)
                delay = (target - now).total_seconds()

                # Cancelar timer anterior si existe
                if self._scheduler_timer is not None:
                    self._scheduler_timer.cancel()

                self._scheduler_timer = threading.Timer(delay, self._run_scheduled)
                self._scheduler_timer.daemon = True
                self._scheduler_timer.start()
                self.scheduler_active_var.set(True)

                time_str = target.strftime("%H:%M")
                mins_left = int(delay // 60)
                self.append_log(f"⏱ Descarga programada para las {time_str} (en {mins_left} min)")
                self.set_status("listo", f"Descarga programada: {time_str}")
                win.destroy()
            except Exception as ex:
                self.append_log(f"✗ Error al programar: {ex}")

        def _cancel_schedule():
            if self._scheduler_timer is not None:
                self._scheduler_timer.cancel()
                self._scheduler_timer = None
                self.scheduler_active_var.set(False)
                self.append_log("✓ Programación cancelada")
                self.set_status("listo", "Programación cancelada")
            win.destroy()

        ctk.CTkButton(
            btn_row, text="PROGRAMAR",
            command=_schedule,
            width=160, height=36,
            font=ctk.CTkFont(family=_MONO, size=11, weight="bold"),
            fg_color=_RED, hover_color="#cc0000",
            text_color="#ffffff", corner_radius=0,
        ).pack(side="left", padx=(0, 8), pady=8)

        ctk.CTkButton(
            btn_row, text="CANCELAR PROGRAMACIÓN",
            command=_cancel_schedule,
            width=200, height=36,
            font=ctk.CTkFont(family=_MONO, size=11, weight="bold"),
            fg_color="#1a1a1a", hover_color="#222222",
            border_width=1, border_color="#333333",
            text_color="#555555", corner_radius=0,
        ).pack(side="left", pady=8)

        win.lift()
        win.focus_force()

    def _run_scheduled(self):
        """Ejecutado por el Timer — arranca la descarga desde el hilo correcto."""
        self._scheduler_timer = None
        self.scheduler_active_var.set(False)
        self.append_log("⏱ Ejecutando descarga programada...")
        self.after(0, self.start_download)


# =============================================================================
# Entry point
# =============================================================================

if __name__ == "__main__":
    app = App()
    app.mainloop()
