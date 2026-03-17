import customtkinter as ctk
from core.constants import MAX_PARALLEL_DOWNLOADS, OUTPUT_TEMPLATES, SUBTITLE_LANGS

_RED      = "#e63333"
_RED_DIM  = "#2a0a0a"
_BG_PANEL = "#0d0d0d"
_BG_INNER = "#111111"
_BG_INPUT = "#0a0a0a"
_BORDER   = "#1e1e1e"
_TXT_DIM  = "#555555"
_TXT_MID  = "#aaaaaa"
_TXT_MAIN = "#ffffff"
_MONO     = "Courier New"


def _label(parent, text, size=10, color=_TXT_DIM, weight="normal", **kw):
    return ctk.CTkLabel(
        parent, text=text,
        font=ctk.CTkFont(family=_MONO, size=size, weight=weight),
        text_color=color, **kw,
    )


def _section_header(parent, text, row, col=0, colspan=1):
    _label(parent, f"///  {text}", size=9, color=_RED, weight="bold").grid(
        row=row, column=col, columnspan=colspan,
        padx=14, pady=(10, 4), sticky="w",
    )


def _panel(parent, **kw):
    return ctk.CTkFrame(
        parent, corner_radius=0,
        fg_color=_BG_PANEL,
        border_width=1, border_color=_BORDER,
        **kw,
    )


def _btn(parent, text, command, width=150, height=34,
         fg_color=None, hover_color=None,
         border_width=1, border_color=_RED,
         text_color=_TXT_MAIN, danger=False):
    return ctk.CTkButton(
        parent, text=text, command=command,
        width=width, height=height,
        font=ctk.CTkFont(family=_MONO, size=11, weight="bold"),
        fg_color=fg_color if fg_color is not None else (_RED if danger else _BG_INNER),
        hover_color=hover_color if hover_color is not None else ("#cc0000" if danger else "#1a1a1a"),
        border_width=border_width,
        border_color=border_color,
        text_color=text_color,
        corner_radius=0,
    )


def _combo(parent, variable, values, command=None, width=90):
    return ctk.CTkComboBox(
        parent, variable=variable, values=values,
        command=command or (lambda _=None: None),
        height=30, width=width,
        font=ctk.CTkFont(family=_MONO, size=11),
        fg_color=_BG_INPUT, border_color=_BORDER,
        button_color=_RED, button_hover_color=_RED_DIM,
        dropdown_fg_color=_BG_PANEL,
        text_color=_TXT_MAIN,
    )


