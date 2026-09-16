"""
JARVIS - Inicio automático
---------------------------
Registra (o quita) a Jarvis del arranque del sistema operativo, tanto si
corre desde el código fuente (python config_gui.py) como empaquetado
(Jarvis.exe / binario de Linux generado con PyInstaller).

Linux: crea/borra ~/.config/autostart/jarvis.desktop
Windows: agrega/borra un valor en HKCU\\...\\CurrentVersion\\Run
"""

import platform
import sys
from pathlib import Path

APP_NAME = "Jarvis"


def _is_frozen():
    return getattr(sys, "frozen", False)


def _launch_command():
    """Comando que arranca Jarvis en modo silencioso (sin abrir el panel)."""
    if _is_frozen():
        return [sys.executable, "--start"]
    script = Path(__file__).resolve().parent / "config_gui.py"
    return [sys.executable, str(script), "--start"]


def _linux_desktop_file():
    return Path.home() / ".config" / "autostart" / "jarvis.desktop"


def is_enabled():
    system = platform.system()
    if system == "Linux":
        return _linux_desktop_file().exists()
    if system == "Windows":
        return _windows_registry_value() is not None
    return False


def enable():
    system = platform.system()
    if system == "Linux":
        _enable_linux()
    elif system == "Windows":
        _enable_windows()
    else:
        raise RuntimeError(f"Inicio automático no soportado en {system}")


def disable():
    system = platform.system()
    if system == "Linux":
        path = _linux_desktop_file()
        if path.exists():
            path.unlink()
    elif system == "Windows":
        _disable_windows()


def _enable_linux():
    autostart_dir = _linux_desktop_file().parent
    autostart_dir.mkdir(parents=True, exist_ok=True)
    exec_line = " ".join(f'"{part}"' for part in _launch_command())
    content = (
        "[Desktop Entry]\n"
        "Type=Application\n"
        f"Name={APP_NAME}\n"
        "Comment=Asistente de arranque\n"
        f"Exec={exec_line}\n"
        "Terminal=false\n"
        "X-GNOME-Autostart-enabled=true\n"
    )
    path = _linux_desktop_file()
    path.write_text(content, encoding="utf-8")
    path.chmod(0o755)


def _windows_run_key(access):
    import winreg
    return winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Run",
        0,
        access,
    )


def _windows_registry_value():
    import winreg
    try:
        with _windows_run_key(winreg.KEY_READ) as key:
            value, _ = winreg.QueryValueEx(key, APP_NAME)
            return value
    except (FileNotFoundError, OSError):
        return None


def _enable_windows():
    import winreg
    command = " ".join(f'"{part}"' for part in _launch_command())
    with _windows_run_key(winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, command)


def _disable_windows():
    import winreg
    try:
        with _windows_run_key(winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, APP_NAME)
    except (FileNotFoundError, OSError):
        pass
