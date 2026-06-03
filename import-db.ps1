param(
    [string]$MysqlExe = "",
    [string]$MysqlHost = "127.0.0.1",
    [int]$MysqlPort = 3306,
    [string]$MysqlUser = "root",
    [string]$MysqlPassword = "123456",
    [string]$AppDump = "db-dumps\szlab_appoint_local_overwrite_20260302_183136.sql"
)

$ErrorActionPreference = "Stop"

function Get-MysqlExecutable {
    param(
        [string]$ExplicitPath = ""
    )

    if (-not [string]::IsNullOrWhiteSpace($ExplicitPath)) {
        if (-not (Test-Path $ExplicitPath)) {
            throw "mysql executable not found: $ExplicitPath"
        }

        return (Resolve-Path $ExplicitPath).Path
    }

    $command = Get-Command mysql.exe -ErrorAction SilentlyContinue
    if ($null -eq $command) {
        $command = Get-Command mysql -ErrorAction SilentlyContinue
    }
    if ($null -ne $command) {
        return $command.Source
    }

    $candidates = @(
        "C:\Program Files\MySQL\MySQL Server 9.5\bin\mysql.exe",
        "C:\Program Files\MySQL\MySQL Server 9.4\bin\mysql.exe",
        "C:\Program Files\MySQL\MySQL Server 8.4\bin\mysql.exe",
        "C:\Program Files\MySQL\MySQL Server 8.3\bin\mysql.exe",
        "C:\Program Files\MySQL\MySQL Server 8.2\bin\mysql.exe",
        "C:\Program Files\MySQL\MySQL Server 8.1\bin\mysql.exe",
        "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe",
        "C:\Program Files (x86)\MySQL\MySQL Server 8.0\bin\mysql.exe",
        "C:\Program Files\MariaDB 11.4\bin\mysql.exe",
        "C:\Program Files\MariaDB 11.3\bin\mysql.exe",
        "C:\Program Files\MariaDB 11.2\bin\mysql.exe",
        "C:\Program Files\MariaDB 11.1\bin\mysql.exe",
        "C:\Program Files\MariaDB 11.0\bin\mysql.exe",
        "C:\Program Files\MariaDB 10.11\bin\mysql.exe"
    )

    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) {
            return $candidate
        }
    }

    throw "mysql was not found in PATH and no common install path matched. Use -MysqlExe `"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe`"."
}

function Invoke-MysqlImport {
    param(
        [Parameter(Mandatory = $true)]
        [string]$MysqlExe,
        [Parameter(Mandatory = $true)]
        [string]$DumpPath,
        [Parameter(Mandatory = $true)]
        [string]$Label
    )

    if (-not (Test-Path $DumpPath)) {
        throw "$Label dump not found: $DumpPath"
    }

    Write-Host "Importing $Label..." -ForegroundColor Yellow
    $command = "`"$MysqlExe`" -h $MysqlHost -P $MysqlPort -u $MysqlUser < `"$DumpPath`""
    cmd.exe /c $command
    if ($LASTEXITCODE -ne 0) {
        throw "$Label import failed with exit code $LASTEXITCODE."
    }
}

try {
    $repoRoot = $PSScriptRoot
    $mysqlExe = Get-MysqlExecutable -ExplicitPath $MysqlExe
    $appDumpPath = Join-Path $repoRoot $AppDump

    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "NEMO Database Import" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "MySQL: $MysqlUser@$MysqlHost`:$MysqlPort" -ForegroundColor Green
    Write-Host "App dump: $appDumpPath" -ForegroundColor Green
    Write-Host ""
    Write-Host "Note: the legacy security-server schema is gone. Staff tables (staff_*)" -ForegroundColor DarkYellow
    Write-Host "now live inside the szlab_appoint database and are created automatically" -ForegroundColor DarkYellow
    Write-Host "by the backend on first start." -ForegroundColor DarkYellow
    Write-Host ""
    Write-Host "This will overwrite the existing database if the dump contains DROP DATABASE." -ForegroundColor Yellow
    Write-Host ""

    $confirmation = Read-Host "Continue import? (y/N)"
    if ($confirmation -notin @("y", "Y")) {
        Write-Host "Import cancelled." -ForegroundColor Red
        exit 1
    }

    $previousPassword = $env:MYSQL_PWD
    $env:MYSQL_PWD = $MysqlPassword

    try {
        Invoke-MysqlImport -MysqlExe $mysqlExe -DumpPath $appDumpPath -Label "szlab_appoint"

        Write-Host ""
        Write-Host "Import completed." -ForegroundColor Green
        Write-Host ""
        & $mysqlExe -h $MysqlHost -P $MysqlPort -u $MysqlUser -e "SHOW DATABASES LIKE 'szlab_appoint';"
    }
    finally {
        if ($null -eq $previousPassword) {
            Remove-Item Env:MYSQL_PWD -ErrorAction SilentlyContinue
        }
        else {
            $env:MYSQL_PWD = $previousPassword
        }
    }
}
catch {
    Write-Host ""
    Write-Host "Failed to import databases." -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}
