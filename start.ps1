$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$magiPython = Join-Path $PSScriptRoot '.venv\Scripts\pythonw.exe'
if (-not (Test-Path -LiteralPath $magiPython)) {
    throw 'Crea .venv e instala requirements.txt siguiendo el README antes de iniciar MAGI.'
}
Start-Process -FilePath $magiPython -ArgumentList ('"' + (Join-Path $PSScriptRoot 'launch.py') + '"') -WorkingDirectory $PSScriptRoot -WindowStyle Hidden
