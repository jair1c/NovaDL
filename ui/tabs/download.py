import os
import customtkinter as ctk

try:
    from tkinterdnd2 import DND_FILES
    HAS_DND = True
except Exception:
    HAS_DND = False

from core.constants import AUDIO_FORMATS, DOWNLOAD_DIR
from ui.widgets import make_placeholder_thumbnail, make_ctk_thumbnail

# ── Paleta Nexus ─────────────────────────────────────────────────────────────
_RED      = "#e63333"
_RED_DIM  = "#2a0a0a"
_BG_APP   = "#080808"
_BG_PANEL = "#0d0d0d"
_BG_INNER = "#111111"
_BG_INPUT = "#0a0a0a"
_BORDER   = "#1e1e1e"
_TXT_DIM  = "#555555"
_TXT_MID  = "#888888"
_TXT_MAIN = "#ffffff"
_MONO     = "Courier New"


def _panel(parent, hi_border=False, **kw):
    return ctk.CTkFrame(
        parent, corner_radius=0,
        fg_color=_BG_PANEL,
        border_width=1,
        border_color=_RED if hi_border else _BORDER,
        **kw,
    )


def _label(parent, text, size=10, color=_TXT_DIM, weight="normal", **kw):
    return ctk.CTkLabel(
        parent, text=text,
        font=ctk.CTkFont(family=_MONO, size=size, weight=weight),
        text_color=color, **kw,
    )


def _section(parent, text):
    return _label(parent, f"///  {text}", size=9, color=_RED, weight="bold")


def _combo(parent, variable, values, command=None, width=150):
    return ctk.CTkComboBox(
        parent, variable=variable, values=values,
        command=command or (lambda _=None: None),
        height=30, width=width,
        font=ctk.CTkFont(family=_MONO, size=11),
        fg_color=_BG_INPUT, border_color="#2a2a2a",
        button_color=_RED, button_hover_color=_RED_DIM,
        dropdown_fg_color=_BG_PANEL,
        text_color=_TXT_MAIN,
    )


def _switch(parent, text, variable, save_fn):
    f = ctk.CTkFrame(parent, fg_color="transparent")
    ctk.CTkSwitch(
        f, text="", variable=variable, command=save_fn,
        width=36, height=18,
        progress_color=_RED, button_color=_TXT_MAIN,
        button_hover_color="#dddddd", fg_color="#1e1e1e",
    ).pack(side="left")
    _label(f, text, size=10, color=_TXT_MID).pack(side="left", padx=(5, 0))
    return f


