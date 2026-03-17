import customtkinter as ctk
import webbrowser
import os
import sys
from pathlib import Path

from core.constants import APP_NAME, APP_VERSION

_RED   = "#e63333"
_MONO  = "Courier New"


def _get_assets_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.join(sys._MEIPASS, "assets")
    return str(Path(__file__).resolve().parent.parent.parent / "assets")


def build_about_tab(tab: ctk.CTkFrame, app) -> dict:
    tab.configure(fg_color="#080808")
    tab.grid_columnconfigure(0, weight=1)
    tab.grid_rowconfigure(0, weight=1)

    center = ctk.CTkFrame(tab, corner_radius=0, fg_color="transparent")
    center.grid(row=0, column=0, sticky="nsew", padx=40, pady=30)
    center.grid_columnconfigure(0, weight=1)

    # ── Hero ─────────────────────────────────────────────────────────────────
    hero = ctk.CTkFrame(center, corner_radius=0, fg_color="#0d0d0d",
                        border_width=1, border_color=_RED)
    hero.grid(row=0, column=0, sticky="ew", pady=(0, 16))
    hero.grid_columnconfigure(0, weight=1)

    ctk.CTkLabel(
        hero,
        text="⚡  NOVADL",
        font=ctk.CTkFont(family=_MONO, size=38, weight="bold"),
        text_color=_RED,
    ).grid(row=0, column=0, padx=30, pady=(24, 4))

    ctk.CTkLabel(
        hero,
        text=f"v{APP_VERSION}  ///  DESCARGADOR MULTIMEDIA AVANZADO",
        font=ctk.CTkFont(family=_MONO, size=12),
        text_color="#555555",
    ).grid(row=1, column=0, padx=30, pady=(0, 6))

    ctk.CTkLabel(
        hero,
        text="Descarga audio y video desde YouTube, SoundCloud, TikTok, Instagram y más.\n"
             "Compatible con playlists, cookies de autenticación, múltiples formatos y descargas paralelas.\n"
             "Construido sobre yt-dlp + FFmpeg.",
        font=ctk.CTkFont(family=_MONO, size=12),
        text_color="#aaaaaa",
        justify="center",
    ).grid(row=2, column=0, padx=30, pady=(0, 24))

    # ── Separador ────────────────────────────────────────────────────────────
    ctk.CTkFrame(center, height=1, fg_color=_RED, corner_radius=0).grid(
        row=1, column=0, sticky="ew", pady=(0, 16))

    # ── Bloque programador ───────────────────────────────────────────────────
    dev = ctk.CTkFrame(center, corner_radius=0, fg_color="#0d0d0d",
                       border_width=1, border_color="#1e1e1e")
    dev.grid(row=2, column=0, sticky="ew", pady=(0, 16))
    dev.grid_columnconfigure(1, weight=1)

    ctk.CTkLabel(
        dev,
        text="///  PROGRAMADOR",
        font=ctk.CTkFont(family=_MONO, size=10, weight="bold"),
        text_color=_RED,
    ).grid(row=0, column=0, columnspan=2, padx=20, pady=(16, 12), sticky="w")

    # ── Avatar — profile.png o fallback iniciales ─────────────────────────
    avatar_frame = ctk.CTkFrame(dev, width=80, height=80, corner_radius=8,
                                fg_color="#1a1a1a",
                                border_width=2, border_color=_RED)
    avatar_frame.grid(row=1, column=0, padx=(20, 16), pady=(0, 20), sticky="nw")
    avatar_frame.grid_propagate(False)

    try:
        from PIL import Image
        _profile_path = os.path.join(_get_assets_dir(), "profile.png")
        _img = Image.open(_profile_path).convert("RGBA").resize((76, 76))
        _ctk_img = ctk.CTkImage(light_image=_img, dark_image=_img, size=(76, 76))
        ctk.CTkLabel(
            avatar_frame, text="", image=_ctk_img,
            fg_color="transparent",
        ).place(relx=0.5, rely=0.5, anchor="center")
        # Guardar referencia para evitar GC
        avatar_frame._profile_img = _ctk_img
    except Exception:
        ctk.CTkLabel(
            avatar_frame, text="GJ",
            font=ctk.CTkFont(family=_MONO, size=26, weight="bold"),
            text_color=_RED,
        ).place(relx=0.5, rely=0.5, anchor="center")

    # ── Info bloque ──────────────────────────────────────────────────────────
    info_block = ctk.CTkFrame(dev, fg_color="transparent")
    info_block.grid(row=1, column=1, padx=(0, 20), pady=(0, 20), sticky="w")

    ctk.CTkLabel(
        info_block,
        text="Gabriel Jair",
        font=ctk.CTkFont(family=_MONO, size=20, weight="bold"),
        text_color="#ffffff",
    ).pack(anchor="w")

    ctk.CTkLabel(
        info_block,
        text="[ DARK-CODE ]",
        font=ctk.CTkFont(family=_MONO, size=14),
        text_color=_RED,
    ).pack(anchor="w", pady=(3, 10))

    ctk.CTkLabel(
        info_block,
        text="Desarrollador independiente  ·  Python / Desktop Apps",
        font=ctk.CTkFont(family=_MONO, size=11),
        text_color="#666666",
    ).pack(anchor="w")

    # ── Separador interno ────────────────────────────────────────────────────
    ctk.CTkFrame(dev, height=1, fg_color="#1e1e1e", corner_radius=0).grid(
        row=2, column=0, columnspan=2, sticky="ew", padx=20, pady=(0, 14))

    # ── Contacto ─────────────────────────────────────────────────────────────
    ctk.CTkLabel(
        dev,
        text="///  CONTACTO",
        font=ctk.CTkFont(family=_MONO, size=10, weight="bold"),
        text_color=_RED,
    ).grid(row=3, column=0, columnspan=2, padx=20, pady=(0, 10), sticky="w")

    ctk.CTkButton(
        dev,
        text="  Instagram  @gabrieljair.gc",
        font=ctk.CTkFont(family=_MONO, size=12),
        fg_color="#1a1a1a", hover_color="#2a0a0a",
        border_width=1, border_color=_RED,
        text_color=_RED,
        height=38, width=290,
        corner_radius=0,
        command=lambda: webbrowser.open("https://instagram.com/gabrieljair.gc"),
    ).grid(row=4, column=0, columnspan=2, padx=20, pady=(0, 20), sticky="w")

    # ── Créditos ─────────────────────────────────────────────────────────────
    footer = ctk.CTkFrame(center, corner_radius=0, fg_color="#0d0d0d",
                          border_width=1, border_color="#1e1e1e")
    footer.grid(row=3, column=0, sticky="ew")
    footer.grid_columnconfigure(0, weight=1)

    ctk.CTkLabel(
        footer,
        text="///  CRÉDITOS  &  LICENCIA",
        font=ctk.CTkFont(family=_MONO, size=10, weight="bold"),
        text_color="#444444",
    ).grid(row=0, column=0, padx=20, pady=(14, 6), sticky="w")

    ctk.CTkLabel(
        footer,
        text="NovaDL es un proyecto personal de código libre.  "
             "Usa solo contenido propio o con permiso del autor.\n"
             "yt-dlp © yt-dlp contributors  ·  FFmpeg © FFmpeg team  ·  CustomTkinter © Tom Schimansky",
        font=ctk.CTkFont(family=_MONO, size=10),
        text_color="#333333",
        justify="left",
    ).grid(row=1, column=0, padx=20, pady=(0, 14), sticky="w")

    return {}

