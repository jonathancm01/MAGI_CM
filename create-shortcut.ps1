$ErrorActionPreference = 'Stop'
$magiPython = Join-Path $PSScriptRoot '.venv\Scripts\pythonw.exe'
if (-not (Test-Path -LiteralPath $magiPython)) {
    throw 'Crea .venv e instala requirements.txt siguiendo el README antes de crear el acceso.'
}
$magiShortcutPath = Join-Path (Split-Path -Parent $PSScriptRoot) 'MAGI.lnk'
$magiShell = New-Object -ComObject WScript.Shell
$magiShortcut = $magiShell.CreateShortcut($magiShortcutPath)
if ((Test-Path -LiteralPath $magiShortcutPath) -and $magiShortcut.TargetPath -ne $magiPython) {
    throw "Ya existe otro acceso directo en $magiShortcutPath. Se conservó sin cambios."
}
$magiShortcut.TargetPath = $magiPython
$magiShortcut.Arguments = '"' + (Join-Path $PSScriptRoot 'launch.py') + '"'
$magiShortcut.WorkingDirectory = $PSScriptRoot
$magiShortcut.Description = 'MAGI - Consejo de agentes'
$magiShortcut.IconLocation = "$magiPython,0"
$magiShortcut.WindowStyle = 7
$magiShortcut.Save()
Write-Output "Acceso creado: $magiShortcutPath"
