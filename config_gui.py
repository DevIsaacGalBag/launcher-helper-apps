"""
JARVIS - Panel de configuración
--------------------------------
Interfaz gráfica para elegir qué apps se abren al prender la compu,
qué canción de Spotify se reproduce, y tu nombre para el saludo.

Al presionar "Guardar cambios" se escribe todo en config.json,
que es el archivo que lee jarvis_start.py al arrancar.
"""

import configparser
import glob
import json
import platform
import re
import sys
import tkinter as tk
import tkinter.font as tkfont
from pathlib import Path
from tkinter import filedialog, ttk

import autostart

def _app_base_dir():
    # Empaquetado con PyInstaller (--onefile): __file__ apunta a la carpeta
    # temporal de extracción, que se borra en cada corrida. Usamos la carpeta
    # donde vive el .exe para que config.json persista entre ejecuciones.
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


BASE_DIR = _app_base_dir()
CONFIG_PATH = BASE_DIR / "config.json"
EXAMPLE_CONFIG_PATH = BASE_DIR / "config.example.json"

# Carpetas típicas donde Linux guarda los .desktop de las apps instaladas
# (las mismas que usa el menú/launcher de GNOME, KDE, etc.)
DESKTOP_APP_DIRS = [
    "/usr/share/applications",
    "/usr/local/share/applications",
    "/var/lib/flatpak/exports/share/applications",
    str(Path.home() / ".local/share/applications"),
    str(Path.home() / ".local/share/flatpak/exports/share/applications"),
]

EXEC_PLACEHOLDER_RE = re.compile(r"%[fFuUdDnNickvm]")
SPOTIFY_TRACK_RE = re.compile(r"(?:open\.spotify\.com/(?:intl-\w+/)?track/|spotify:track:)([A-Za-z0-9]+)")


def _truncate(text, max_chars=64):
    return text if len(text) <= max_chars else text[: max_chars - 1].rstrip() + "…"


# ============================================================
#  Paleta / tema visual
# ============================================================
BG = "#0f1115"
CARD_BG = "#181b22"
CARD_BG_ALT = "#1f2330"
BORDER = "#2a2e3a"
TEXT = "#eceef3"
MUTED = "#8a8fa3"
MUTED_DIM = "#5b5f6e"
ACCENT = "#7c6cf6"
ACCENT_HOVER = "#8f81f8"
DANGER = "#f16c6c"
DANGER_HOVER = "#ff8b8b"
SUCCESS = "#5fd68a"
SWITCH_OFF = "#363b48"


def _lighten(hex_color, factor=0.15):
    hex_color = hex_color.lstrip("#")
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    r = min(255, int(r + (255 - r) * factor))
    g = min(255, int(g + (255 - g) * factor))
    b = min(255, int(b + (255 - b) * factor))
    return f"#{r:02x}{g:02x}{b:02x}"


def pick_font_family(root):
    """Elige la mejor fuente disponible en el sistema, con fallback seguro."""
    available = set(tkfont.families(root))
    for candidate in ("Segoe UI Variable", "Segoe UI", "Ubuntu", "Cantarell",
                       "Noto Sans", "Helvetica Neue", "Helvetica", "Arial"):
        if candidate in available:
            return candidate
    return "TkDefaultFont"


def scan_installed_apps():
    """Lee los archivos .desktop del sistema (los mismos que arma el menú de
    aplicaciones de Fedora/GNOME) y devuelve una lista de {name, command}."""
    apps = {}
    for directory in DESKTOP_APP_DIRS:
        for path in glob.glob(f"{directory}/*.desktop"):
            parser = configparser.ConfigParser(interpolation=None, strict=False)
            try:
                parser.read(path, encoding="utf-8")
            except (configparser.Error, UnicodeDecodeError, OSError):
                continue

            if "Desktop Entry" not in parser:
                continue
            entry = parser["Desktop Entry"]

            if entry.get("NoDisplay", "false").lower() == "true":
                continue
            if entry.get("Hidden", "false").lower() == "true":
                continue
            if entry.get("Type", "Application") != "Application":
                continue

            name = entry.get("Name")
            exec_cmd = entry.get("Exec")
            if not name or not exec_cmd:
                continue

            # Sacamos los placeholders (%f, %U, %i, etc.) que solo tienen sentido
            # cuando el launcher abre un archivo puntual con la app.
            clean_exec = EXEC_PLACEHOLDER_RE.sub("", exec_cmd).strip()
            apps[name] = clean_exec

    return sorted(apps.items(), key=lambda item: item[0].lower())


