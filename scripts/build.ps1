param(
    [switch]$ExecutableOnly
)

$ErrorActionPreference = 'Stop'

# Vai para a raiz do projeto
Set-Location (Split-Path $PSScriptRoot -Parent)

Write-Host "Lendo versao do D4Sign..."

$appVersion = python -c "from d4sign.version import VERSION; print(VERSION)"

if ($LASTEXITCODE -ne 0) {
    throw 'Falha ao ler a versao.'
}

Write-Host "Versao: $appVersion"
Write-Host ""

# Limpa builds anteriores
Write-Host "Limpando builds anteriores..."

if (Test-Path "dist") {
    Remove-Item "dist" -Recurse -Force
}

if (Test-Path "build") {
    Remove-Item "build" -Recurse -Force
}

Write-Host "Gerando D4Sign.exe..."

python -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --onefile `
    --name "D4Sign-Setup-$appVersion" `
    --icon="icon/logo.ico" `
    --add-data "icon/logo.ico;icon" `
    --collect-all selenium `
    --distpath "dist" `
    --workpath "build" `
    "desktop.py"

if ($LASTEXITCODE -ne 0) {
    throw 'Falha ao gerar o executavel.'
}

if (-not (Test-Path "dist\D4Sign-Setup-$appVersion.exe")) {
    throw 'D4Sign-Setup-$appVersion.exe nao foi encontrado apos o build.'
}

Write-Host ""
Write-Host "======================================"
Write-Host " D4Sign $appVersion"
Write-Host " Build concluido com sucesso"
Write-Host "======================================"
Write-Host ""
Write-Host "Executavel:"
Write-Host "dist\D4Sign-Setup-$appVersion.exe"

# Para aqui quando queremos somente o EXE
if ($ExecutableOnly) {
    exit 0
}

Write-Host ""
Write-Host "Procurando Inno Setup..."

$compiler = Get-Command ISCC.exe -ErrorAction SilentlyContinue

if ($compiler) {
    $compilerPath = $compiler.Source
}
else {
    $compilerPath = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
}

if (-not (Test-Path -LiteralPath $compilerPath)) {
    Write-Host ""
    Write-Warning "Inno Setup nao encontrado."
    Write-Host "O D4Sign-Setup-$appVersion.exe foi gerado normalmente em dist\D4Sign-Setup-$appVersion.exe"
    exit 0
}

Write-Host "Inno Setup encontrado:"
Write-Host $compilerPath

Write-Host ""
Write-Host "Gerando instalador versao $appVersion..."

& $compilerPath "/DAppVersion=$appVersion" "packaging\installer.iss"

if ($LASTEXITCODE -ne 0) {
    throw 'Falha ao gerar o instalador.'
}

Write-Host ""
Write-Host "Instalador gerado com sucesso."