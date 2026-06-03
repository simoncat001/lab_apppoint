# Build the project images and push them to a private Harbor registry.
#
# Only two images now:
#   - nemo-backend (FastAPI, also serves /security-api/api/* in-process)
#   - nemo-ui (single nginx image; vue-router handles both / and /security/*)
#
# Usage:
#   .\build-and-push.ps1
#   $env:TAG="v0.1.0"; .\build-and-push.ps1
#   $env:USE_STAGED_BASE_IMAGES="1"; .\build-and-push.ps1
[CmdletBinding()]
param(
    [string]$Registry = $(if ($env:REGISTRY) { $env:REGISTRY } else { "harbor.local:8088" }),
    [string]$Project  = $(if ($env:PROJECT)  { $env:PROJECT  } else { "oppointments-system" }),
    [string]$Tag      = $(if ($env:TAG)      { $env:TAG      } else { "latest" }),
    [string]$BaseProject = $(if ($env:BASE_PROJECT) { $env:BASE_PROJECT } else { "library" }),
    [string]$UseStagedBaseImages = $(if ($env:USE_STAGED_BASE_IMAGES) { $env:USE_STAGED_BASE_IMAGES } else { "" }),
    [string]$BackendBaseImage = $(if ($env:BACKEND_BASE_IMAGE) { $env:BACKEND_BASE_IMAGE } else { "" }),
    [string]$NodeBaseImage = $(if ($env:NODE_BASE_IMAGE) { $env:NODE_BASE_IMAGE } else { "" }),
    [string]$NginxBaseImage = $(if ($env:NGINX_BASE_IMAGE) { $env:NGINX_BASE_IMAGE } else { "" })
)

$ErrorActionPreference = "Stop"
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")

if ($UseStagedBaseImages) {
    if (-not $BackendBaseImage) { $BackendBaseImage = "$Registry/$BaseProject/continuumio/miniconda3:latest" }
    if (-not $NodeBaseImage)    { $NodeBaseImage    = "$Registry/$BaseProject/node:20-alpine" }
    if (-not $NginxBaseImage)   { $NginxBaseImage   = "$Registry/$BaseProject/nginx:1.27-alpine" }
}

Write-Host "==> Logging in to $Registry"
docker login $Registry
if ($LASTEXITCODE -ne 0) { throw "docker login failed" }

function BuildAndPush {
    param(
        [Parameter(Mandatory)] [string] $Name,
        [Parameter(Mandatory)] [string] $Context,
        [Parameter(Mandatory)] [string] $Dockerfile,
        [string[]] $BuildArgs
    )
    $image = "$Registry/$Project/${Name}:$Tag"
    Write-Host ""
    Write-Host "==> Building $image"
    docker build @BuildArgs -f $Dockerfile -t $image $Context
    if ($LASTEXITCODE -ne 0) { throw "docker build failed for $Name" }
    Write-Host "==> Pushing  $image"
    docker push $image
    if ($LASTEXITCODE -ne 0) { throw "docker push failed for $Name" }
}

# ---------- nemo-backend ----------
$backendArgs = @()
if ($BackendBaseImage) { $backendArgs += @("--build-arg", "BASE_IMAGE=$BackendBaseImage") }
BuildAndPush -Name "nemo-backend" `
             -Context (Join-Path $repoRoot "backend") `
             -Dockerfile (Join-Path $repoRoot "backend/Dockerfile") `
             -BuildArgs $backendArgs

# ---------- nemo-ui (single SPA; staff routes are under /security/*) ----------
$uiArgs = @()
if ($NodeBaseImage)  { $uiArgs += @("--build-arg", "NODE_BASE_IMAGE=$NodeBaseImage") }
if ($NginxBaseImage) { $uiArgs += @("--build-arg", "NGINX_BASE_IMAGE=$NginxBaseImage") }
BuildAndPush -Name "nemo-ui" `
             -Context (Join-Path $repoRoot "ui") `
             -Dockerfile (Join-Path $repoRoot "ui/Dockerfile") `
             -BuildArgs $uiArgs

Write-Host ""
Write-Host "All images pushed:"
Write-Host "  $Registry/$Project/nemo-backend:$Tag"
Write-Host "  $Registry/$Project/nemo-ui:$Tag"