def load_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    if EXAMPLE_CONFIG_PATH.exists():
        with open(EXAMPLE_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"user_name": "", "voice": "es-MX-DaliaNeural", "spotify_track_url": "", "apps": []}


def save_config(config):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


# ============================================================
#  Widgets propios (switch tipo iOS, botón plano con hover)
# ============================================================
class ToggleSwitch(tk.Canvas):
    """Switch tipo iOS/Android, dibujado a mano con Canvas."""

    W, H = 46, 24

    def __init__(self, parent, variable, bg):
        super().__init__(parent, width=self.W, height=self.H,
                          highlightthickness=0, bg=bg, cursor="hand2")
        self.variable = variable
        self.bind("<Button-1>", self._toggle)
        self.variable.trace_add("write", lambda *_: self._draw())
        self._draw()

    def _toggle(self, _event=None):
        self.variable.set(not self.variable.get())

    def _draw(self):
        self.delete("all")
        is_on = self.variable.get()
        color = ACCENT if is_on else SWITCH_OFF
        pad, r = 2, (self.H - 4) / 2
        self.create_oval(pad, pad, pad + 2 * r, pad + 2 * r, fill=color, outline=color)
        self.create_oval(self.W - pad - 2 * r, pad, self.W - pad, pad + 2 * r, fill=color, outline=color)
        self.create_rectangle(pad + r, pad, self.W - pad - r, pad + 2 * r, fill=color, outline=color)
        knob_d = self.H - 6
        knob_x = self.W - 3 - knob_d if is_on else 3
        self.create_oval(knob_x, 3, knob_x + knob_d, 3 + knob_d, fill="#ffffff", outline="#ffffff")


def flat_button(parent, text, command, bg=ACCENT, hover=None, fg="white",
                 font=None, padx=18, pady=10):
    hover = hover or _lighten(bg)
    btn = tk.Button(
        parent, text=text, command=command, bg=bg, fg=fg,
        activebackground=hover, activeforeground=fg, bd=0, relief="flat",
        font=font, cursor="hand2", padx=padx, pady=pady,
    )
    btn.bind("<Enter>", lambda e: btn.config(bg=hover))
    btn.bind("<Leave>", lambda e: btn.config(bg=bg))
    return btn


class _Tooltip:
    """Globito simple que muestra el texto completo al pasar el mouse
    (usado para el comando completo cuando lo truncamos en la lista)."""

    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip = None
        widget.bind("<Enter>", self._show)
        widget.bind("<Leave>", self._hide)

    def _show(self, _event=None):
        if self.tip is not None:
            return
        x = self.widget.winfo_rootx()
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{x}+{y}")
        tk.Label(self.tip, text=self.text, bg=CARD_BG_ALT, fg=TEXT,
                 relief="solid", bd=1, padx=8, pady=4).pack()

    def _hide(self, _event=None):
        if self.tip is not None:
            self.tip.destroy()
            self.tip = None


def style_entry(entry):
    """Resalta el borde del campo de texto cuando tiene foco."""
    entry.bind("<FocusIn>", lambda e: entry.config(highlightbackground=ACCENT, highlightcolor=ACCENT))
    entry.bind("<FocusOut>", lambda e: entry.config(highlightbackground=BORDER, highlightcolor=BORDER))


