"""
JARVIS - Script de arranque
----------------------------
Este script se ejecuta automáticamente al prender la computadora
(una vez configurado el autostart con setup_linux.sh o setup_windows.ps1).

Hace lo siguiente:
1. Saluda por voz (usando Edge TTS, voz natural online).
2. Dice el día y la fecha en español.
3. Consulta el clima según tu ubicación (detectada por IP).
4. Abre Spotify en la canción configurada.
5. Abre todas las apps que estén marcadas como "enabled": true en config.json
"""

import asyncio
import datetime
import json
import os
import platform
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

import requests

try:
    import edge_tts
except ImportError:
    print("Falta instalar edge-tts. Corré: pip install -r requirements.txt")
    sys.exit(1)


def _app_base_dir():
    # Empaquetado con PyInstaller (--onefile): __file__ apunta a la carpeta
    # temporal de extracción, que se borra en cada corrida. Usamos la carpeta
    # donde vive el .exe para que config.json persista entre ejecuciones.
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


BASE_DIR = _app_base_dir()
CONFIG_PATH = BASE_DIR / "config.json"
AUDIO_PATH = BASE_DIR / "_greeting.mp3"

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]

# Mapeo simplificado de códigos de clima de Open-Meteo a texto en español
WEATHER_CODES = {
    0: "cielo despejado",
    1: "mayormente despejado",
    2: "parcialmente nublado",
    3: "nublado",
    45: "con niebla",
    48: "con niebla helada",
    51: "con llovizna ligera",
    53: "con llovizna moderada",
    55: "con llovizna intensa",
    61: "con lluvia ligera",
    63: "con lluvia moderada",
    65: "con lluvia intensa",
    71: "con nevadas ligeras",
    73: "con nevadas moderadas",
    75: "con nevadas intensas",
    80: "con chubascos",
    95: "con tormenta",
}


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_greeting_word():
    hour = datetime.datetime.now().hour
    if hour < 12:
        return "Buenos días"
    elif hour < 20:
        return "Buenas tardes"
    else:
        return "Buenas noches"


def get_spanish_date():
    now = datetime.datetime.now()
    dia_semana = DIAS[now.weekday()]
    mes = MESES[now.month - 1]
    return f"Hoy es {dia_semana}, {now.day} de {mes} de {now.year}"


def get_weather_text():
    try:
        # Ubicación aproximada por IP (gratis, sin API key)
        geo = requests.get("http://ip-api.com/json/", timeout=5).json()
        lat, lon = geo.get("lat"), geo.get("lon")
        city = geo.get("city", "tu ciudad")

        weather = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,weather_code",
                "timezone": "auto",
            },
            timeout=5,
        ).json()

        temp = weather["current"]["temperature_2m"]
        code = weather["current"]["weather_code"]
        desc = WEATHER_CODES.get(code, "condiciones variables")

        return f"En {city} hay {temp} grados y el clima está {desc}."
    except Exception as e:
        print(f"[clima] No se pudo obtener el clima: {e}")
        return "No pude obtener el clima en este momento."


async def _generate_speech(text, voice):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(AUDIO_PATH))


