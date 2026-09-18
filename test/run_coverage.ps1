Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $PSScriptRoot
Push-Location $RootDir
try {
    & python -m pytest -c test/pytest.ini test `
        --cov=d4sign `
        --cov=main `
        --cov-branch `
        --cov-report=term-missing `
        --cov-fail-under=100 @args
    $ExitCode = $LASTEXITCODE
}
finally {
    Pop-Location
}

exit $ExitCode