# ============================================================
#  App principal
# ============================================================
class JarvisConfigApp(tk.Tk):
    VOICES = {
        "Español (México) - Dalia, mujer": "es-MX-DaliaNeural",
        "Español (México) - Jorge, hombre": "es-MX-JorgeNeural",
        "Español (España) - Elvira, mujer": "es-ES-ElviraNeural",
        "Español (España) - Álvaro, hombre": "es-ES-AlvaroNeural",
        "Español (Argentina) - Elena, mujer": "es-AR-ElenaNeural",
        "Español (Argentina) - Tomás, hombre": "es-AR-TomasNeural",
    }

    def __init__(self):
        super().__init__()
        self.title("Jarvis - Panel de configuración")
        self.geometry("640x760")
        self.minsize(580, 540)
        self.configure(bg=BG)

        self.font_family = pick_font_family(self)
        self.f_title = (self.font_family, 22, "bold")
        self.f_subtitle = (self.font_family, 10)
        self.f_section = (self.font_family, 10, "bold")
        self.f_label = (self.font_family, 10)
        self.f_hint = (self.font_family, 8)
        self.f_button = (self.font_family, 11, "bold")

        self._setup_ttk_style()

        self.config_data = load_config()
        self.app_rows = []

        self._build_ui()
        self._populate_apps()

    # ---------- estilos ttk (combobox, scrollbar) ----------
    def _setup_ttk_style(self):
        style = ttk.Style(self)
        style.theme_use("clam")

        style.configure("TCombobox",
                         fieldbackground=CARD_BG_ALT, background=CARD_BG_ALT,
                         foreground=TEXT, arrowcolor=MUTED, bordercolor=BORDER,
                         lightcolor=BORDER, darkcolor=BORDER, padding=6)
        style.map("TCombobox", fieldbackground=[("readonly", CARD_BG_ALT)],
                   foreground=[("readonly", TEXT)])
        self.option_add("*TCombobox*Listbox.background", CARD_BG_ALT)
        self.option_add("*TCombobox*Listbox.foreground", TEXT)
        self.option_add("*TCombobox*Listbox.selectBackground", ACCENT)

        style.configure("Vertical.TScrollbar", background=CARD_BG_ALT,
                         troughcolor=BG, bordercolor=BG, arrowcolor=MUTED)

    # ---------- helpers de layout ----------
    def _card(self, parent, title):
        card = tk.Frame(parent, bg=CARD_BG, highlightbackground=BORDER,
                         highlightthickness=1, bd=0)
        tk.Label(card, text=title, bg=CARD_BG, fg=MUTED, font=self.f_section) \
            .pack(anchor="w", padx=18, pady=(14, 6))
        return card

    def _entry(self, parent, textvariable, width=30):
        entry = tk.Entry(parent, textvariable=textvariable, width=width,
                          bg=CARD_BG_ALT, fg=TEXT, insertbackground=TEXT,
                          relief="flat", bd=0, highlightthickness=1,
                          highlightbackground=BORDER, highlightcolor=BORDER,
                          font=self.f_label)
        style_entry(entry)
        return entry

    # ---------- UI ----------
    def _build_ui(self):
        outer = tk.Frame(self, bg=BG)
        outer.pack(fill="both", expand=True)

        # --- Botón de guardar: fijo abajo, siempre visible ---
        footer = tk.Frame(outer, bg=BG)
        footer.pack(side="bottom", fill="x", padx=20, pady=16)
        save_btn = flat_button(
            footer, "Guardar cambios", self.save,
            bg=ACCENT, hover=ACCENT_HOVER, font=self.f_button, pady=12
        )
        save_btn.pack(fill="x")

        # --- Header ---
        header = tk.Frame(outer, bg=BG)
        header.pack(fill="x", padx=20, pady=(22, 4))
        tk.Label(header, text="JARVIS", bg=BG, fg=TEXT, font=self.f_title).pack(anchor="w")
        tk.Label(header, text="Configurá qué pasa cuando prendés tu compu",
                 bg=BG, fg=MUTED, font=self.f_subtitle).pack(anchor="w", pady=(2, 0))

        # --- Card: General ---
        general = self._card(outer, "GENERAL")
        general.pack(fill="x", padx=20, pady=(14, 10))

        grid = tk.Frame(general, bg=CARD_BG)
        grid.pack(fill="x", padx=18, pady=(0, 16))
        grid.columnconfigure(1, weight=1)

        tk.Label(grid, text="Tu nombre", bg=CARD_BG, fg=MUTED, font=self.f_label) \
            .grid(row=0, column=0, sticky="w", pady=8)
        self.name_var = tk.StringVar(value=self.config_data.get("user_name", ""))
        self._entry(grid, self.name_var, width=26).grid(row=0, column=1, sticky="ew", padx=(12, 0), pady=8)

        tk.Label(grid, text="Voz", bg=CARD_BG, fg=MUTED, font=self.f_label) \
            .grid(row=1, column=0, sticky="w", pady=8)
        current_voice = self.config_data.get("voice", "es-MX-DaliaNeural")
        current_label = next((k for k, v in self.VOICES.items() if v == current_voice),
                              list(self.VOICES.keys())[0])
        self.voice_var = tk.StringVar(value=current_label)
        ttk.Combobox(grid, textvariable=self.voice_var, values=list(self.VOICES.keys()),
                     state="readonly", font=self.f_label) \
            .grid(row=1, column=1, sticky="ew", padx=(12, 0), pady=8)

        tk.Label(grid, text="Canción de Spotify", bg=CARD_BG, fg=MUTED, font=self.f_label) \
            .grid(row=2, column=0, sticky="w", pady=8)
        self.spotify_var = tk.StringVar(value=self.config_data.get("spotify_track_url", ""))
        self._entry(grid, self.spotify_var).grid(row=2, column=1, sticky="ew", padx=(12, 0), pady=(8, 0))

        self.spotify_status_var = tk.StringVar()
        self.spotify_status_label = tk.Label(
            grid, textvariable=self.spotify_status_var, bg=CARD_BG, font=self.f_hint, anchor="w",
        )
        self.spotify_status_label.grid(row=3, column=1, sticky="w", padx=(12, 0), pady=(4, 8))
        self.spotify_var.trace_add("write", lambda *_: self._update_spotify_status())
        self._update_spotify_status()

        tk.Label(grid, text="Iniciar con la compu", bg=CARD_BG, fg=MUTED, font=self.f_label) \
            .grid(row=4, column=0, sticky="w", pady=8)
        self.autostart_var = tk.BooleanVar(value=self._autostart_enabled_safe())
        autostart_row = tk.Frame(grid, bg=CARD_BG)
        autostart_row.grid(row=4, column=1, sticky="w", padx=(12, 0), pady=8)
        ToggleSwitch(autostart_row, self.autostart_var, bg=CARD_BG).pack(side="left")
        tk.Label(autostart_row, text="Se aplica al guardar", bg=CARD_BG, fg=MUTED_DIM, font=self.f_hint) \
            .pack(side="left", padx=(10, 0))

        tk.Label(
            general,
            text="Tip: pegá el link tal cual lo copiás de Spotify (click derecho en la canción \u2192 "
                 "Compartir \u2192 Copiar link de la canción). No hace falta limpiarlo: funciona "
                 "aunque traiga cosas como \u201csi=...\u201d al final.",
            bg=CARD_BG, fg=MUTED_DIM, font=self.f_hint, wraplength=440, justify="left",
        ).pack(anchor="w", padx=18, pady=(0, 14))

        # --- Card: Apps ---
        apps_card = self._card(outer, "APPS QUE SE ABREN AL INICIAR")
        apps_card.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        list_wrap = tk.Frame(apps_card, bg=CARD_BG)
        list_wrap.pack(fill="both", expand=True, padx=10, pady=(0, 6))

        canvas = tk.Canvas(list_wrap, bg=CARD_BG, highlightthickness=0, bd=0)
        scrollbar = ttk.Scrollbar(list_wrap, orient="vertical", command=canvas.yview)
        self.apps_list_frame = tk.Frame(canvas, bg=CARD_BG)

        apps_window = canvas.create_window((0, 0), window=self.apps_list_frame, anchor="nw")
        self.apps_list_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        # Sin esto, el frame interno conserva su ancho "natural" (el que pida el
        # contenido más ancho) y las filas con comandos largos empujan los
        # botones de eliminar fuera del área visible del canvas.
        canvas.bind(
            "<Configure>", lambda e: canvas.itemconfigure(apps_window, width=e.width)
        )
        canvas.configure(yscrollcommand=scrollbar.set)

        def _on_mousewheel(event):
            delta = -1 if event.num == 5 or event.delta < 0 else 1
            canvas.yview_scroll(-delta, "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        canvas.bind_all("<Button-4>", _on_mousewheel)
        canvas.bind_all("<Button-5>", _on_mousewheel)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.empty_hint = tk.Label(
            self.apps_list_frame,
            text="Todavía no agregaste ninguna app.",
            bg=CARD_BG, fg=MUTED_DIM, font=self.f_label,
        )

        add_row = tk.Frame(apps_card, bg=CARD_BG)
        add_row.pack(fill="x", padx=18, pady=(2, 16))
        flat_button(
            add_row, "+  Agregar app", self.add_app_dialog,
            bg=CARD_BG_ALT, hover=_lighten(CARD_BG_ALT, 0.3), fg=TEXT,
            font=self.f_label, padx=14, pady=8,
        ).pack(side="left")
        tk.Label(
            add_row,
            text="(buscá entre tus apps instaladas, como el menú de aplicaciones)"
            if platform.system() == "Linux" else "",
            bg=CARD_BG, fg=MUTED_DIM, font=self.f_hint,
        ).pack(side="left", padx=10)

    # ---------- diálogos propios (reemplazan messagebox/simpledialog nativos) ----------
    def _modal_shell(self, title, width=380):
        dialog = tk.Toplevel(self)
        dialog.title(title)
        dialog.configure(bg=CARD_BG, highlightbackground=BORDER, highlightthickness=1)
        dialog.transient(self)
        dialog.resizable(False, False)
        dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
        return dialog

    def _center_over_parent(self, dialog):
        dialog.update_idletasks()
        px, py = self.winfo_rootx(), self.winfo_rooty()
        pw, ph = self.winfo_width(), self.winfo_height()
        dw, dh = dialog.winfo_width(), dialog.winfo_height()
        x = px + max(0, (pw - dw) // 2)
        y = py + max(0, (ph - dh) // 3)
        dialog.geometry(f"+{x}+{y}")

    def _message_dialog(self, title, message, kind="info"):
        dialog = self._modal_shell(title)
        accent = DANGER if kind == "warning" else ACCENT
        badge_char = "!" if kind == "warning" else "i"

        body = tk.Frame(dialog, bg=CARD_BG)
        body.pack(padx=24, pady=(22, 16), fill="both")

        badge = tk.Canvas(body, width=28, height=28, bg=CARD_BG, highlightthickness=0)
        badge.create_oval(0, 0, 28, 28, fill=accent, outline=accent)
        badge.create_text(14, 14, text=badge_char, fill="white", font=(self.font_family, 11, "bold"))
        badge.grid(row=0, column=0, sticky="n", padx=(0, 14))

        tk.Label(body, text=message, bg=CARD_BG, fg=TEXT, font=self.f_label,
                 justify="left", wraplength=300).grid(row=0, column=1, sticky="w")

        btn_row = tk.Frame(dialog, bg=CARD_BG)
        btn_row.pack(fill="x", padx=24, pady=(0, 20))
        ok_btn = flat_button(btn_row, "Entendido", dialog.destroy, bg=ACCENT, hover=ACCENT_HOVER,
                              font=self.f_label, padx=18, pady=8)
        ok_btn.pack(side="right")

        dialog.bind("<Return>", lambda e: dialog.destroy())
        dialog.bind("<Escape>", lambda e: dialog.destroy())
        dialog.grab_set()
        self._center_over_parent(dialog)
        ok_btn.focus_set()
        dialog.wait_window()

    def _confirm_dialog(self, title, message):
        result = {"value": False}
        dialog = self._modal_shell(title)

        tk.Label(dialog, text=message, bg=CARD_BG, fg=TEXT, font=self.f_label,
                 justify="left", wraplength=320).pack(padx=24, pady=(22, 16), fill="both")

        def _yes():
            result["value"] = True
            dialog.destroy()

        btn_row = tk.Frame(dialog, bg=CARD_BG)
        btn_row.pack(fill="x", padx=24, pady=(0, 20))
        flat_button(btn_row, "No", dialog.destroy, bg=CARD_BG_ALT, hover=_lighten(CARD_BG_ALT, 0.3),
                    fg=TEXT, font=self.f_label, padx=18, pady=8).pack(side="right")
        flat_button(btn_row, "Sí", _yes, bg=ACCENT, hover=ACCENT_HOVER,
                    font=self.f_label, padx=18, pady=8).pack(side="right", padx=(0, 8))

        dialog.bind("<Return>", lambda e: _yes())
        dialog.bind("<Escape>", lambda e: dialog.destroy())
        dialog.grab_set()
        self._center_over_parent(dialog)
        dialog.wait_window()
        return result["value"]

    def _ask_string_dialog(self, title, prompt, initial=""):
        result = {"value": None}
        dialog = self._modal_shell(title)

        tk.Label(dialog, text=prompt, bg=CARD_BG, fg=TEXT, font=self.f_label,
                 justify="left", wraplength=320).pack(padx=24, pady=(22, 12), anchor="w")

        var = tk.StringVar(value=initial)
        entry = self._entry(dialog, var, width=36)
        entry.pack(padx=24, pady=(0, 18), fill="x", ipady=4)
        entry.focus_set()
        entry.select_range(0, tk.END)

        def _ok(_event=None):
            value = var.get().strip()
            if value:
                result["value"] = value
            dialog.destroy()

        btn_row = tk.Frame(dialog, bg=CARD_BG)
        btn_row.pack(fill="x", padx=24, pady=(0, 20))
        flat_button(btn_row, "Cancelar", dialog.destroy, bg=CARD_BG_ALT, hover=_lighten(CARD_BG_ALT, 0.3),
                    fg=TEXT, font=self.f_label, padx=18, pady=8).pack(side="right")
        flat_button(btn_row, "Aceptar", _ok, bg=ACCENT, hover=ACCENT_HOVER,
                    font=self.f_label, padx=18, pady=8).pack(side="right", padx=(0, 8))

        dialog.bind("<Return>", _ok)
        dialog.bind("<Escape>", lambda e: dialog.destroy())
        dialog.grab_set()
        self._center_over_parent(dialog)
        dialog.wait_window()
        return result["value"]

    def _update_spotify_status(self):
        url = self.spotify_var.get().strip()
        if not url:
            self.spotify_status_var.set("")
            return
        if SPOTIFY_TRACK_RE.search(url):
            self.spotify_status_var.set("✓ Canción detectada, no hace falta tocar nada más")
            self.spotify_status_label.config(fg=SUCCESS)
        else:
            self.spotify_status_var.set("⚠ No parece un link de canción de Spotify (¿es de un álbum o playlist?)")
            self.spotify_status_label.config(fg=DANGER)

    def _autostart_enabled_safe(self):
        try:
            return autostart.is_enabled()
        except OSError:
            return False

    def _apply_autostart(self):
        try:
            if self.autostart_var.get():
                autostart.enable()
            else:
                autostart.disable()
        except OSError as e:
            self._message_dialog(
                "Jarvis",
                f"No pude aplicar el cambio de inicio automático: {e}",
                kind="warning",
            )

    def _refresh_empty_hint(self):
        if self.app_rows:
            self.empty_hint.pack_forget()
        else:
            self.empty_hint.pack(anchor="w", padx=10, pady=16)

    def _populate_apps(self):
        for app in self.config_data.get("apps", []):
            self._add_app_row(app["name"], app["command"], app.get("enabled", True))
        self._refresh_empty_hint()

    def _add_app_row(self, name, command, enabled):
        row = tk.Frame(self.apps_list_frame, bg=CARD_BG_ALT)
        row.pack(fill="x", padx=8, pady=4)
        inner = tk.Frame(row, bg=CARD_BG_ALT)
        inner.pack(fill="x", padx=12, pady=10)

        enabled_var = tk.BooleanVar(value=enabled)
        ToggleSwitch(inner, enabled_var, bg=CARD_BG_ALT).pack(side="left")

        text_col = tk.Frame(inner, bg=CARD_BG_ALT)
        text_col.pack(side="left", fill="x", expand=True, padx=(12, 8))
        tk.Label(text_col, text=name, bg=CARD_BG_ALT, fg=TEXT, font=self.f_label, anchor="w") \
            .pack(fill="x")
        command_label = tk.Label(text_col, text=_truncate(command), bg=CARD_BG_ALT, fg=MUTED_DIM,
                                  font=self.f_hint, anchor="w")
        command_label.pack(fill="x")
        if command_label.cget("text") != command:
            _Tooltip(command_label, command)

        remove_btn = tk.Button(
            inner, text="\u2715", fg=DANGER, bg=CARD_BG_ALT, activebackground=CARD_BG_ALT,
            activeforeground=DANGER_HOVER, bd=0, relief="flat", cursor="hand2",
            font=self.f_label, command=lambda: self._remove_app_row(row),
        )
        remove_btn.pack(side="right")

        self.app_rows.append({"frame": row, "name": name, "command": command, "enabled_var": enabled_var})
        self._refresh_empty_hint()

    def _remove_app_row(self, row_frame):
        self.app_rows = [r for r in self.app_rows if r["frame"] != row_frame]
        row_frame.destroy()
        self._refresh_empty_hint()

    def add_app_dialog(self):
        if platform.system() == "Linux":
            self._open_installed_apps_picker()
        else:
            self._add_app_manually()

    def _open_installed_apps_picker(self):
        installed_apps = scan_installed_apps()
        if not installed_apps:
            self._message_dialog(
                "Jarvis",
                "No encontré apps instaladas para listar. Vas a poder agregarla a mano.",
                kind="warning",
            )
            self._add_app_manually()
            return

        picker = tk.Toplevel(self)
        picker.title("Buscar app instalada")
        picker.geometry("440x520")
        picker.configure(bg=BG)
        picker.transient(self)
        picker.grab_set()

        tk.Label(picker, text="Buscá una app (como en tu menú de aplicaciones)",
                 bg=BG, fg=TEXT, font=self.f_label).pack(anchor="w", padx=16, pady=(16, 8))

        search_var = tk.StringVar()
        search_entry = tk.Entry(
            picker, textvariable=search_var, bg=CARD_BG_ALT, fg=TEXT,
            insertbackground=TEXT, relief="flat", bd=0, highlightthickness=1,
            highlightbackground=BORDER, highlightcolor=ACCENT, font=self.f_label,
        )
        search_entry.pack(fill="x", padx=16, ipady=6)
        search_entry.focus_set()

        list_frame = tk.Frame(picker, bg=BG)
        list_frame.pack(fill="both", expand=True, padx=16, pady=12)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical")
        listbox = tk.Listbox(
            list_frame, yscrollcommand=scrollbar.set, activestyle="none",
            bg=CARD_BG_ALT, fg=TEXT, selectbackground=ACCENT, selectforeground="white",
            relief="flat", bd=0, highlightthickness=0, font=self.f_label,
        )
        scrollbar.config(command=listbox.yview)
        scrollbar.pack(side="right", fill="y")
        listbox.pack(side="left", fill="both", expand=True)

        def refresh_list(*_):
            query = search_var.get().lower().strip()
            listbox.delete(0, tk.END)
            for name, _command in installed_apps:
                if query in name.lower():
                    listbox.insert(tk.END, name)

        search_var.trace_add("write", refresh_list)
        refresh_list()

        apps_by_name = dict(installed_apps)

        def confirm_selection(_event=None):
            selection = listbox.curselection()
            if not selection:
                return
            name = listbox.get(selection[0])
            command = apps_by_name.get(name)
            if command:
                self._add_app_row(name, command, True)
            picker.destroy()

        listbox.bind("<Double-Button-1>", confirm_selection)
        search_entry.bind("<Return>", lambda e: (
            confirm_selection() if listbox.size() == 1 else listbox.selection_set(0)
        ))

        btns = tk.Frame(picker, bg=BG)
        btns.pack(fill="x", padx=16, pady=(0, 16))
        flat_button(btns, "Agregar seleccionada", confirm_selection,
                    bg=ACCENT, hover=ACCENT_HOVER, font=self.f_label, padx=14, pady=8).pack(side="left")
        flat_button(
            btns, "Agregar a mano", lambda: (picker.destroy(), self._add_app_manually()),
            bg=CARD_BG_ALT, hover=_lighten(CARD_BG_ALT, 0.3), fg=TEXT,
            font=self.f_label, padx=14, pady=8,
        ).pack(side="right")

    def _add_app_manually(self):
        name = self._ask_string_dialog("Nombre de la app", "¿Cómo se llama? (ej: Discord)")
        if not name:
            return

        use_file = self._confirm_dialog(
            "Comando", "¿Querés elegir un ejecutable/archivo con el explorador?\n"
            "(Si elegís 'No' vas a poder escribir el comando a mano, ej: discord)"
        )
        if use_file:
            path = filedialog.askopenfilename(title=f"Elegí el ejecutable de {name}")
            if not path:
                return
            command = f'"{path}"'
        else:
            command = self._ask_string_dialog(
                "Comando", f"Comando para abrir {name} (ej: discord, o la ruta completa):"
            )
            if not command:
                return

        self._add_app_row(name, command, True)

    def save(self):
        self.config_data["user_name"] = self.name_var.get().strip()
        self.config_data["voice"] = self.VOICES[self.voice_var.get()]
        self.config_data["spotify_track_url"] = self.spotify_var.get().strip()
        self.config_data["apps"] = [
            {"name": r["name"], "command": r["command"], "enabled": r["enabled_var"].get()}
            for r in self.app_rows
        ]
        save_config(self.config_data)
        self._apply_autostart()
        self._message_dialog("Jarvis", "Cambios guardados. Se van a aplicar la próxima vez que prendas tu compu.")


if __name__ == "__main__":
    if "--start" in sys.argv:
        # Modo silencioso: lo usa el registro de inicio automático (autostart.py)
        # para correr el saludo/apps sin mostrar el panel de configuración.
        import jarvis_start
        jarvis_start.main()
    else:
        app = JarvisConfigApp()
        app.mainloop()