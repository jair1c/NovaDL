import json
import os
import queue
import re
import subprocess
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from shutil import which
from typing import Optional
from urllib.request import urlopen

import customtkinter as ctk
from tkinter import filedialog

APP_NAME = "NovaDL"
APP_VERSION = "0.2.0"
APP_DIR = Path.home() / ".novadl"
BIN_DIR = APP_DIR / "bin"
DOWNLOAD_DIR = Path.home() / "Downloads" / "NovaDL"
SETTINGS_FILE = APP_DIR / "settings.json"
YTDLP_PATH = BIN_DIR / ("yt-dlp.exe" if os.name == "nt" else "yt-dlp")
FFMPEG_PATH = BIN_DIR / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")

APP_DIR.mkdir(parents=True, exist_ok=True)
BIN_DIR.mkdir(parents=True, exist_ok=True)
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


# Puedes publicar la app en tu propio repositorio de GitHub para autoupdate real.
# Ejemplo:
# APP_RELEASES_API = "https://api.github.com/repos/TU_USUARIO/NovaDL/releases/latest"
# APP_EXE_NAME = "NovaDL.exe"
APP_RELEASES_API = ""
APP_EXE_NAME = "NexusMediaLoader.exe"


@dataclass
class DownloadOptions:
    url: str
    mode: str  # mp3 | mp4
    output_dir: str
    add_thumbnail: bool
    audio_quality: str
    video_quality: str


class Settings:
    @staticmethod
    def load() -> dict:
        if SETTINGS_FILE.exists():
            try:
                return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    @staticmethod
    def save(data: dict) -> None:
        SETTINGS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def which_or_none(name: str) -> Optional[str]:
    return which(name)


def get_yt_dlp_cmd() -> str:
    if YTDLP_PATH.exists():
        return str(YTDLP_PATH)
    system = which_or_none("yt-dlp")
    if system:
        return system
    raise FileNotFoundError(
        "No se encontró yt-dlp. Coloca yt-dlp.exe en ~/.novadl/bin o agrégalo al PATH."
    )


def get_ffmpeg_cmd() -> str:
    if FFMPEG_PATH.exists():
        return str(FFMPEG_PATH)
    system = which_or_none("ffmpeg")
    if system:
        return system
    raise FileNotFoundError(
        "No se encontró ffmpeg. Coloca ffmpeg.exe en ~/.novadl/bin o agrégalo al PATH."
    )


