[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Token,
    [string]$HostUrl = "http://localhost:9000"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$coverageDir = Join-Path $repoRoot ".runtime\coverage"
$scopeReportPath = Join-Path $repoRoot ".runtime\sonar-scope.txt"
$dockerTempRoot = "D:\DockerData\sonar-temp"
$dockerDesktopBin = "C:\Users\Dell\AppData\Local\Programs\DockerDesktop\resources\bin"

New-Item -ItemType Directory -Force -Path $coverageDir | Out-Null
New-Item -ItemType Directory -Force -Path $dockerTempRoot | Out-Null

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

if (Test-Path (Join-Path $dockerDesktopBin "docker.exe")) {
    $env:PATH = "$dockerDesktopBin;$env:PATH"
}

Invoke-CheckedNative -Description "Sonar scope listing" -Command {
    powershell -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "list-sonar-scope.ps1") -OutputPath $scopeReportPath
}

Invoke-CheckedNative -Description "Backend coverage generation" -Command {
    powershell -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "run-backend-coverage.ps1")
}

Invoke-CheckedNative -Description "Frontend coverage generation" -Command {
    powershell -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "run-frontend-coverage.ps1")
}

$moved = @()
$dockerFolders = @(
    @{ Source = Join-Path $repoRoot ".docker"; Dest = Join-Path $dockerTempRoot "project-dot-docker-main" },
    @{ Source = Join-Path $repoRoot ".docker_scan_tmp"; Dest = Join-Path $dockerTempRoot "project-dot-docker-tmp" }
)

foreach ($folder in $dockerFolders) {
    if (Test-Path $folder.Source) {
        if (Test-Path $folder.Dest) {
            Remove-Item -LiteralPath $folder.Dest -Recurse -Force
        }
        Move-Item -LiteralPath $folder.Source -Destination $folder.Dest
        $moved += $folder
    }
}

try {
    Invoke-CheckedNative -Description "SonarQube scan" -Command {
        powershell -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "run-sonarqube.ps1") -Token $Token -HostUrl $HostUrl
    }
}
finally {
    foreach ($folder in $moved) {
        if ((Test-Path $folder.Dest) -and -not (Test-Path $folder.Source)) {
            Move-Item -LiteralPath $folder.Dest -Destination $folder.Source
        }
    }
}
