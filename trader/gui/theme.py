from __future__ import annotations

import tkinter as tk
from tkinter import ttk

WINDOW_BG = "#eef3f8"
SURFACE = "#ffffff"
SURFACE_ALT = "#f7f9fc"
SURFACE_MUTED = "#edf2f7"
BORDER = "#d7e1ec"
BORDER_STRONG = "#c5d2e1"
TEXT = "#16324f"
TEXT_MUTED = "#667a91"
TEXT_SOFT = "#8a99ad"
PRIMARY = "#0f6fff"
PRIMARY_ACTIVE = "#0a5ad2"
SUCCESS = "#159f6b"
SUCCESS_BG = "#e7f7ef"
DANGER = "#d64545"
DANGER_BG = "#fdecec"
WARNING = "#b7791f"
WARNING_BG = "#fff6e5"
INFO = "#1f7a8c"
INFO_BG = "#e7f5f8"
CHART_GRID = "#d9e3ef"
CHART_UP = "#19a974"
CHART_DOWN = "#e25555"

FONT_FAMILY = "TkDefaultFont"
FONT_UI = (FONT_FAMILY, 10)
FONT_SMALL = (FONT_FAMILY, 9)
FONT_H2 = (FONT_FAMILY, 11, "bold")
FONT_H1 = (FONT_FAMILY, 18, "bold")
FONT_KPI = (FONT_FAMILY, 15, "bold")

OUTER_PAD = 18
CARD_PAD = 16
SECTION_GAP = 14
CONTROL_HEIGHT_PAD = 9


def configure_ttk_styles(root: tk.Misc) -> ttk.Style:
    style = ttk.Style(root)
    style.theme_use("clam")

    style.configure(
        "App.TCombobox",
        fieldbackground=SURFACE_ALT,
        background=SURFACE_ALT,
        foreground=TEXT,
        bordercolor=BORDER,
        lightcolor=BORDER,
        darkcolor=BORDER,
        arrowcolor=TEXT_MUTED,
        relief="flat",
        padding=6,
    )
    style.map(
        "App.TCombobox",
        fieldbackground=[("readonly", SURFACE_ALT), ("disabled", SURFACE_MUTED)],
        foreground=[("disabled", TEXT_SOFT)],
        arrowcolor=[("disabled", TEXT_SOFT)],
    )

    style.configure(
        "App.Horizontal.TSeparator",
        background=BORDER,
    )
    style.configure(
        "App.TNotebook",
        background=WINDOW_BG,
        borderwidth=0,
        tabmargins=(0, 0, 0, 0),
    )
    style.configure(
        "App.TNotebook.Tab",
        background=SURFACE_ALT,
        foreground=TEXT_MUTED,
        padding=(16, 10),
        borderwidth=0,
    )
    style.map(
        "App.TNotebook.Tab",
        background=[("selected", SURFACE)],
        foreground=[("selected", TEXT)],
    )
    return style


def style_card(widget: tk.Widget, *, background: str = SURFACE, border: str = BORDER) -> None:
    widget.configure(bg=background, highlightthickness=1, highlightbackground=border, highlightcolor=border)


def section_title(parent: tk.Widget, title: str, subtitle: str | None = None) -> tk.Frame:
    frame = tk.Frame(parent, bg=parent.cget("bg"))
    tk.Label(frame, text=title, bg=parent.cget("bg"), fg=TEXT, font=FONT_H2).pack(anchor="w")
    if subtitle:
        tk.Label(frame, text=subtitle, bg=parent.cget("bg"), fg=TEXT_MUTED, font=FONT_SMALL).pack(anchor="w", pady=(2, 0))
    return frame


def tag_label(parent: tk.Widget, text: str, *, fg: str, bg: str) -> tk.Label:
    return tk.Label(parent, text=text, bg=bg, fg=fg, font=FONT_SMALL, padx=8, pady=4)


def set_entry_style(widget: tk.Entry | tk.Spinbox) -> None:
    widget.configure(
        bg=SURFACE_ALT,
        fg=TEXT,
        insertbackground=TEXT,
        relief=tk.FLAT,
        highlightthickness=1,
        highlightbackground=BORDER,
        highlightcolor=PRIMARY,
        disabledbackground=SURFACE_MUTED,
        disabledforeground=TEXT_SOFT,
    )


def set_option_style(widget: tk.Widget) -> None:
    widget.configure(
        bg=SURFACE_ALT,
        fg=TEXT,
        activebackground=SURFACE_MUTED,
        activeforeground=TEXT,
        highlightthickness=1,
        highlightbackground=BORDER,
        highlightcolor=PRIMARY,
        bd=0,
        relief=tk.FLAT,
        font=FONT_UI,
    )


def set_radio_style(widget: tk.Radiobutton, *, background: str = SURFACE_ALT) -> None:
    widget.configure(
        bg=background,
        fg=TEXT,
        activebackground=background,
        activeforeground=TEXT,
        selectcolor=SURFACE,
        highlightthickness=0,
        bd=0,
        relief=tk.FLAT,
        font=FONT_UI,
        anchor="w",
    )


def set_button_style(
    button: tk.Button,
    *,
    variant: str = "primary",
) -> None:
    schemes = {
        "primary": (PRIMARY, "#ffffff", PRIMARY_ACTIVE),
        "danger": (DANGER_BG, DANGER, "#f8d9d9"),
        "warning": (WARNING_BG, WARNING, "#fdebc4"),
        "success": (SUCCESS_BG, SUCCESS, "#d5f1e3"),
        "secondary": (SURFACE_ALT, TEXT, SURFACE_MUTED),
    }
    bg, fg, active = schemes[variant]
    button.configure(
        bg=bg,
        fg=fg,
        activebackground=active,
        activeforeground=fg,
        relief=tk.FLAT,
        bd=0,
        highlightthickness=0,
        cursor="hand2",
        font=FONT_UI,
        padx=12,
        pady=CONTROL_HEIGHT_PAD,
        disabledforeground=TEXT_SOFT,
    )
