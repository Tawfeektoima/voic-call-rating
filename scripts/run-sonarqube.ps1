[CmdletBinding()]
param(
    [string]$Token,
    [string]$HostUrl = "http://localhost:9000",
    [switch]$StartServer,
    [switch]$StopServer
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$composeFile = Join-Path $repoRoot "docker-compose.sonarqube.yml"
$sonarProperties = Join-Path $repoRoot "sonar-project.properties"
$sonarDataRoot = Join-Path $repoRoot ".docker\\sonarqube"
$dockerTempRoot = "D:\DockerData\sonar-temp"
$scannerWorkspaceRoot = Join-Path $dockerTempRoot "scanner-workspace"

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

function Require-Docker {
    $dockerCommand = Get-Command docker -ErrorAction SilentlyContinue
    if ($dockerCommand) {
        return
    }

    $knownDockerDir = "C:\Users\Dell\AppData\Local\Programs\DockerDesktop\resources\bin"
    $knownDockerExe = Join-Path $knownDockerDir "docker.exe"
    if (Test-Path $knownDockerExe) {
        $env:PATH = "$knownDockerDir;$env:PATH"
        return
    }

    throw "Docker is required to run SonarQube and SonarScanner from this script."
}

function Ensure-SonarDirectories {
    $paths = @(
        (Join-Path $sonarDataRoot "postgres"),
        (Join-Path $sonarDataRoot "data"),
        (Join-Path $sonarDataRoot "extensions"),
        (Join-Path $sonarDataRoot "logs")
    )

    foreach ($path in $paths) {
        New-Item -ItemType Directory -Force -Path $path | Out-Null
    }
}

function Suspend-ScannerBlockedDirectories {
    New-Item -ItemType Directory -Force -Path $dockerTempRoot | Out-Null

    $moved = @()
    $blockedFolders = @(
        @{ Source = Join-Path $repoRoot ".docker"; Dest = Join-Path $dockerTempRoot "project-dot-docker-main" },
        @{ Source = Join-Path $repoRoot ".docker_scan_tmp"; Dest = Join-Path $dockerTempRoot "project-dot-docker-tmp" },
        @{ Source = Join-Path $repoRoot ".pytest_cache"; Dest = Join-Path $dockerTempRoot "project-pytest-cache" }
    )

    $runtimeRoot = Join-Path $repoRoot ".runtime"
    if (Test-Path -LiteralPath $runtimeRoot) {
        $runtimeBlockedFolders = Get-ChildItem -LiteralPath $runtimeRoot -Directory -Force |
            Where-Object { ($_.Name -like "pytest-temp*") -or ($_.Name -eq "tmp") }

        foreach ($runtimeFolder in $runtimeBlockedFolders) {
            $blockedFolders += @{
                Source = $runtimeFolder.FullName
                Dest = Join-Path $dockerTempRoot ("runtime-" + $runtimeFolder.Name)
            }
        }
    }

    foreach ($folder in $blockedFolders) {
        if (-not (Test-Path -LiteralPath $folder.Source)) {
            continue
        }

        if (Test-Path -LiteralPath $folder.Dest) {
            Remove-Item -LiteralPath $folder.Dest -Recurse -Force
        }

        Move-Item -LiteralPath $folder.Source -Destination $folder.Dest
        $moved += $folder
    }

    return ,$moved
}

function Restore-ScannerBlockedDirectories {
    param([array]$MovedFolders)

    foreach ($folder in $MovedFolders) {
        if ((Test-Path -LiteralPath $folder.Dest) -and -not (Test-Path -LiteralPath $folder.Source)) {
            Move-Item -LiteralPath $folder.Dest -Destination $folder.Source
        }
    }
}

function Copy-SonarWorkspace {
    if (Test-Path -LiteralPath $scannerWorkspaceRoot) {
        Remove-Item -LiteralPath $scannerWorkspaceRoot -Recurse -Force
    }

    New-Item -ItemType Directory -Force -Path $scannerWorkspaceRoot | Out-Null

    $pathsToCopy = @(
        "sonar-project.properties",
        ".runtime\coverage",
        "app",
        "scripts",
        "deploy",
        "tests",
        "AI Call Center Platform\src",
        "AI Call Center Platform\tsconfig.sonar.json",
        "run_smoke_test.py",
        "setup_admin.py",
        "Dockerfile",
        "docker-compose.yml",
        "docker-compose.prod.yml",
        "docker-compose.sonarqube.yml",
        "run_platform.bat",
        "start_public_tunnel.bat"
    )

    foreach ($relativePath in $pathsToCopy) {
        $source = Join-Path $repoRoot $relativePath
        if (-not (Test-Path -LiteralPath $source)) {
            continue
        }

        $destination = Join-Path $scannerWorkspaceRoot $relativePath
        $destinationParent = Split-Path -Parent $destination
        if ($destinationParent) {
            New-Item -ItemType Directory -Force -Path $destinationParent | Out-Null
        }

        Copy-Item -LiteralPath $source -Destination $destination -Recurse -Force
    }

    return (Resolve-Path $scannerWorkspaceRoot).Path
}

if (-not (Test-Path $composeFile)) {
    throw "Cannot find docker-compose.sonarqube.yml at $composeFile"
}

if (-not (Test-Path $sonarProperties)) {
    throw "Cannot find sonar-project.properties at $sonarProperties"
}

Require-Docker
Ensure-SonarDirectories

if ($StopServer) {
    Invoke-CheckedNative -Description "Docker Compose stop" -Command {
        docker compose -f $composeFile down
    }
    Write-Host "SonarQube stack stopped."
    exit 0
}

if ($StartServer) {
    Invoke-CheckedNative -Description "Docker Compose start" -Command {
        docker compose -f $composeFile up -d
    }
    Write-Host "SonarQube stack started. Open $HostUrl and wait until the UI is healthy."
}

if ([string]::IsNullOrWhiteSpace($Token)) {
    throw "A Sonar token is required. Create one in SonarQube, then rerun: .\scripts\run-sonarqube.ps1 -Token <token>"
}

$resolvedScannerWorkspace = Copy-SonarWorkspace
$scannerHostUrl = $HostUrl `
    -replace "http://localhost", "http://host.docker.internal" `
    -replace "https://localhost", "https://host.docker.internal" `
    -replace "http://127\.0\.0\.1", "http://host.docker.internal" `
    -replace "https://127\.0\.0\.1", "https://host.docker.internal"

Invoke-CheckedNative -Description "SonarScanner Docker run" -Command {
    docker run --rm `
        -e SONAR_HOST_URL=$scannerHostUrl `
        -e SONAR_TOKEN=$Token `
        -v "${resolvedScannerWorkspace}:/usr/src" `
        sonarsource/sonar-scanner-cli:latest
}
