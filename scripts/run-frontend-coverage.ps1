[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$frontendRoot = Join-Path $repoRoot "AI Call Center Platform"
$runtimeCoverage = Join-Path $repoRoot ".runtime\coverage"
$frontendLcovSource = Join-Path $repoRoot ".runtime\coverage\frontend\lcov.info"
$frontendLcovTarget = Join-Path $runtimeCoverage "frontend-lcov.info"
$frontendTemp = Join-Path $repoRoot ".runtime\tmp\frontend"
$frontendCache = Join-Path $repoRoot ".runtime\tmp\npm-cache"

New-Item -ItemType Directory -Force -Path $runtimeCoverage | Out-Null
New-Item -ItemType Directory -Force -Path $frontendTemp | Out-Null
New-Item -ItemType Directory -Force -Path $frontendCache | Out-Null

function Invoke-CheckedNative {
    param(
        [Parameter(Mandatory = $true)]
        [scriptblock]$Command,
        [Parameter(Mandatory = $true)]
        [string]$Description
    )

    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Description failed with exit code $LASTEXITCODE."
    }
}

$env:TMP = $frontendTemp
$env:TEMP = $frontendTemp
$env:npm_config_cache = $frontendCache

Push-Location $frontendRoot
try {
    Invoke-CheckedNative -Description "Frontend coverage test suite" -Command {
        npm run test:coverage
    }
}
finally {
    Pop-Location
}

if (-not (Test-Path $frontendLcovSource)) {
    throw "Frontend LCOV report not found at $frontendLcovSource"
}

Copy-Item -LiteralPath $frontendLcovSource -Destination $frontendLcovTarget -Force
