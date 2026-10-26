[CmdletBinding()]
param(
    [switch]$Yes,
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
if (Get-Variable PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue) {
    # PowerShell 7 can turn expected stderr from missing Docker objects into
    # terminating NativeCommandError exceptions.
    $PSNativeCommandUseErrorActionPreference = $false
}

$root = $PSScriptRoot
$envPath = Join-Path $root '.env.ce'
$composeFile = Join-Path $root 'docker-compose.ce.yaml'
$containers = @(
    'feiyu-ce-web-app',
    'feiyu-ce-web-api',
    'feiyu-ce-ferretdb',
    'feiyu-ce-redis',
    'feiyu-ce-postgres'
)
$images = @(
    'ghcr.nju.edu.cn/angshihan777-droid/feiyu-frontend-ce:snapshot-ce',
    'ghcr.nju.edu.cn/angshihan777-droid/feiyu-backend-ce:snapshot-ce',
    'ghcr.nju.edu.cn/angshihan777-droid/feiyu-frontend-ce:latest-ce',
    'ghcr.nju.edu.cn/angshihan777-droid/feiyu-backend-ce:latest-ce',
    'ghcr.io/angshihan777-droid/feiyu-frontend-ce:snapshot-ce',
    'ghcr.io/angshihan777-droid/feiyu-backend-ce:snapshot-ce',
    'ghcr.io/angshihan777-droid/feiyu-frontend-ce:latest-ce',
    'ghcr.io/angshihan777-droid/feiyu-backend-ce:latest-ce',
    'ghcr.nju.edu.cn/ferretdb/postgres-documentdb:17-0.105.0-ferretdb-2.4.0',
    'ghcr.nju.edu.cn/ferretdb/ferretdb:2.4.0',
    'ghcr.io/ferretdb/postgres-documentdb:17-0.105.0-ferretdb-2.4.0',
    'ghcr.io/ferretdb/ferretdb:2.4.0',
    'redis:7.4.10-alpine'
)
$dataDirs = @(
    'feiyu_ce_user_data',
    'feiyu_ce_media',
    'feiyu_ce_logs',
    'feiyu_ce_redis_data',
    'feiyu_ce_postgres_data'
) | ForEach-Object { Join-Path ([Environment]::GetFolderPath('UserProfile')) "tmp\$_" }

$imageRefs = @(
    & docker image ls --format '{{.Repository}}:{{.Tag}}' 2>$null |
        Where-Object { $_ -match 'feiyu-(frontend|backend)-ce:' }
)
$images = @($images + $imageRefs | Sort-Object -Unique)

if (-not $Yes -and -not $DryRun) {
    Write-Host 'This will permanently remove the feiyu-openlabel CE containers, images, data and local JWT secret.'
    Write-Host 'Source code under D:\feiyu-openlabel is kept.'
    $answer = Read-Host 'Type DELETE to continue'
    if ($answer -cne 'DELETE') {
        Write-Host 'Cancelled.'
        exit 0
    }
}

if ($DryRun) {
    Write-Host 'DRY RUN: no resources will be removed.'
    Write-Host 'Containers:'
    $containers | ForEach-Object { Write-Host "  $_" }
    Write-Host 'Images:'
    $images | ForEach-Object { Write-Host "  $_" }
    Write-Host 'Data directories:'
    $dataDirs | ForEach-Object { Write-Host "  $_" }
    Write-Host "Env file: $envPath"
    exit 0
}

if (Test-Path -LiteralPath $envPath -PathType Leaf) {
    & docker compose --env-file $envPath -f $composeFile down --rmi all --remove-orphans -v
    if ($LASTEXITCODE -ne 0) {
        Write-Warning 'docker compose down failed; falling back to exact resource names.'
    }
}

$existingContainers = @(& docker ps -a --format '{{.Names}}' 2>$null)
foreach ($container in $containers) {
    if ($existingContainers -contains $container) {
        & docker rm -f $container *> $null
        Write-Host "Removed container $container"
    }
}

$existingImages = @(& docker image ls --format '{{.Repository}}:{{.Tag}}' 2>$null)
foreach ($image in $images) {
    if ($existingImages -contains $image) {
        & docker image rm -f $image *> $null
        Write-Host "Removed image $image"
    }
}

$networkName = 'docker-production_feiyu-ce-network'
$existingNetworks = @(& docker network ls --format '{{.Name}}' 2>$null)
if ($existingNetworks -contains $networkName) {
    & docker network rm $networkName *> $null
    Write-Host 'Removed Docker network docker-production_feiyu-ce-network'
}

$expectedRoot = [System.IO.Path]::GetFullPath(
    (Join-Path ([Environment]::GetFolderPath('UserProfile')) 'tmp')
).TrimEnd('\') + '\'
foreach ($target in $dataDirs) {
    $resolved = [System.IO.Path]::GetFullPath($target)
    if (-not $resolved.StartsWith($expectedRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to delete outside expected root: $resolved"
    }
    if ([System.IO.Directory]::Exists($resolved)) {
        [System.IO.Directory]::Delete($resolved, $true)
        Write-Host "Removed data directory $resolved"
    }
}

if ([System.IO.File]::Exists($envPath)) {
    [System.IO.File]::Delete($envPath)
    Write-Host "Removed local config $envPath"
}

Write-Host ''
Write-Host 'feiyu-openlabel CE was removed. Source code was kept.'
