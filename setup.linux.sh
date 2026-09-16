#!/bin/bash
# Registra Jarvis para que arranque solo la próxima vez que inicies sesión en Linux,
# y agrega un acceso directo al panel de configuración en el menú de aplicaciones.
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AUTOSTART_DIR="$HOME/.config/autostart"
APPS_DIR="$HOME/.local/share/applications"
DESKTOP_FILE="$AUTOSTART_DIR/jarvis.desktop"
CONFIG_DESKTOP_FILE="$APPS_DIR/jarvis-config.desktop"

mkdir -p "$AUTOSTART_DIR" "$APPS_DIR"

PYTHON_BIN="$(command -v python3)"

# 1) Autostart: corre jarvis_start.py solo, al iniciar sesión
cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=Jarvis
Comment=Asistente de arranque
Exec=$PYTHON_BIN "$DIR/jarvis_start.py"
Terminal=false
X-GNOME-Autostart-enabled=true
EOF
chmod +x "$DESKTOP_FILE"

# 2) Menú de aplicaciones: acceso directo al panel de configuración,
#    buscable como cualquier otra app (Actividades > "Jarvis")
cat > "$CONFIG_DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=Jarvis - Configuración
Comment=Panel para elegir qué apps y canción se abren al iniciar
Exec=$PYTHON_BIN "$DIR/config_gui.py"
Icon=preferences-system
Terminal=false
Categories=Settings;Utility;
EOF
chmod +x "$CONFIG_DESKTOP_FILE"

echo "Listo:"
echo "  - Jarvis se ejecutará automáticamente la próxima vez que inicies sesión."
echo "    ($DESKTOP_FILE)"
echo "  - El panel de configuración ya aparece en tu menú de aplicaciones,"
echo "    buscalo como 'Jarvis - Configuración'."
echo "    ($CONFIG_DESKTOP_FILE)"
echo ""
echo "Para probar el saludo ahora mismo sin reiniciar, corré:"
echo "  python3 \"$DIR/jarvis_start.py\""