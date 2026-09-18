param([switch]$ExecutableOnly)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$appVersion = python -c "from d4sign.version import VERSION; print(VERSION)"
if ($LASTEXITCODE -ne 0) { throw 'Falha ao ler a versão.' }
python -m PyInstaller --noconfirm --clean --windowed --onedir --name D4Sign --collect-all selenium --distpath dist --workpath build desktop.py
if ($LASTEXITCODE -ne 0) { throw 'Falha ao gerar o executável.' }
if ($ExecutableOnly) { exit 0 }
$compiler = Get-Command ISCC.exe -ErrorAction SilentlyContinue
$compilerPath = if ($compiler) { $compiler.Source } else { "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" }
if (-not (Test-Path -LiteralPath $compilerPath)) { throw 'Instale Inno Setup 6 ou adicione ISCC.exe ao PATH. O executável já está em dist/D4Sign.' }
& $compilerPath "/DAppVersion=$appVersion" packaging/installer.iss
if ($LASTEXITCODE -ne 0) { throw 'Falha ao gerar o instalador.' }
