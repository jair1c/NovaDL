import customtkinter as ctk

_RED      = "#e63333"
_BG_PANEL = "#0d0d0d"
_BG_INNER = "#111111"
_BG_INPUT = "#0a0a0a"
_BORDER   = "#1e1e1e"
_TXT_DIM  = "#555555"
_TXT_MID  = "#aaaaaa"
_TXT_MAIN = "#ffffff"
_MONO     = "Courier New"


def _panel(parent, **kw):
    return ctk.CTkFrame(parent, corner_radius=0,
                        fg_color=_BG_PANEL,
                        border_width=1, border_color=_BORDER, **kw)


def _btn(parent, text, command, width=160, height=34):
    return ctk.CTkButton(
        parent, text=text, command=command,
        width=width, height=height,
        font=ctk.CTkFont(family=_MONO, size=11, weight="bold"),
        fg_color=_BG_INNER, hover_color="#1a1a1a",
        border_width=1, border_color=_RED,
        text_color=_TXT_MAIN, corner_radius=0,
    )


def build_history_tab(tab: ctk.CTkFrame, app) -> dict:
    tab.configure(fg_color="#080808")
    tab.grid_columnconfigure(0, weight=1)
    tab.grid_rowconfigure(2, weight=1)

    # ── Panel acciones ───────────────────────────────────────────────────────
    actions = _panel(tab)
    actions.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))
    actions.grid_columnconfigure(0, weight=1)

    ctk.CTkLabel(
        actions,
        text="///  HISTORIAL DE DESCARGAS",
        font=ctk.CTkFont(family=_MONO, size=9, weight="bold"),
        text_color=_RED,
    ).grid(row=0, column=0, padx=14, pady=(10, 4), sticky="w")

    btn_row = ctk.CTkFrame(actions, fg_color="transparent")
    btn_row.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))

    _btn(btn_row, "REUSAR ENLACE",     app.reuse_history_item,  width=160).pack(side="left", padx=(0, 8))
    _btn(btn_row, "ABRIR CARPETA",     app.open_history_folder, width=160).pack(side="left", padx=(0, 8))
    _btn(btn_row, "LIMPIAR HISTORIAL", app.clear_history,       width=170).pack(side="left")

    # ── Barra de búsqueda ────────────────────────────────────────────────────
    search_panel = _panel(tab)
    search_panel.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 4))
    search_panel.grid_columnconfigure(1, weight=1)

    ctk.CTkLabel(
        search_panel,
        text="///  BUSCAR",
        font=ctk.CTkFont(family=_MONO, size=9, weight="bold"),
        text_color=_RED,
    ).grid(row=0, column=0, padx=14, pady=10)

    search_var = ctk.StringVar()

    search_entry = ctk.CTkEntry(
        search_panel,
        textvariable=search_var,
        placeholder_text="Filtrar por URL, formato o carpeta…",
        height=30,
        font=ctk.CTkFont(family=_MONO, size=11),
        fg_color=_BG_INPUT, border_color=_BORDER,
        text_color=_TXT_MAIN,
    )
    search_entry.grid(row=0, column=1, padx=(0, 8), pady=10, sticky="ew")

    result_label = ctk.CTkLabel(
        search_panel, text="",
        font=ctk.CTkFont(family=_MONO, size=10),
        text_color=_TXT_DIM,
    )
    result_label.grid(row=0, column=2, padx=(0, 8), pady=10)

    ctk.CTkButton(
        search_panel, text="✕",
        command=lambda: search_var.set(""),
        width=30, height=30,
        font=ctk.CTkFont(family=_MONO, size=11),
        fg_color=_BG_INNER, hover_color="#1a1a1a",
        border_width=1, border_color="#2a2a2a",
        text_color=_TXT_DIM, corner_radius=0,
    ).grid(row=0, column=3, padx=(0, 14), pady=10)

    # ── Lista ─────────────────────────────────────────────────────────────────
    frame = _panel(tab)
    frame.grid(row=2, column=0, sticky="nsew", padx=8, pady=(0, 8))
    frame.grid_rowconfigure(0, weight=1)
    frame.grid_columnconfigure(0, weight=1)

    history_listbox = ctk.CTkTextbox(
        frame, wrap="none",
        font=ctk.CTkFont(family=_MONO, size=11),
        fg_color=_BG_INPUT,
        border_width=1, border_color=_BORDER,
        text_color=_TXT_MID,
        scrollbar_button_color=_RED,
    )
    history_listbox.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
    history_listbox.insert("1.0", "(sin historial)\n")
    history_listbox.configure(state="disabled")

    # Búsqueda en tiempo real — delega a app.filter_history()
    search_var.trace_add("write", lambda *_: app.filter_history(
        search_var.get(), result_label
    ))

    return {
        "history_listbox":     history_listbox,
        "history_search_var":  search_var,
        "history_result_label": result_label,
    }