def safe_popen(args):
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


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} {APP_VERSION}")
        self.geometry("980x700")
        self.minsize(900, 640)

        self.settings = Settings.load()
        self.log_queue: queue.Queue[str] = queue.Queue()

        self.url_var = ctk.StringVar()
        self.mode_var = ctk.StringVar(value=self.settings.get("mode", "mp3"))
        self.output_var = ctk.StringVar(value=self.settings.get("output_dir", str(DOWNLOAD_DIR)))
        self.thumb_var = ctk.BooleanVar(value=self.settings.get("add_thumbnail", True))
        self.audio_quality_var = ctk.StringVar(value=self.settings.get("audio_quality", "0"))
        self.video_quality_var = ctk.StringVar(value=self.settings.get("video_quality", "1080"))
        self.status_var = ctk.StringVar(value="Listo")
        self.title_var = ctk.StringVar(value="Sin escanear")
        self.channel_var = ctk.StringVar(value="-")
        self.duration_var = ctk.StringVar(value="-")
        self.progress_label_var = ctk.StringVar(value="0%")

        self.current_thumbnail = None
        self.is_downloading = False

        self._build_ui()
        self.after(120, self.process_log_queue)

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        top = ctk.CTkFrame(self, corner_radius=16)
        top.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 8))
        top.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(top, text=APP_NAME, font=ctk.CTkFont(size=28, weight="bold")).grid(
            row=0, column=0, padx=16, pady=14, sticky="w"
        )
        ctk.CTkLabel(top, text=f"v{APP_VERSION}", text_color="gray70").grid(
            row=0, column=1, padx=(0, 16), pady=14, sticky="e"
        )

        controls = ctk.CTkFrame(self, corner_radius=16)
        controls.grid(row=1, column=0, sticky="ew", padx=16, pady=8)
        controls.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(controls, text="URL").grid(row=0, column=0, padx=12, pady=(14, 8), sticky="w")
        ctk.CTkEntry(controls, textvariable=self.url_var, height=40, placeholder_text="Pega aquí el enlace...").grid(
            row=0, column=1, columnspan=4, padx=12, pady=(14, 8), sticky="ew"
        )

        ctk.CTkButton(controls, text="Escanear", width=120, command=self.scan_url).grid(
            row=1, column=0, padx=12, pady=8, sticky="w"
        )
        ctk.CTkButton(controls, text="Actualizar yt-dlp", width=150, command=self.update_engine).grid(
            row=1, column=1, padx=12, pady=8, sticky="w"
        )
        ctk.CTkButton(controls, text="Buscar update app", width=150, command=self.check_app_update).grid(
            row=1, column=2, padx=12, pady=8, sticky="w"
        )
        ctk.CTkButton(controls, text="Abrir carpeta", width=120, command=self.open_output).grid(
            row=1, column=3, padx=12, pady=8, sticky="w"
        )

        middle = ctk.CTkFrame(self, corner_radius=16)
        middle.grid(row=2, column=0, sticky="ew", padx=16, pady=8)
        middle.grid_columnconfigure((0, 1, 2, 3), weight=1)

        ctk.CTkSegmentedButton(middle, values=["mp3", "mp4"], variable=self.mode_var, command=lambda _: self.save_settings()).grid(
            row=0, column=0, padx=12, pady=(14, 8), sticky="ew"
        )

        ctk.CTkComboBox(middle, variable=self.audio_quality_var, values=["0", "128K", "192K", "320K"], command=lambda _: self.save_settings()).grid(
            row=0, column=1, padx=12, pady=(14, 8), sticky="ew"
        )
        ctk.CTkComboBox(middle, variable=self.video_quality_var, values=["2160", "1440", "1080", "720", "480", "360"], command=lambda _: self.save_settings()).grid(
            row=0, column=2, padx=12, pady=(14, 8), sticky="ew"
        )
        ctk.CTkCheckBox(middle, text="Portada y metadatos", variable=self.thumb_var, command=self.save_settings).grid(
            row=0, column=3, padx=12, pady=(14, 8), sticky="w"
        )

        ctk.CTkLabel(middle, text="Guardar en").grid(row=1, column=0, padx=12, pady=8, sticky="w")
        ctk.CTkEntry(middle, textvariable=self.output_var, height=36).grid(
            row=1, column=1, columnspan=2, padx=12, pady=8, sticky="ew"
        )
        ctk.CTkButton(middle, text="Elegir", command=self.pick_folder).grid(
            row=1, column=3, padx=12, pady=8, sticky="ew"
        )

        preview = ctk.CTkFrame(self, corner_radius=16)
        preview.grid(row=3, column=0, sticky="nsew", padx=16, pady=8)
        preview.grid_columnconfigure(1, weight=1)
        preview.grid_rowconfigure(1, weight=1)

        thumb_frame = ctk.CTkFrame(preview, width=260, corner_radius=16)
        thumb_frame.grid(row=0, column=0, rowspan=2, padx=16, pady=16, sticky="nsw")
        thumb_frame.grid_propagate(False)
        self.thumb_label = ctk.CTkLabel(thumb_frame, text="Miniatura\nno disponible", justify="center")
        self.thumb_label.place(relx=0.5, rely=0.5, anchor="center")

        info = ctk.CTkFrame(preview, corner_radius=16)
        info.grid(row=0, column=1, padx=(0, 16), pady=(16, 8), sticky="new")
        info.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(info, text="Título:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=12, pady=8, sticky="nw")
        ctk.CTkLabel(info, textvariable=self.title_var, wraplength=520, justify="left").grid(row=0, column=1, padx=12, pady=8, sticky="w")
        ctk.CTkLabel(info, text="Canal:", font=ctk.CTkFont(weight="bold")).grid(row=1, column=0, padx=12, pady=8, sticky="nw")
        ctk.CTkLabel(info, textvariable=self.channel_var, wraplength=520, justify="left").grid(row=1, column=1, padx=12, pady=8, sticky="w")
        ctk.CTkLabel(info, text="Duración:", font=ctk.CTkFont(weight="bold")).grid(row=2, column=0, padx=12, pady=8, sticky="nw")
        ctk.CTkLabel(info, textvariable=self.duration_var).grid(row=2, column=1, padx=12, pady=8, sticky="w")

        progress_box = ctk.CTkFrame(preview, corner_radius=16)
        progress_box.grid(row=1, column=1, padx=(0, 16), pady=(8, 16), sticky="nsew")
        progress_box.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(progress_box, text="Progreso", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, padx=12, pady=(12, 6), sticky="w"
        )
        self.progress = ctk.CTkProgressBar(progress_box, height=18)
        self.progress.grid(row=1, column=0, padx=12, pady=6, sticky="ew")
        self.progress.set(0)
        ctk.CTkLabel(progress_box, textvariable=self.progress_label_var).grid(row=2, column=0, padx=12, pady=(0, 10), sticky="e")

        action_bar = ctk.CTkFrame(self, corner_radius=16)
        action_bar.grid(row=4, column=0, sticky="ew", padx=16, pady=8)
        ctk.CTkButton(action_bar, text="Descargar", height=42, command=self.start_download).pack(side="left", padx=12, pady=12)
        ctk.CTkLabel(action_bar, textvariable=self.status_var).pack(side="right", padx=12)

        log_frame = ctk.CTkFrame(self, corner_radius=16)
        log_frame.grid(row=5, column=0, sticky="nsew", padx=16, pady=(8, 16))
        self.grid_rowconfigure(5, weight=1)

        ctk.CTkLabel(log_frame, text="Registro", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=12, pady=(12, 6))
        self.log_box = ctk.CTkTextbox(log_frame, wrap="word")
        self.log_box.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.log_box.insert("1.0", "Aplicación lista. Usa solo contenido propio o con permiso.\n")
        self.log_box.configure(state="disabled")

    def save_settings(self):
        Settings.save(
            {
                "mode": self.mode_var.get(),
                "output_dir": self.output_var.get(),
                "add_thumbnail": self.thumb_var.get(),
                "audio_quality": self.audio_quality_var.get(),
                "video_quality": self.video_quality_var.get(),
            }
        )

    def append_log(self, text: str):
        self.log_queue.put(text.rstrip() + "\n")

    def process_log_queue(self):
        while not self.log_queue.empty():
            text = self.log_queue.get_nowait()
            self.log_box.configure(state="normal")
            self.log_box.insert("end", text)
            self.log_box.see("end")
            self.log_box.configure(state="disabled")
        self.after(120, self.process_log_queue)

    def set_status(self, text: str):
        self.status_var.set(text)
        self.update_idletasks()

    def set_progress_from_line(self, line: str):
        match = re.search(r"\[download\]\s+(\d+(?:\.\d+)?)%", line)
        if match:
            value = float(match.group(1)) / 100.0
            self.progress.set(value)
            self.progress_label_var.set(f"{match.group(1)}%")
        elif "Destination:" in line or "Merging formats" in line or "Post-process" in line:
            if self.progress.get() < 0.97:
                self.progress.set(min(self.progress.get() + 0.03, 0.97))

    def pick_folder(self):
        folder = filedialog.askdirectory(initialdir=self.output_var.get() or str(DOWNLOAD_DIR))
        if folder:
            self.output_var.set(folder)
            self.save_settings()

    def open_output(self):
        path = self.output_var.get().strip() or str(DOWNLOAD_DIR)
        os.makedirs(path, exist_ok=True)
        if os.name == "nt":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])

    def set_thumbnail_from_url(self, image_url: str):
        if not image_url:
            return
        try:
            with urlopen(image_url, timeout=10) as response:
                data = response.read()
            self.current_thumbnail = ctk.CTkImage(data=data, size=(240, 135))
            self.thumb_label.configure(text="", image=self.current_thumbnail)
        except Exception:
            self.thumb_label.configure(text="Miniatura\nno disponible", image=None)

    def scan_url(self):
        url = self.url_var.get().strip()
        if not url:
            self.append_log("✗ Pega una URL primero")
            return

        def worker():
            try:
                self.set_status("Escaneando...")
                cmd = [get_yt_dlp_cmd(), "--dump-single-json", "--no-warnings", url]
                proc = safe_popen(cmd)
                out, _ = proc.communicate()
                if proc.returncode != 0:
                    raise RuntimeError(out.strip() or "No se pudo escanear la URL")
                info = json.loads(out)
                title = info.get("title", "Sin título")
                uploader = info.get("uploader", "-")
                duration = info.get("duration_string") or str(info.get("duration", "-"))
                thumb = info.get("thumbnail", "")

                self.title_var.set(title)
                self.channel_var.set(uploader)
                self.duration_var.set(duration)
                self.after(0, lambda: self.set_thumbnail_from_url(thumb))

                self.append_log(f"✓ Título: {title}")
                self.append_log(f"✓ Canal: {uploader}")
                self.append_log(f"✓ Duración: {duration}")
                self.set_status("Escaneo completado")
            except Exception as e:
                self.append_log(f"✗ Error al escanear: {e}")
                self.set_status("Error al escanear")

        threading.Thread(target=worker, daemon=True).start()

    def build_download_command(self, opts: DownloadOptions):
        output_template = os.path.join(opts.output_dir, "%(title).180B [%(id)s].%(ext)s")
        cmd = [
            get_yt_dlp_cmd(),
            "--newline",
            "--progress",
            "-P", opts.output_dir,
            "-o", output_template,
            "--ffmpeg-location", str(Path(get_ffmpeg_cmd()).parent),
        ]

        if opts.mode == "mp3":
            cmd += ["-x", "--audio-format", "mp3", "--audio-quality", opts.audio_quality]
            if opts.add_thumbnail:
                cmd += ["--embed-thumbnail", "--add-metadata"]
        else:
            fmt = f"bv*[height<={opts.video_quality}]+ba/b[height<={opts.video_quality}]/b"
            cmd += ["-f", fmt, "--merge-output-format", "mp4"]
            if opts.add_thumbnail:
                cmd += ["--embed-metadata"]

        cmd.append(opts.url)
        return cmd

    def start_download(self):
        if self.is_downloading:
            self.append_log("✗ Ya hay una descarga en progreso")
            return

        url = self.url_var.get().strip()
        output_dir = self.output_var.get().strip() or str(DOWNLOAD_DIR)
        if not url:
            self.append_log("✗ Pega una URL primero")
            return

        os.makedirs(output_dir, exist_ok=True)
        self.save_settings()
        self.progress.set(0)
        self.progress_label_var.set("0%")

        opts = DownloadOptions(
            url=url,
            mode=self.mode_var.get(),
            output_dir=output_dir,
            add_thumbnail=self.thumb_var.get(),
            audio_quality=self.audio_quality_var.get(),
            video_quality=self.video_quality_var.get(),
        )

        def worker():
            self.is_downloading = True
            try:
                self.set_status("Descargando...")
                cmd = self.build_download_command(opts)
                self.append_log("$ " + " ".join(f'"{x}"' if " " in x else x for x in cmd))
                proc = safe_popen(cmd)
                assert proc.stdout is not None
                for line in proc.stdout:
                    self.append_log(line.rstrip())
                    self.set_progress_from_line(line)
                rc = proc.wait()
                if rc == 0:
                    self.progress.set(1)
                    self.progress_label_var.set("100%")
                    self.append_log("✓ Descarga completada")
                    self.set_status("Completado")
                else:
                    self.append_log(f"✗ La descarga terminó con código {rc}")
                    self.set_status("Error en descarga")
            except Exception as e:
                self.append_log(f"✗ Error: {e}")
                self.set_status("Error")
            finally:
                self.is_downloading = False

        threading.Thread(target=worker, daemon=True).start()

    def update_engine(self):
        def worker():
            try:
                self.set_status("Actualizando yt-dlp...")
                proc = safe_popen([get_yt_dlp_cmd(), "-U"])
                assert proc.stdout is not None
                for line in proc.stdout:
                    self.append_log(line.rstrip())
                rc = proc.wait()
                if rc == 0:
                    self.append_log("✓ yt-dlp actualizado")
                    self.set_status("yt-dlp actualizado")
                else:
                    self.append_log(f"✗ No se pudo actualizar yt-dlp (código {rc})")
                    self.set_status("Error al actualizar yt-dlp")
            except Exception as e:
                self.append_log(f"✗ Error al actualizar yt-dlp: {e}")
                self.set_status("Error al actualizar yt-dlp")

        threading.Thread(target=worker, daemon=True).start()

    def check_app_update(self):
        def worker():
            if not APP_RELEASES_API:
                self.append_log("ℹ Configura APP_RELEASES_API para habilitar el autoupdate de tu app")
                self.set_status("Autoupdate app no configurado")
                return

            try:
                self.set_status("Buscando actualización de la app...")
                with urlopen(APP_RELEASES_API, timeout=12) as response:
                    release = json.loads(response.read().decode("utf-8"))

                latest_version = str(release.get("tag_name", "")).lstrip("v")
                if not latest_version:
                    raise RuntimeError("La API no devolvió tag_name")

                if latest_version == APP_VERSION:
                    self.append_log(f"✓ Ya tienes la última versión de la app: {APP_VERSION}")
                    self.set_status("App actualizada")
                    return

                self.append_log(f"✓ Nueva versión detectada: {latest_version}")
                self.append_log("ℹ Puedes automatizar aquí la descarga del .exe nuevo desde assets del release")
                self.set_status("Nueva versión disponible")
            except Exception as e:
                self.append_log(f"✗ Error buscando update app: {e}")
                self.set_status("Error al buscar update app")

        threading.Thread(target=worker, daemon=True).start()


if __name__ == "__main__":
    app = App()
    app.mainloop()