def build_download_tab(tab: ctk.CTkFrame, app) -> dict:
    tab.configure(fg_color=_BG_APP)
    tab.grid_columnconfigure(0, weight=1)
    tab.grid_rowconfigure(0, weight=0)

    refs = {}

    # ════════════════════════════════════════════════════════════════════════
    # BLOQUE 1 — URL + VISTA PREVIA  (igual que Nexus: grande y prominente)
    # ════════════════════════════════════════════════════════════════════════
    top = ctk.CTkFrame(tab, fg_color="transparent")
    top.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 0))
    top.grid_columnconfigure(0, weight=1)

    # — URL —
    url_panel = _panel(top, hi_border=False)
    url_panel.grid(row=0, column=0, sticky="ew", padx=(0, 8))
    url_panel.grid_columnconfigure(0, weight=1)

    _section(url_panel, "ENLACES DE ENTRADA").grid(
        row=0, column=0, padx=14, pady=(10, 6), sticky="w")

    url_entry = ctk.CTkTextbox(
        url_panel, height=120,
        font=ctk.CTkFont(family=_MONO, size=11),
        fg_color=_BG_INPUT,
        border_width=2, border_color=_RED,
        text_color=_TXT_MAIN,
        scrollbar_button_color=_RED,
    )
    url_entry.grid(row=1, column=0, padx=12, pady=(0, 12), sticky="ew")
    refs["url_entry"] = url_entry

    if HAS_DND:
        try:
            url_entry.drop_target_register(DND_FILES)
            url_entry.dnd_bind("<<Drop>>", app.on_drop)
        except Exception:
            pass

    # — Vista previa —
    prev_panel = _panel(top, hi_border=True)
    prev_panel.grid(row=0, column=1, sticky="nsew")
    prev_panel.configure(width=260)
    prev_panel.grid_propagate(False)
    prev_panel.grid_columnconfigure(0, weight=1)

    _section(prev_panel, "VISTA PREVIA").grid(
        row=0, column=0, padx=14, pady=(10, 6), sticky="w")

    thumb_box = ctk.CTkFrame(
        prev_panel, width=230, height=120,
        corner_radius=0, fg_color=_BG_INPUT,
        border_width=0,
    )
    thumb_box.grid(row=1, column=0, padx=14, pady=(0, 8))
    thumb_box.grid_propagate(False)

    placeholder = make_ctk_thumbnail(None)
    thumb_label = ctk.CTkLabel(
        thumb_box, text="", image=placeholder,
        fg_color=_BG_INPUT,
    )
    thumb_label.place(relx=0.5, rely=0.5, anchor="center")
    refs["thumb_label"] = thumb_label
    refs["placeholder_thumbnail"] = placeholder

    ctk.CTkButton(
        prev_panel, text="▶  VISTA PREVIA",
        command=app.scan_url,
        height=28, width=230,
        font=ctk.CTkFont(family=_MONO, size=11, weight="bold"),
        fg_color=_BG_INNER, hover_color="#1a1a1a",
        border_width=1, border_color="#333333",
        text_color=_TXT_MID, corner_radius=0,
    ).grid(row=2, column=0, padx=14, pady=(0, 12))

    # ════════════════════════════════════════════════════════════════════════
    # BLOQUE 2 — MODO + TOGGLES + ESCANEAR  (barra compacta como Nexus)
    # ════════════════════════════════════════════════════════════════════════
    mode_bar = _panel(tab)
    mode_bar.grid(row=1, column=0, sticky="ew", padx=10, pady=(8, 0))
    mode_bar.grid_columnconfigure(0, weight=1)

    inner = ctk.CTkFrame(mode_bar, fg_color="transparent")
    inner.grid(row=0, column=0, sticky="ew", padx=12, pady=10)

    _lbl_modo = _label(inner, "MODO:", size=10, color=_TXT_DIM, weight="bold")
    _lbl_modo.pack(side="left", padx=(0, 8))
    _lbl_modo._pack_padx = (0, 8)
    refs["mode_label"] = _lbl_modo

    fmt_combo = _combo(inner, app.format_var,
                       ["MP3", "M4A", "WAV", "FLAC", "MP4", "MKV"],
                       command=app.on_format_change, width=160)
    fmt_combo.pack(side="left", padx=(0, 20))
    fmt_combo._pack_padx = (0, 20)
    refs["format_combo"] = fmt_combo

    aq_label = _label(inner, "CALIDAD:", size=10, color=_TXT_DIM)
    aq_label._pack_padx = (0, 8)
    refs["audio_quality_label"] = aq_label
    aq_combo = _combo(inner, app.audio_quality_var,
                      ["Mejor calidad", "320K", "192K", "128K"], width=130,
                      command=lambda _=None: app.save_settings())
    aq_combo._pack_padx = (0, 20)
    aq_combo.pack(side="left", padx=(0, 20))
    refs["audio_quality_combo"] = aq_combo

    vq_label = _label(inner, "CALIDAD:", size=10, color=_TXT_DIM)
    vq_label._pack_padx = (0, 8)
    refs["video_quality_label"] = vq_label
    vq_combo = _combo(inner, app.video_quality_var,
                      ["Mejor calidad", "2160p", "1440p", "1080p", "720p", "480p", "360p"],
                      width=130, command=lambda _=None: app.save_settings())
    vq_combo._pack_padx = (0, 20)
    refs["video_quality_combo"] = vq_combo

    # Guardar referencia al inner para que update_format_ui pueda reordenar
    refs["mode_inner"] = inner

    vel_lbl = _label(inner, "VEL:", size=10, color=_TXT_DIM)
    vel_lbl.pack(side="left", padx=(0, 8))
    vel_lbl._pack_padx = (0, 8)

    rl_combo = _combo(inner, app.rate_limit_var,
                      ["Sin límite", "5 MB/s", "2 MB/s", "1 MB/s", "500 KB/s", "250 KB/s"],
                      width=110, command=lambda _=None: app.save_settings())
    rl_combo.pack(side="left", padx=(0, 24))
    rl_combo._pack_padx = (0, 24)
    refs["rate_limit_combo"] = rl_combo

    sw_portada   = _switch(inner, "PORTADA",  app.thumb_var,    app.save_settings)
    sw_portada.pack(side="left", padx=(0, 16))
    sw_playlist  = _switch(inner, "PLAYLIST", app.playlist_var, app.save_settings)
    sw_playlist.pack(side="left", padx=(0, 16))
    sw_notif     = _switch(inner, "NOTIF.",   app.notify_var,   app.save_settings)
    sw_notif.pack(side="left", padx=(0, 24))

    btn_txt = ctk.CTkButton(
        inner, text="IMPORTAR TXT",
        command=app.import_txt_links,
        height=28, width=110,
        font=ctk.CTkFont(family=_MONO, size=10, weight="bold"),
        fg_color=_BG_INNER, hover_color="#1a1a1a",
        border_width=1, border_color=_RED,
        text_color=_TXT_MAIN, corner_radius=4,
    )
    btn_txt.pack(side="left", padx=(0, 6))

    btn_scan = ctk.CTkButton(
        inner, text="[ ESCANEAR ]",
        command=app.scan_url,
        height=28, width=110,
        font=ctk.CTkFont(family=_MONO, size=10, weight="bold"),
        fg_color=_BG_INNER, hover_color="#1a1a1a",
        border_width=1, border_color=_RED,
        text_color=_TXT_MAIN, corner_radius=4,
    )
    btn_scan.pack(side="left")

    # Lista ordenada completa para que update_format_ui reconstruya sin adivinar
    # Formato: (widget, padx, es_audio, es_video)
    # es_audio/es_video = True significa que solo aparece en ese modo
    refs["mode_widgets_ordered"] = [
        (_lbl_modo,   (0, 8),  False, False),   # siempre
        (fmt_combo,   (0, 20), False, False),   # siempre
        (aq_label,    (0, 8),  True,  False),   # solo audio
        (aq_combo,    (0, 20), True,  False),   # solo audio
        (vq_label,    (0, 8),  False, True),    # solo video
        (vq_combo,    (0, 20), False, True),    # solo video
        (vel_lbl,     (0, 8),  False, False),   # siempre
        (rl_combo,    (0, 24), False, False),   # siempre
        (sw_portada,  (0, 16), False, False),   # siempre
        (sw_playlist, (0, 16), False, False),   # siempre
        (sw_notif,    (0, 24), False, False),   # siempre
        (btn_txt,     (0, 6),  False, False),   # siempre
        (btn_scan,    (0, 0),  False, False),   # siempre
    ]

    # ════════════════════════════════════════════════════════════════════════
    # BLOQUE 3 — GUARDAR EN + INICIAR DESCARGA  (igual que Nexus)
    # ════════════════════════════════════════════════════════════════════════
    dest_bar = _panel(tab)
    dest_bar.grid(row=2, column=0, sticky="ew", padx=10, pady=(8, 0))
    dest_bar.grid_columnconfigure(0, weight=1)

    dest_inner = ctk.CTkFrame(dest_bar, fg_color="transparent")
    dest_inner.grid(row=0, column=0, sticky="ew", padx=12, pady=10)
    dest_inner.grid_columnconfigure(1, weight=1)

    _label(dest_inner, "GUARDAR EN:", size=10, color=_TXT_DIM, weight="bold").grid(
        row=0, column=0, padx=(0, 10))

    ctk.CTkEntry(
        dest_inner, textvariable=app.output_var,
        height=36,
        font=ctk.CTkFont(family=_MONO, size=11),
        fg_color=_BG_INPUT, border_color="#2a2a2a",
        text_color=_TXT_MID,
    ).grid(row=0, column=1, padx=(0, 8), sticky="ew")

    ctk.CTkButton(
        dest_inner, text="...",
        command=app.pick_folder,
        height=36, width=44,
        font=ctk.CTkFont(family=_MONO, size=12, weight="bold"),
        fg_color=_BG_INNER, hover_color="#1a1a1a",
        border_width=1, border_color="#2a2a2a",
        text_color=_TXT_MID, corner_radius=4,
    ).grid(row=0, column=2, padx=(0, 20))

    # INICIAR DESCARGA — gran bloque rojo igual que Nexus
    dl_btn = ctk.CTkButton(
        dest_inner,
        text="INICIAR DESCARGA",
        command=app.start_download,
        height=46, width=300,
        font=ctk.CTkFont(family=_MONO, size=15, weight="bold"),
        fg_color=_RED, hover_color="#cc0000",
        text_color=_TXT_MAIN, corner_radius=0,
    )
    dl_btn.grid(row=0, column=3, padx=(0, 6))
    refs["download_now_btn"] = dl_btn

    ctk.CTkButton(
        dest_inner, text="X",
        command=app.cancel_download,
        height=46, width=46,
        font=ctk.CTkFont(family=_MONO, size=14, weight="bold"),
        fg_color=_RED, hover_color="#cc0000",
        text_color=_TXT_MAIN, corner_radius=0,
    ).grid(row=0, column=4)

    # ════════════════════════════════════════════════════════════════════════
    # BLOQUE 4 — BARRA INFERIOR: stats + info + badge  (todo inline como Nexus)
    # ════════════════════════════════════════════════════════════════════════
    bottom = ctk.CTkFrame(tab, fg_color="#0a0a0a", corner_radius=0,
                          border_width=1, border_color=_BORDER)
    bottom.grid(row=3, column=0, sticky="ew", padx=10, pady=(8, 10))
    bottom.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

    # Contadores velocidad/restante/progreso/cola/completadas
    for col, (icon, var) in enumerate([
        ("⚡ VELOCIDAD",   app.speed_var),
        ("⏱ RESTANTE",    app.eta_var),
        ("◎ PROGRESO",    app.progress_label_var),
        ("☰ COLA",        app.queue_count_var),
        ("✓ COMPLETADAS", app.completed_count_var),
    ]):
        cell = ctk.CTkFrame(bottom, fg_color="transparent")
        cell.grid(row=0, column=col, padx=4, pady=10, sticky="ew")
        _label(cell, icon, size=8, color=_TXT_DIM).pack()
        ctk.CTkLabel(
            cell, textvariable=var,
            font=ctk.CTkFont(family=_MONO, size=12, weight="bold"),
            text_color=_RED,
        ).pack(pady=(2, 0))

    ctk.CTkButton(
        bottom, text="ABRIR CARPETA",
        command=app.open_output,
        height=30, width=130,
        font=ctk.CTkFont(family=_MONO, size=10, weight="bold"),
        fg_color=_BG_INNER, hover_color="#1a1a1a",
        border_width=1, border_color="#2a2a2a",
        text_color=_TXT_DIM, corner_radius=4,
    ).grid(row=0, column=5, padx=(4, 10), pady=10, sticky="e")
    bottom.grid_columnconfigure(5, weight=0)

    # ════════════════════════════════════════════════════════════════════════
    # BLOQUE 5 — BARRA PROGRESO + INFO INLINE
    # ════════════════════════════════════════════════════════════════════════
    prog_bar = ctk.CTkFrame(tab, fg_color=_BG_PANEL, corner_radius=0,
                            border_width=1, border_color=_BORDER)
    prog_bar.grid(row=4, column=0, sticky="ew", padx=10, pady=(0, 10))
    prog_bar.grid_columnconfigure(1, weight=1)

    # Fila progreso
    prog_inner = ctk.CTkFrame(prog_bar, fg_color="transparent")
    prog_inner.grid(row=0, column=0, columnspan=6, sticky="ew", padx=12, pady=(8, 4))
    prog_inner.grid_columnconfigure(1, weight=1)

    _label(prog_inner, "PROGRESO", size=9, color=_TXT_DIM).grid(row=0, column=0, padx=(0, 10))

    progress = ctk.CTkProgressBar(
        prog_inner, height=8, corner_radius=0,
        fg_color="#1a1a1a", progress_color=_RED,
    )
    progress.grid(row=0, column=1, sticky="ew", padx=(0, 12))
    progress.set(0)
    refs["progress"] = progress

    ctk.CTkLabel(
        prog_inner, textvariable=app.global_progress_var,
        font=ctk.CTkFont(family=_MONO, size=10, weight="bold"),
        text_color=_RED,
    ).grid(row=0, column=2, padx=(0, 16))

    # Badge de estado
    status_badge = ctk.CTkLabel(
        prog_inner, textvariable=app.status_var,
        font=ctk.CTkFont(family=_MONO, size=10, weight="bold"),
        fg_color=_RED, corner_radius=0,
        padx=10, pady=3, text_color=_TXT_MAIN,
    )
    status_badge.grid(row=0, column=3)
    refs["status_badge"] = status_badge

    # Fila info inline — Título | Canal | Duración | Playlist | datos extra
    info_inner = ctk.CTkFrame(prog_bar, fg_color="transparent")
    info_inner.grid(row=1, column=0, columnspan=6, sticky="ew", padx=12, pady=(2, 4))

    for key, var in [
        ("TÍTULO",    app.title_var),
        ("CANAL",     app.channel_var),
        ("DURACIÓN",  app.duration_var),
    ]:
        _label(info_inner, f"{key}:", size=9, color=_RED, weight="bold").pack(side="left", padx=(0, 4))
        ctk.CTkLabel(
            info_inner, textvariable=var,
            font=ctk.CTkFont(family=_MONO, size=9),
            text_color=_TXT_MID,
        ).pack(side="left", padx=(0, 16))

    _label(info_inner, "PLAYLIST:", size=9, color=_RED, weight="bold").pack(side="left", padx=(0, 4))
    playlist_info_label = ctk.CTkLabel(
        info_inner, textvariable=app.playlist_info_var,
        font=ctk.CTkFont(family=_MONO, size=9),
        text_color=_TXT_DIM,
    )
    playlist_info_label.pack(side="left", padx=(0, 16))
    refs["playlist_info_label"] = playlist_info_label

    ctk.CTkLabel(
        info_inner, textvariable=app.status_detail_var,
        font=ctk.CTkFont(family=_MONO, size=9),
        text_color=_TXT_DIM,
    ).pack(side="right")

    # v1.1 — segunda fila: datos enriquecidos
    info_extra = ctk.CTkFrame(prog_bar, fg_color="transparent")
    info_extra.grid(row=2, column=0, columnspan=6, sticky="ew", padx=12, pady=(0, 8))

    for key, var in [
        ("VISTAS",       app.views_var),
        ("FECHA",        app.upload_date_var),
        ("RESOLUCIONES", app.formats_var),
        ("TAMAÑO EST.",  app.filesize_var),
    ]:
        _label(info_extra, f"{key}:", size=9, color=_RED, weight="bold").pack(side="left", padx=(0, 4))
        ctk.CTkLabel(
            info_extra, textvariable=var,
            font=ctk.CTkFont(family=_MONO, size=9),
            text_color=_TXT_DIM,
        ).pack(side="left", padx=(0, 20))

    return refs
