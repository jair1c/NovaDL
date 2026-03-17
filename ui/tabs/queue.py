import customtkinter as ctk

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


def _panel(parent, **kw):
    return ctk.CTkFrame(parent, corner_radius=10,
                        fg_color=_BG_PANEL,
                        border_width=1, border_color=_BORDER, **kw)


def _btn(parent, text, command, width=160, height=34):
    return ctk.CTkButton(
        parent, text=text, command=command,
        width=width, height=height,
        font=ctk.CTkFont(family=_MONO, size=11, weight="bold"),
        fg_color=_BG_INNER, hover_color="#1a1a1a",
        border_width=1, border_color=_RED,
        text_color=_TXT_MAIN, corner_radius=6,
    )


def build_queue_tab(tab: ctk.CTkFrame, app) -> dict:
    tab.configure(fg_color="#080808")
    tab.grid_columnconfigure(0, weight=1)
    tab.grid_rowconfigure(1, weight=1)

    # ── Acciones ─────────────────────────────────────────────────────────────
    actions = _panel(tab)
    actions.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))

    ctk.CTkLabel(
        actions,
        text="///  COLA DE DESCARGAS",
        font=ctk.CTkFont(family=_MONO, size=9, weight="bold"),
        text_color=_RED,
    ).grid(row=0, column=0, columnspan=10, padx=14, pady=(10, 4), sticky="w")

    btn_row = ctk.CTkFrame(actions, fg_color="transparent")
    btn_row.grid(row=1, column=0, columnspan=10, sticky="ew", padx=10, pady=(0, 10))

    _btn(btn_row, "QUITAR SELECCIONADO", app.remove_selected_queue_item, width=200).pack(
        side="left", padx=(0, 8))
    _btn(btn_row, "LIMPIAR COLA", app.clear_queue, width=150).pack(side="left")

    # ── Lista ─────────────────────────────────────────────────────────────────
    frame = _panel(tab)
    frame.grid(row=1, column=0, sticky="nsew", padx=8, pady=(4, 8))
    frame.grid_rowconfigure(0, weight=1)
    frame.grid_columnconfigure(0, weight=1)

    queue_listbox = ctk.CTkTextbox(
        frame, wrap="none",
        font=ctk.CTkFont(family=_MONO, size=11),
        fg_color=_BG_INPUT,
        border_width=1, border_color=_BORDER,
        text_color=_TXT_MID,
        scrollbar_button_color=_RED,
    )
    queue_listbox.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
    queue_listbox.insert("1.0", "(vacía)\n")
    queue_listbox.configure(state="disabled")

    return {"queue_listbox": queue_listbox}
