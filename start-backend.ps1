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

    $oldNativePrefExists = $null -ne (Get-Variable -Name PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue)
    if ($oldNativePrefExists) {
        $oldNativePref = $PSNativeCommandUseErrorActionPreference
        $PSNativeCommandUseErrorActionPreference = $false
    }

    try {
        $code = "import importlib.util, sys; sys.exit(0 if importlib.util.find_spec('$ModuleName') else 1)"
        $null = & $PythonExe -c $code 2>$null
        return ($LASTEXITCODE -eq 0)
    }
    finally {
        if ($oldNativePrefExists) {
            $PSNativeCommandUseErrorActionPreference = $oldNativePref
        }
    }
}

function Get-StartupCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string]$BackendDir
    )

    $mainPyPath = Join-Path $BackendDir "main.py"
    $appMainPyPath = Join-Path $BackendDir "app\main.py"

    if (Test-Path $mainPyPath) {
        return @{
            Type  = "uvicorn"
            Value = "main:app"
        }
    }

    if (Test-Path $appMainPyPath) {
        return @{
            Type  = "uvicorn"
            Value = "app.main:app"
        }
    }

    throw "Cannot find backend entrypoint. Checked backend\main.py and backend\app\main.py."
}

function Test-PortInUse {
    param(
        [Parameter(Mandatory = $true)]
        [int]$Port
    )

    try {
        $connection = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction Stop
        return ($null -ne $connection)
    }
    catch {
        return $false
    }
}

function Read-DotEnv {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $values = @{}
    if (-not (Test-Path $Path)) {
        return $values
    }

    foreach ($rawLine in Get-Content $Path) {
        $line = $rawLine.Trim()
        if (-not $line -or $line.StartsWith("#")) {
            continue
        }

        $separatorIndex = $line.IndexOf("=")
        if ($separatorIndex -lt 1) {
            continue
        }

        $key = $line.Substring(0, $separatorIndex).Trim()
        $value = $line.Substring($separatorIndex + 1).Trim()

        if (
            ($value.StartsWith('"') -and $value.EndsWith('"')) -or
            ($value.StartsWith("'") -and $value.EndsWith("'"))
        ) {
            $value = $value.Substring(1, $value.Length - 2)
        }

        $values[$key] = $value
    }

    return $values
}

function Get-EnvValue {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name
    )

    $item = Get-Item -Path "Env:$Name" -ErrorAction SilentlyContinue
    if ($null -eq $item) {
        return $null
    }

    return $item.Value
}

function Resolve-Setting {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Names,
        [Parameter(Mandatory = $true)]
        [hashtable[]]$Sources,
        [AllowEmptyString()]
        [string]$DefaultValue
    )

    foreach ($name in $Names) {
        $envValue = Get-EnvValue -Name $name
        if (-not [string]::IsNullOrWhiteSpace($envValue)) {
            return $envValue
        }
    }

    foreach ($source in $Sources) {
        foreach ($name in $Names) {
            if ($source.ContainsKey($name) -and -not [string]::IsNullOrWhiteSpace($source[$name])) {
                return $source[$name]
            }
        }
    }

    return $DefaultValue
}

function Mask-Secret {
    param(
        [AllowNull()]
        [AllowEmptyString()]
        [string]$Value
    )

    if ($null -eq $Value) {
        return "<unset>"
    }

    if ($Value -eq "") {
        return "<empty>"
    }

    if ($Value.Length -le 2) {
        return ("*" * $Value.Length)
    }

    return ($Value.Substring(0, 1) + ("*" * ($Value.Length - 2)) + $Value.Substring($Value.Length - 1, 1))
}

try {
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

    $backendEnv = Read-DotEnv -Path $envPath
    $pythonExe = Get-PythonExecutable -BackendDir $backendDir
    $startup = Get-StartupCommand -BackendDir $backendDir

    # Keep the runtime isolated from user-level site-packages such as
    # C:\Users\<user>\AppData\Roaming\Python\Python312\site-packages.
    $env:PYTHONNOUSERSITE = "1"

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

    $backendPort = 8000
    if (-not [string]::IsNullOrWhiteSpace($env:BACKEND_PORT)) {
        $backendPort = [int]$env:BACKEND_PORT
    }

    if (Test-PortInUse -Port $backendPort) {
        throw "Port $backendPort is already in use."
    }

    $mysqlServer = Resolve-Setting -Names @("MYSQL_SERVER") -Sources @($backendEnv) -DefaultValue "127.0.0.1"
    $mysqlPort = Resolve-Setting -Names @("MYSQL_PORT") -Sources @($backendEnv) -DefaultValue "3306"
    $mysqlUser = Resolve-Setting -Names @("MYSQL_USER") -Sources @($backendEnv) -DefaultValue "root"
    $mysqlPassword = Resolve-Setting -Names @("MYSQL_PASSWORD") -Sources @($backendEnv) -DefaultValue "123456"
    $mysqlDb = Resolve-Setting -Names @("MYSQL_DB") -Sources @($backendEnv) -DefaultValue "szlab_appoint"
    $databaseUrl = Resolve-Setting -Names @("DATABASE_URL") -Sources @($backendEnv) -DefaultValue ""

    if ([string]::IsNullOrWhiteSpace($databaseUrl)) {
        $databaseUrl = "mysql+aiomysql://{0}:{1}@{2}:{3}/{4}" -f $mysqlUser, $mysqlPassword, $mysqlServer, $mysqlPort, $mysqlDb
    }

    $maskedDatabaseUrl = $databaseUrl
    if ($databaseUrl -match '^(?<scheme>[^:]+://)(?<user>[^:]+):(?<password>[^@]*)@(?<rest>.+)$') {
        $maskedDatabaseUrl = "$($Matches['scheme'])$($Matches['user']):$(Mask-Secret $Matches['password'])@$($Matches['rest'])"
    }

    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "NEMO Backend" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Backend Dir: $backendDir" -ForegroundColor Green
    Write-Host "Python:      $pythonExe" -ForegroundColor Green
    Write-Host "Port:        $backendPort" -ForegroundColor Green
    Write-Host "User site:   disabled (PYTHONNOUSERSITE=1)" -ForegroundColor Green
    Write-Host "Effective DB settings:" -ForegroundColor Yellow
    Write-Host "  MySQL Host:     $mysqlServer" -ForegroundColor Yellow
    Write-Host "  MySQL Port:     $mysqlPort" -ForegroundColor Yellow
    Write-Host "  MySQL User:     $mysqlUser" -ForegroundColor Yellow
    Write-Host "  MySQL Password: $(Mask-Secret $mysqlPassword)" -ForegroundColor Yellow
    Write-Host "  MySQL Database: $mysqlDb" -ForegroundColor Yellow
    Write-Host "  Database URL:   $maskedDatabaseUrl" -ForegroundColor Yellow
    Write-Host "API docs:    http://127.0.0.1:$backendPort/api/docs" -ForegroundColor Yellow
    Write-Host "Health:      http://127.0.0.1:$backendPort/health" -ForegroundColor Yellow
    Write-Host ""

    & $pythonExe -m uvicorn $startup.Value --host 127.0.0.1 --port $backendPort --reload

    $pythonExitCode = $LASTEXITCODE
    if ($pythonExitCode -ne 0) {
        throw "Backend exited with code $pythonExitCode"
    }

    exit 0
}
catch {
    Write-Host ""
    Write-Host "Failed to start backend." -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}
