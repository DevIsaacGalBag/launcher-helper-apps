# launcher-helper-apps

# Jarvis-Personal 🤖

Asistente de arranque personal. Al prender tu compu:
1. Te saluda por voz ("Buenos días señor Isaac...")
2. Te dice el día y la fecha
3. Te dice el clima de tu ciudad (detectada automáticamente)
4. Abre Spotify en la canción que elijas
5. Abre las apps que hayas activado en el panel de configuración

Funciona igual en **Linux** y **Windows** (mismo código Python).

> **¿No querés instalar Python?** Descargá el ejecutable ya armado (`.exe` para Windows,
> binario para Linux) desde la [página del proyecto](https://devisaacgalbag.github.io/launcher-helper-apps/) —
> no hace falta nada más instalado. Las secciones de abajo son para correrlo desde el código fuente.

---

## 1. Requisitos

- Python 3.9 o superior instalado ([python.org](https://www.python.org/downloads/))
  - En Windows, al instalar marcá la casilla **"Add Python to PATH"**.
- Conexión a internet (se usa para la voz y el clima).

> **Si clonaste esto desde un repositorio de git:** `config.json` (tus datos personales) no
> se sube al repo — está en `.gitignore`. La primera vez que corras `config_gui.py`, si no
> existe `config.json` en tu máquina, se va a crear a partir de `config.example.json` en
> cuanto guardes cambios.

## 2. Instalación

Abrí una terminal (Linux) o PowerShell/CMD (Windows) dentro de esta carpeta y corré:

```bash
pip install -r requirements.txt
```

## 3. Configurar qué se abre al iniciar

Corré el panel de configuración:

```bash
python config_gui.py
```

Ahí vas a poder:
- Poner tu nombre (para el saludo)
- Elegir la voz (varias voces en español)
- Pegar el link de la canción de Spotify (click derecho en la canción > Compartir > Copiar link de la canción)
- Agregar apps con el switch de encendido/apagado (ej: Discord, tu navegador, VSCode, etc.)

Al presionar **"Guardar cambios"** se genera el archivo `config.json` que usa el script principal.

> Nota sobre Spotify: como no tenés cuenta Premium, el sistema abre el link de la canción
> (que dispara la app de Spotify si la tenés instalada, o el navegador si no). No es posible
> forzar el "play" automático sin Premium/API — pero al abrir el link, Spotify normalmente
> empieza a reproducir solo.

## 4. Probarlo manualmente (sin esperar a reiniciar)

```bash
python jarvis_start.py
```

Si todo suena y abre bien, pasá al siguiente paso.

## 5. Hacer que arranque solo al prender la compu

La forma más simple: abrí `config_gui.py`, activá el switch **"Iniciar con la compu"** y
tocá "Guardar cambios" — funciona igual en Linux y Windows y es lo que usa el ejecutable
empaquetado. Las opciones de abajo (`setup_linux.sh` / `setup_windows.ps1`) hacen lo mismo
a mano y además agregan un acceso directo al panel de configuración en el menú de apps.

### En Linux

```bash
chmod +x setup_linux.sh
./setup_linux.sh
```

Esto crea un archivo en `~/.config/autostart/jarvis.desktop`. Se activa la próxima vez que
inicies sesión en tu escritorio (funciona en GNOME, KDE, XFCE, etc.).

### En Windows

Abrí PowerShell **dentro de la carpeta del proyecto** y corré:

```powershell
powershell -ExecutionPolicy Bypass -File setup_windows.ps1
```

Esto crea un acceso directo en tu carpeta de Inicio de Windows
(`shell:startup`). Se activa la próxima vez que inicies sesión.

---

## 6. Cambiar la configuración más adelante

Cuando quieras agregar o sacar apps, cambiar la canción, o el nombre:

```bash
python config_gui.py
```

Guardás los cambios y listo — no hace falta volver a correr los scripts de `setup_*`.

---

## Estructura del proyecto

```
jarvis/
├── .github/workflows/release.yml   <- compila y publica los ejecutables (PyInstaller)
├── docs/index.html                 <- landing page del proyecto (GitHub Pages)
├── .gitignore
├── autostart.py               <- registra/quita el inicio automático (Linux y Windows)
├── config.example.json    
├── config.json            
├── config_gui.py               <- panel de configuración (interfaz gráfica)
├── jarvis_start.py             <- lógica que corre al prender la pc
├── requirements.txt
├── setup_linux.sh              <- registra el autostart en Linux (uso desde fuente)
├── setup_windows.ps1           <- registra el autostart en Windows (uso desde fuente)
└── README.md
```

## Descargas y soporte

- Los ejecutables (`.exe` de Windows y binario de Linux) se generan automáticamente con
  GitHub Actions cada vez que se publica un tag `vX.Y.Z`, y quedan disponibles en
  [Releases](https://github.com/DevIsaacGalBag/launcher-helper-apps/releases).
- La landing page vive en `docs/index.html` y se publica con GitHub Pages.
- Si te sirvió el proyecto, podés invitar un café en
  [Ko-fi](https://ko-fi.com/isaacdev).

## Notas / posibles mejoras futuras

- Si en algún momento sacás Spotify Premium, se puede migrar a la API oficial de Spotify
  para controlar reproducción exacta, volumen, playlists, etc.
- Se puede agregar reconocimiento de voz para darle comandos a Jarvis además del saludo inicial.
- El clima usa [Open-Meteo](https://open-meteo.com) (gratis, sin API key) y la ubicación
  se detecta por IP con [ip-api.com](https://ip-api.com) (gratis, sin API key).
- La voz usa **Edge TTS** (motor de Microsoft, gratis, sin API key, voces bastante naturales).