def _play_audio_blocking(path):
    """Reproduce un mp3 usando herramientas ya instaladas en el sistema
    (sin depender de librerías de Python que haya que compilar)."""
    system = platform.system()

    if system == "Windows":
        # PowerShell con MediaPlayer bloquea hasta que termina la reproducción
        ps_command = (
            "Add-Type -AssemblyName presentationCore; "
            "$player = New-Object system.windows.media.mediaplayer; "
            f"$player.open([uri]'{path}'); "
            "$player.Play(); "
            "Start-Sleep -Milliseconds 500; "
            "while ($player.NaturalDuration.HasTimeSpan -eq $false) { Start-Sleep -Milliseconds 100 }; "
            "Start-Sleep -Seconds $player.NaturalDuration.TimeSpan.TotalSeconds; "
            "$player.Close();"
        )
        # Sin esto, se abre una consola de PowerShell visible (fondo azul)
        # mientras habla Jarvis — CREATE_NO_WINDOW evita que se cree la consola.
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        subprocess.run(
            ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps_command],
            check=True, startupinfo=startupinfo, creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return

    # Linux / macOS: probamos reproductores de línea de comandos comunes, en orden de preferencia
    players = [
        ["mpg123", "-q", str(path)],
        ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", str(path)],
        ["cvlc", "--play-and-exit", str(path)],
        ["paplay", str(path)],  # solo soporta wav en algunas distros, queda como último intento
    ]
    for player_cmd in players:
        try:
            subprocess.run(player_cmd, check=True,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return
        except (FileNotFoundError, subprocess.CalledProcessError):
            continue

    raise RuntimeError(
        "No se encontró ningún reproductor de audio instalado. "
        "Instalá uno con: sudo dnf install mpg123 (o sudo apt install mpg123)"
    )


def speak(text, voice):
    print(f"[jarvis dice] {text}")
    try:
        asyncio.run(_generate_speech(text, voice))
        _play_audio_blocking(AUDIO_PATH)
    except Exception as e:
        print(f"[voz] No se pudo reproducir el audio: {e}")
    finally:
        if AUDIO_PATH.exists():
            try:
                AUDIO_PATH.unlink()
            except OSError:
                pass


def spotify_uri_from_url(url):
    # https://open.spotify.com/track/XXXXXXXX?si=... -> spotify:track:XXXXXXXX
    try:
        track_id = url.split("track/")[1].split("?")[0]
        return f"spotify:track:{track_id}"
    except (IndexError, AttributeError):
        return None


def open_spotify(track_url):
    if not track_url:
        print("[spotify] No hay canción configurada, se omite.")
        return

    uri = spotify_uri_from_url(track_url)
    if not uri:
        print("[spotify] No se pudo interpretar el link, lo abro tal cual.")
        webbrowser.open(track_url)
        return

    system = platform.system()

    if system == "Linux":
        # Probamos lanzar la app de Spotify directamente pasándole el URI,
        # que es mucho más confiable que depender de que el sistema
        # redirija el protocolo spotify:// a la app correcta.
        candidates = [
            ["spotify", uri],
            ["flatpak", "run", "com.spotify.Client", uri],
            ["snap", "run", "spotify", uri],
        ]
        for cmd in candidates:
            try:
                subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                print(f"[spotify] Abriendo con: {' '.join(cmd)}")
                return
            except FileNotFoundError:
                continue

        # Último recurso: dejar que xdg-open resuelva el protocolo spotify:
        try:
            subprocess.Popen(["xdg-open", uri], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print("[spotify] Abriendo vía xdg-open (protocolo spotify:)")
            return
        except FileNotFoundError:
            pass

        print("[spotify] No encontré el comando de Spotify instalado (spotify/flatpak/snap).")

    elif system == "Windows":
        try:
            os.startfile(uri)
            print(f"[spotify] Abriendo: {uri}")
            return
        except OSError as e:
            print(f"[spotify] No se pudo abrir con el protocolo spotify: {e}")

    # Fallback universal si nada de lo anterior funcionó: abrir el link normal
    print("[spotify] Usando el link como último recurso (puede abrir el navegador).")
    webbrowser.open(track_url)


def launch_apps(apps):
    # En Windows, shell=True lanza por debajo un cmd.exe que puede hacer
    # parpadear una consola; CREATE_NO_WINDOW evita ese flash.
    popen_kwargs = {}
    if platform.system() == "Windows":
        popen_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

    for app in apps:
        if not app.get("enabled"):
            continue
        command = app.get("command")
        name = app.get("name", command)
        if not command:
            continue
        try:
            # shell=True permite tanto rutas con espacios como comandos simples (ej: "discord")
            subprocess.Popen(command, shell=True, **popen_kwargs)
            print(f"[apps] Abriendo: {name}")
        except Exception as e:
            print(f"[apps] No se pudo abrir {name}: {e}")


def main():
    config = load_config()
    user_name = config.get("user_name", "")
    voice = config.get("voice", "es-MX-DaliaNeural")

    greeting = f"{get_greeting_word()} señor {user_name}." if user_name else get_greeting_word()
    date_text = get_spanish_date()
    weather_text = get_weather_text()

    full_message = f"{greeting} {date_text}. {weather_text}"
    speak(full_message, voice)

    open_spotify(config.get("spotify_track_url"))
    launch_apps(config.get("apps", []))


if __name__ == "__main__":
    main()