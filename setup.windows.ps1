# Registra Jarvis para que arranque solo la próxima vez que inicies sesión en Windows.
# Ejecutar con: powershell -ExecutionPolicy Bypass -File setup_windows.ps1

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$StartupFolder = [Environment]::GetFolderPath('Startup')
$ShortcutPath = Join-Path $StartupFolder "Jarvis.lnk"

# Busca pythonw.exe (corre sin abrir consola) o python.exe como respaldo
$PythonwCmd = Get-Command pythonw -ErrorAction SilentlyContinue
if ($PythonwCmd) {
    $PythonPath = $PythonwCmd.Source
} else {
    $PythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if (-not $PythonCmd) {
        Write-Host "No se encontró Python instalado. Instalalo desde python.org y volvé a correr este script." -ForegroundColor Red
        exit 1
    }
    $PythonPath = $PythonCmd.Source
}

$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $PythonPath
$Shortcut.Arguments = "`"$ScriptDir\jarvis_start.py`""
$Shortcut.WorkingDirectory = $ScriptDir
$Shortcut.Save()

Write-Host "Listo. Jarvis se ejecutará automáticamente la próxima vez que inicies sesión en Windows." -ForegroundColor Green
Write-Host "Acceso directo creado en: $ShortcutPath"
Write-Host ""
Write-Host "Para probarlo ahora mismo sin reiniciar, corré:"
Write-Host "  python `"$ScriptDir\jarvis_start.py`""
