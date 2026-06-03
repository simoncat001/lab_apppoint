$ErrorActionPreference = "Stop"

try {
    $repoRoot = $PSScriptRoot
    $uiDir = Join-Path $repoRoot "ui"

    if (-not (Test-Path (Join-Path $uiDir "package.json"))) {
        throw "Cannot find ui\package.json. Run this script from the repository root."
    }

    $npmCommand = Get-Command npm.cmd -ErrorAction SilentlyContinue
    if ($null -eq $npmCommand) {
        $npmCommand = Get-Command npm -ErrorAction SilentlyContinue
    }
    if ($null -eq $npmCommand) {
        throw "npm was not found in PATH."
    }

    Set-Location $uiDir

    if (-not (Test-Path (Join-Path $uiDir "node_modules"))) {
        Write-Host "node_modules was not found. Running npm install..." -ForegroundColor Yellow
        & $npmCommand.Source install
        if ($LASTEXITCODE -ne 0) {
            throw "npm install failed."
        }
    }

    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "NEMO UI" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Vite dev server: http://localhost:3000" -ForegroundColor Yellow
    Write-Host ""

    & $npmCommand.Source run dev
    exit $LASTEXITCODE
}
catch {
    Write-Host ""
    Write-Host "Failed to start UI." -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}