def build_tools_tab(tab: ctk.CTkFrame, app) -> dict:
    tab.configure(fg_color="#080808")
    tab.grid_columnconfigure(0, weight=1)
    tab.grid_rowconfigure(5, weight=1)

    # ════════════════════════════════════════════════════════════════════════
    # FILA 0 — Actualizaciones (sin buscar update app — está en sidebar)
    # ════════════════════════════════════════════════════════════════════════
    update_panel = _panel(tab)
    update_panel.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))
    update_panel.grid_columnconfigure(0, weight=1)

    _section_header(update_panel, "ACTUALIZACIONES", row=0, colspan=10)

    upd_row = ctk.CTkFrame(update_panel, fg_color="transparent")
    upd_row.grid(row=1, column=0, columnspan=10, sticky="ew", padx=10, pady=(0, 10))

    _btn(upd_row, "ACTUALIZAR  YT-DLP", app.update_engine, width=180).pack(side="left", padx=(0, 8))
    _btn(upd_row, "ACTUALIZAR  FFMPEG", app.update_ffmpeg, width=180).pack(side="left", padx=(0, 24))

    ctk.CTkFrame(upd_row, width=1, height=30, fg_color="#2a2a2a").pack(side="left", padx=(0, 24))

    _btn(upd_row, "LIMPIAR  LOG", app.clear_log, width=130,
         fg_color="#1a1a1a", hover_color="#222222",
         border_width=1, border_color="#2a2a2a",
         text_color=_TXT_DIM).pack(side="left")

    # ════════════════════════════════════════════════════════════════════════
    # FILA 1 — Configuración de descarga
    # ════════════════════════════════════════════════════════════════════════
    cfg_panel = _panel(tab)
    cfg_panel.grid(row=1, column=0, sticky="ew", padx=8, pady=4)
    cfg_panel.grid_columnconfigure(0, weight=1)

    _section_header(cfg_panel, "CONFIGURACIÓN DE DESCARGA", row=0, colspan=10)

    cfg_row = ctk.CTkFrame(cfg_panel, fg_color="transparent")
    cfg_row.grid(row=1, column=0, columnspan=10, sticky="ew", padx=10, pady=(0, 10))

    _label(cfg_row, "REINTENTOS AUTOMÁTICOS:", size=10, color=_TXT_DIM).pack(side="left", padx=(4, 8))
    _combo(cfg_row, app.retry_count_var, ["0", "1", "2", "3", "5"],
           command=lambda _=None: app.save_settings(), width=80).pack(side="left", padx=(0, 30))

    _label(cfg_row, "DESCARGAS PARALELAS:", size=10, color=_TXT_DIM).pack(side="left", padx=(0, 8))
    _combo(cfg_row, app.parallel_var,
           [str(i) for i in range(1, MAX_PARALLEL_DOWNLOADS + 1)],
           command=lambda _=None: app.save_settings(), width=80).pack(side="left", padx=(0, 30))

    # v1.1 — carpetas automáticas
    ctk.CTkSwitch(
        cfg_row, text="",
        variable=app.auto_subfolders_var,
        command=app.save_settings,
        width=36, height=18,
        progress_color="#e63333",
        button_color="#ffffff",
        button_hover_color="#dddddd",
        fg_color="#1e1e1e",
    ).pack(side="left", padx=(0, 6))
    _label(cfg_row, "CARPETAS POR FORMATO", size=10, color=_TXT_DIM).pack(side="left", padx=(0, 6))
    _label(cfg_row, "(MP3→Música, MP4→Videos)", size=9, color="#3a3a3a").pack(side="left", padx=(0, 20))

    _label(cfg_row, "⚠  Más de 2 paralelas puede causar bloqueos.",
           size=10, color="#3a3a3a").pack(side="left")

    # ════════════════════════════════════════════════════════════════════════
    # FILA 2 — Nombre de archivo (movido desde Descargar)
    # ════════════════════════════════════════════════════════════════════════
    name_panel = _panel(tab)
    name_panel.grid(row=2, column=0, sticky="ew", padx=8, pady=4)
    name_panel.grid_columnconfigure(0, weight=1)

    _section_header(name_panel, "NOMBRE DE ARCHIVO", row=0, colspan=10)

    name_row = ctk.CTkFrame(name_panel, fg_color="transparent")
    name_row.grid(row=1, column=0, columnspan=10, sticky="ew", padx=10, pady=(0, 10))
    name_row.grid_columnconfigure(2, weight=1)

    _label(name_row, "PLANTILLA:", size=10, color=_TXT_DIM).grid(row=0, column=0, padx=(4, 8))

    _combo(name_row, app.output_template_preset_var,
           list(OUTPUT_TEMPLATES.keys()),
           command=app.on_template_preset_change, width=210).grid(row=0, column=1, padx=(0, 10))

    custom_entry = ctk.CTkEntry(
        name_row,
        textvariable=app.output_template_var,
        placeholder_text="%(title)s [%(id)s]  —  variables yt-dlp",
        height=30,
        font=ctk.CTkFont(family=_MONO, size=11),
        fg_color=_BG_INPUT, border_color=_BORDER,
        text_color=_TXT_MAIN,
    )
    custom_entry.grid(row=0, column=2, padx=(0, 10), sticky="ew")
    custom_entry.bind("<FocusOut>", lambda _: app.save_settings())

    _label(name_row, "ext. automática", size=9, color=_TXT_DIM).grid(row=0, column=3, padx=(0, 4))

    # ════════════════════════════════════════════════════════════════════════
    # FILA 3 — Cookies
    # ════════════════════════════════════════════════════════════════════════
    cookies_panel = _panel(tab)
    cookies_panel.grid(row=3, column=0, sticky="ew", padx=8, pady=4)
    cookies_panel.grid_columnconfigure(0, weight=1)

    _section_header(cookies_panel, "COOKIES  /  AUTENTICACIÓN", row=0, colspan=10)

    ck_row = ctk.CTkFrame(cookies_panel, fg_color="transparent")
    ck_row.grid(row=1, column=0, columnspan=10, sticky="ew", padx=10, pady=(0, 10))
    ck_row.grid_columnconfigure(3, weight=1)

    _label(ck_row, "NAVEGADOR:", size=10, color=_TXT_DIM).grid(row=0, column=0, padx=(4, 8))

    ctk.CTkComboBox(
        ck_row,
        variable=app.cookies_browser_var,
        values=["Ninguno", "Chrome", "Firefox", "Edge", "Safari", "Brave", "Opera"],
        command=lambda _=None: (
            app.cookies_var.set("") if app.cookies_browser_var.get() != "Ninguno" else None,
            app.save_settings(),
        ),
        height=30, width=130,
        font=ctk.CTkFont(family=_MONO, size=11),
        fg_color=_BG_INPUT, border_color=_BORDER,
        button_color=_RED, button_hover_color=_RED_DIM,
        dropdown_fg_color=_BG_PANEL,
        text_color=_TXT_MAIN,
    ).grid(row=0, column=1, padx=(0, 22))

    _label(ck_row, "ARCHIVO  COOKIES.TXT:", size=10, color=_TXT_DIM).grid(row=0, column=2, padx=(0, 8))

    ctk.CTkEntry(
        ck_row, textvariable=app.cookies_var,
        placeholder_text="ruta al archivo cookies.txt…",
        height=30,
        font=ctk.CTkFont(family=_MONO, size=11),
        fg_color=_BG_INPUT, border_color=_BORDER,
        text_color=_TXT_MID,
    ).grid(row=0, column=3, padx=(0, 10), sticky="ew")

    _btn(ck_row, "ELEGIR",  app.pick_cookies_file, width=90, height=30).grid(row=0, column=4, padx=(0, 8))
    _btn(ck_row, "LIMPIAR", lambda: (
        app.cookies_var.set(""),
        app.cookies_browser_var.set("Ninguno"),
        app.save_settings(),
        app.append_log("✓ Cookies limpiadas"),
    ), width=90, height=30,
         fg_color="#1a1a1a", hover_color="#222222",
         border_width=1, border_color="#2a2a2a",
         text_color=_TXT_DIM).grid(row=0, column=5, padx=(0, 4))

    # ════════════════════════════════════════════════════════════════════════
    # FILA 4 — Proxy + Subtítulos + Tema + Programador  (v1.2)
    # ════════════════════════════════════════════════════════════════════════
    extra_panel = _panel(tab)
    extra_panel.grid(row=4, column=0, sticky="ew", padx=8, pady=4)
    extra_panel.grid_columnconfigure(0, weight=1)

    _section_header(extra_panel, "DESCARGA AVANZADA  /  APARIENCIA", row=0, colspan=10)

    extra_row = ctk.CTkFrame(extra_panel, fg_color="transparent")
    extra_row.grid(row=1, column=0, columnspan=10, sticky="ew", padx=10, pady=(0, 10))
    extra_row.grid_columnconfigure(1, weight=1)

    # — Proxy —
    _label(extra_row, "PROXY:", size=10, color=_TXT_DIM).grid(row=0, column=0, padx=(4, 8), sticky="w")
    ctk.CTkEntry(
        extra_row, textvariable=app.proxy_var,
        placeholder_text="http://usuario:pass@host:puerto  (vacío = sin proxy)",
        height=30,
        font=ctk.CTkFont(family=_MONO, size=11),
        fg_color=_BG_INPUT, border_color=_BORDER,
        text_color=_TXT_MAIN,
    ).grid(row=0, column=1, padx=(0, 10), sticky="ew")

    _btn(extra_row, "LIMPIAR", lambda: (
        app.proxy_var.set(""),
        app.save_settings(),
        app.append_log("✓ Proxy limpiado"),
    ), width=90, height=30,
         fg_color="#1a1a1a", hover_color="#222222",
         border_width=1, border_color="#2a2a2a",
         text_color=_TXT_DIM).grid(row=0, column=2, padx=(0, 20))

    # — Subtítulos —
    _label(extra_row, "SUBTÍTULOS:", size=10, color=_TXT_DIM).grid(row=0, column=3, padx=(0, 8), sticky="w")
    _combo(extra_row, app.subtitle_var, SUBTITLE_LANGS,
           command=lambda _=None: app.save_settings(), width=90).grid(row=0, column=4, padx=(0, 24))

    # — Tema —
    _label(extra_row, "TEMA:", size=10, color=_TXT_DIM).grid(row=0, column=5, padx=(0, 8), sticky="w")
    _btn(extra_row, "☀  CLARO / OSCURO", app.toggle_theme,
         width=160, height=30).grid(row=0, column=6, padx=(0, 20))

    # — Programador —
    _btn(extra_row, "⏱  PROGRAMAR DESCARGA", app.open_scheduler,
         width=190, height=30, danger=True).grid(row=0, column=7)

    # ════════════════════════════════════════════════════════════════════════
    # FILA 5 — Log terminal (expandible)
    # ════════════════════════════════════════════════════════════════════════
    log_panel = _panel(tab)
    log_panel.grid(row=5, column=0, sticky="nsew", padx=8, pady=(4, 8))
    log_panel.grid_rowconfigure(1, weight=1)
    log_panel.grid_columnconfigure(0, weight=1)

    _section_header(log_panel, "REGISTRO  /  KERNEL OUTPUT", row=0)

    log_box = ctk.CTkTextbox(
        log_panel, wrap="word",
        font=ctk.CTkFont(family=_MONO, size=11),
        fg_color=_BG_INPUT,
        border_width=1, border_color=_BORDER,
        text_color="#00cc44",
        scrollbar_button_color=_RED,
    )
    log_box.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
    log_box.insert("1.0", "KERNEL CARGADO...\nESPERANDO ENTRADA.\n")
    log_box.configure(state="disabled")

    return {"log_box": log_box}
