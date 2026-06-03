$ErrorActionPreference = "Stop"

function Get-PythonExecutable {
    param(
        [Parameter(Mandatory = $true)]
        [string]$BackendDir
    )

    $isWindows = $false
    if ($env:OS -eq "Windows_NT") {
        $isWindows = $true
    }
    elseif ([System.Runtime.InteropServices.RuntimeInformation]::IsOSPlatform([System.Runtime.InteropServices.OSPlatform]::Windows)) {
        $isWindows = $true
    }

    $candidates = @()
    if ($isWindows) {
        $candidates += (Join-Path $BackendDir ".venv\Scripts\python.exe")
        $candidates += (Join-Path $BackendDir "venv\Scripts\python.exe")
    }
    else {
        $candidates += (Join-Path $BackendDir ".venv/bin/python")
        $candidates += (Join-Path $BackendDir "venv/bin/python")
    }

    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) {
            return $candidate
        }
    }

    foreach ($cmdName in @("python", "python3", "py")) {
        $pythonCommand = Get-Command $cmdName -ErrorAction SilentlyContinue
        if ($null -ne $pythonCommand) {
            if (-not [string]::IsNullOrWhiteSpace($pythonCommand.Source)) {
                return $pythonCommand.Source
            }
            elseif (-not [string]::IsNullOrWhiteSpace($pythonCommand.Path)) {
                return $pythonCommand.Path
            }
            else {
                return $cmdName
            }
        }
    }

    throw "Python was not found. Please install Python or create backend\.venv first."
}

function Test-PythonModule {
    param(
        [Parameter(Mandatory = $true)]
        [string]$PythonExe,
        [Parameter(Mandatory = $true)]
        [string]$ModuleName
    )

    & $PythonExe -c "import $ModuleName" 2>$null | Out-Null
    return ($LASTEXITCODE -eq 0)
}

function Get-StartupCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string]$BackendDir,
        [Parameter(Mandatory = $true)]
        [string]$PythonExe
    )

    $mainPyPath = Join-Path $BackendDir "main.py"
    $appMainPyPath = Join-Path $BackendDir "app\main.py"

    if (Test-Path $mainPyPath) {
        return @{ Type = "script"; Value = $mainPyPath }
    }

    if (Test-Path $appMainPyPath) {
        return @{ Type = "uvicorn"; Value = "app.main:app" }
    }

    throw "Cannot find backend entrypoint. Checked backend\main.py and backend\app\main.py."
}

if (Get-Variable -Name PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue) {
    $PSNativeCommandUseErrorActionPreference = $false
}

$repoRoot = $PSScriptRoot
$backendDir = Join-Path $repoRoot "backend"
$envExamplePath = Join-Path $backendDir ".env.example"
$envPath = Join-Path $backendDir ".env"
$requirementsPath = Join-Path $backendDir "requirements.txt"

if (-not (Test-Path $backendDir)) {
    throw "Cannot find backend directory. Run this script from the repository root."
}

if (-not (Test-Path $envPath) -and (Test-Path $envExamplePath)) {
    Copy-Item $envExamplePath $envPath
    Write-Host "Created backend\.env from .env.example. Review database settings before first use." -ForegroundColor Yellow
}

$pythonExe = Get-PythonExecutable -BackendDir $backendDir
$startup = Get-StartupCommand -BackendDir $backendDir -PythonExe $pythonExe

Set-Location $backendDir

Write-Host "Using Python: $pythonExe" -ForegroundColor Green

& $pythonExe --version
if ($LASTEXITCODE -ne 0) {
    throw "Failed to execute Python: $pythonExe"
}

$needInstall = $false

foreach ($moduleName in @("fastapi", "uvicorn")) {
    if (-not (Test-PythonModule -PythonExe $pythonExe -ModuleName $moduleName)) {
        $needInstall = $true
        break
    }
}

if ($needInstall) {
    if (-not (Test-Path $requirementsPath)) {
        throw "requirements.txt not found in backend directory."
    }

    Write-Host "Python dependencies not found. Installing backend requirements..." -ForegroundColor Yellow
    & $pythonExe -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) {
        throw "pip upgrade failed."
    }

    & $pythonExe -m pip install -r $requirementsPath
    if ($LASTEXITCODE -ne 0) {
        throw "pip install -r requirements.txt failed."
    }
}

$backendPort = if ($env:BACKEND_PORT) { $env:BACKEND_PORT } else { "8000" }

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "NEMO Backend" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Backend Dir: $backendDir" -ForegroundColor Green
Write-Host "Python:      $pythonExe" -ForegroundColor Green
Write-Host "API docs:    http://127.0.0.1:$backendPort/api/docs" -ForegroundColor Yellow
Write-Host "Health:      http://127.0.0.1:$backendPort/health" -ForegroundColor Yellow
Write-Host ""

if ($startup.Type -eq "script") {
    & $pythonExe $startup.Value
}
else {
    & $pythonExe -m uvicorn $startup.Value --host 127.0.0.1 --port $backendPort --reload
}

$pythonExitCode = $LASTEXITCODE
if ($pythonExitCode -ne 0) {
    throw "backend exited with code $pythonExitCode"
}

exit 0
