[CmdletBinding()]
param(
    [switch]$Demo,
    [switch]$NoStart,
    [string]$EnvFile
)

$ErrorActionPreference = 'Stop'
$env:COMPOSE_HTTP_TIMEOUT = '300'
$env:DOCKER_CLIENT_TIMEOUT = '300'

$root = $PSScriptRoot
$template = Join-Path $root 'env-templates\.env.ce.template'
$composeFile = Join-Path $root 'docker-compose.ce.yaml'
$envPath = if ($EnvFile) {
    [System.IO.Path]::GetFullPath($EnvFile)
} else {
    Join-Path $root '.env.ce'
}

if (-not (Test-Path -LiteralPath $template -PathType Leaf)) {
    throw "CE env template not found: $template"
}
if (-not (Test-Path -LiteralPath $composeFile -PathType Leaf)) {
    throw "CE compose file not found: $composeFile"
}

if (-not (Test-Path -LiteralPath $envPath -PathType Leaf)) {
    Copy-Item -LiteralPath $template -Destination $envPath
    Write-Host "Created $envPath"
}

$lines = @(Get-Content -LiteralPath $envPath)
$jwtLine = $lines |
    Where-Object { $_ -match '^\s*FY_JWT_SECRET\s*=' } |
    Select-Object -First 1
$jwtValue = if ($null -ne $jwtLine) {
    ($jwtLine -split '=', 2)[1].Trim()
} else {
    ''
}

if ([string]::IsNullOrWhiteSpace($jwtValue) -or $jwtValue -match '^REPLACE') {
    $bytes = New-Object byte[] 32
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $rng.GetBytes($bytes)
    } finally {
        $rng.Dispose()
    }
    $jwtValue = ($bytes | ForEach-Object { $_.ToString('x2') }) -join ''

    $foundJwt = $false
    $lines = @(
        foreach ($line in $lines) {
            if ($line -match '^\s*FY_JWT_SECRET\s*=') {
                $foundJwt = $true
                "FY_JWT_SECRET=$jwtValue"
            } else {
                $line
            }
        }
    )
    if (-not $foundJwt) {
        $lines += "FY_JWT_SECRET=$jwtValue"
    }
    Write-Host 'Generated a new 64-character hexadecimal JWT secret.'
} else {
    Write-Host 'Keeping the existing JWT secret.'
}

$demoValue = if ($Demo) { 'true' } else { 'false' }
$foundDemo = $false
$lines = @(
    foreach ($line in $lines) {
        if ($line -match '^\s*FY_DEMO_QUICK_LOGIN\s*=') {
            $foundDemo = $true
            "FY_DEMO_QUICK_LOGIN=$demoValue"
        } else {
            $line
        }
    }
)
if (-not $foundDemo) {
    $lines += "FY_DEMO_QUICK_LOGIN=$demoValue"
}
if ($Demo) {
    Write-Host 'Enabled quick demo login for this local environment.'
} else {
    Write-Host 'Quick demo login is disabled.'
}

$imageDefaults = [ordered]@{
    FY_FRONTEND_IMAGE = 'ghcr.nju.edu.cn/angshihan777-droid/feiyu-frontend-ce:snapshot-ce'
    FY_BACKEND_IMAGE = 'ghcr.nju.edu.cn/angshihan777-droid/feiyu-backend-ce:snapshot-ce'
    FY_POSTGRES_IMAGE = 'ghcr.nju.edu.cn/ferretdb/postgres-documentdb:17-0.105.0-ferretdb-2.4.0'
    FY_FERRETDB_IMAGE = 'ghcr.nju.edu.cn/ferretdb/ferretdb:2.4.0'
}
foreach ($item in $imageDefaults.GetEnumerator()) {
    $pattern = "^\s*$([regex]::Escape($item.Key))\s*="
    if (-not ($lines | Where-Object { $_ -match $pattern })) {
        $lines += "$($item.Key)=$($item.Value)"
    }
}

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllLines($envPath, [string[]]$lines, $utf8NoBom)

if ($NoStart) {
    Write-Host "Environment is ready: $envPath"
    exit 0
}

$started = $false
$retries = 6
for ($attempt = 1; $attempt -le $retries; $attempt++) {
    & docker compose --env-file $envPath -f $composeFile up -d --remove-orphans
    if ($LASTEXITCODE -eq 0) {
        $started = $true
        break
    }
    if ($attempt -lt $retries) {
        $delay = [Math]::Min(30, $attempt * 5)
        Write-Warning "Docker pull/start attempt $attempt failed; retrying in $delay seconds."
        Start-Sleep -Seconds $delay
    }
}
if (-not $started) {
    throw "Docker Compose could not start the CE services after $retries attempts. Check the network and retry."
}

& docker compose --env-file $envPath -f $composeFile ps

Write-Host ''
Write-Host 'feiyu-openlabel CE is running:'
Write-Host '  http://localhost:6600/guis/feiyu/auth.html'
if ($Demo) {
Write-Host 'Quick demo login is enabled. Choose an identity on the login page.'
} else {
    Write-Host 'Quick demo login is disabled. Use the normal email/password login.'
}
