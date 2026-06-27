[CmdletBinding()]
param(
    [string]$RepoRoot,
    [string]$OutputPath
)

$ErrorActionPreference = "Stop"

if (-not $RepoRoot) {
    $scriptPath = $MyInvocation.MyCommand.Path
    if (-not $scriptPath) {
        throw "Unable to resolve script path."
    }
    $RepoRoot = Split-Path -Parent (Split-Path -Parent $scriptPath)
}

$sourceItems = @(
    "app",
    "scripts",
    "deploy",
    "AI Call Center Platform/src",
    "run_smoke_test.py",
    "setup_admin.py",
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.prod.yml",
    "docker-compose.sonarqube.yml",
    "run_platform.bat",
    "start_public_tunnel.bat"
)

$testItems = @(
    "tests",
    "AI Call Center Platform/src/app/__tests__",
    "AI Call Center Platform/src/app/hooks/__tests__"
)

$excludeRegexes = @(
    '(^|\\)\.git(\\|$)',
    '(^|\\)\.specify(\\|$)',
    '(^|\\)\.agents(\\|$)',
    '(^|\\)\.docker(\\|$)',
    '(^|\\)\.docker_scan_tmp(\\|$)',
    '(^|\\)node_modules(\\|$)',
    '(^|\\)\.pytest_cache(\\|$)',
    '(^|\\)dist(\\|$)',
    '(^|\\)build(\\|$)',
    '(^|\\)\.venv(\\|$)',
    '(^|\\)venv(\\|$)',
    '(^|\\)__pycache__(\\|$)',
    '(^|\\)uploads(\\|$)',
    '(^|\\)local_chroma_db(\\|$)',
    '(^|\\)scratch(\\|$)',
    '(^|\\)specs(\\|$)',
    '(^|\\)docs(\\|$)',
    '(^|\\)alembic(\\|$)'
)

$excludeExtensions = @(
    ".pyc", ".bin", ".txt", ".csv", ".png", ".jpg", ".jpeg", ".gif",
    ".webp", ".mp3", ".wav", ".ogg", ".flac", ".m4a", ".webm"
)

function Test-IsExcluded {
    param(
        [string]$RelativePath,
        [bool]$IsTestFile
    )

    foreach ($regex in $excludeRegexes) {
        if ($RelativePath -match $regex) {
            return $true
        }
    }

    if ($excludeExtensions -contains ([IO.Path]::GetExtension($RelativePath).ToLowerInvariant())) {
        return $true
    }

    if (-not $IsTestFile -and $RelativePath -match 'AI Call Center Platform\\src\\.*\\__tests__\\') {
        return $true
    }

    return $false
}

function Test-IsIncludedTestFile {
    param([string]$RelativePath)

    if ($RelativePath -like 'tests\*.py') {
        return $true
    }

    if ($RelativePath -like 'AI Call Center Platform\src\app\__tests__\*.ts') {
        return $true
    }

    if ($RelativePath -like 'AI Call Center Platform\src\app\__tests__\*.tsx') {
        return $true
    }

    if ($RelativePath -like 'AI Call Center Platform\src\app\hooks\__tests__\*.ts') {
        return $true
    }

    if ($RelativePath -like 'AI Call Center Platform\src\app\hooks\__tests__\*.tsx') {
        return $true
    }

    return $false
}

function Resolve-ProjectPath {
    param([string]$RelativePath)
    Join-Path $RepoRoot $RelativePath
}

function Get-FilesFromItems {
    param([string[]]$Items)

    foreach ($item in $Items) {
        $fullPath = Resolve-ProjectPath $item
        if (-not (Test-Path -LiteralPath $fullPath)) {
            continue
        }

        $entry = Get-Item -LiteralPath $fullPath -Force
        if ($entry.PSIsContainer) {
            Get-ChildItem -LiteralPath $fullPath -Recurse -File -Force -ErrorAction SilentlyContinue
        } else {
            $entry
        }
    }
}

$sourceFiles = Get-FilesFromItems -Items $sourceItems |
    ForEach-Object { $_.FullName.Substring($RepoRoot.Length + 1) } |
    Where-Object { -not (Test-IsExcluded -RelativePath $_ -IsTestFile:$false) } |
    Where-Object { $_ -notlike 'tests\*' } |
    Where-Object { $_ -notmatch 'AI Call Center Platform\\src\\.*\\__tests__\\' } |
    Sort-Object -Unique

$testFiles = Get-FilesFromItems -Items $testItems |
    ForEach-Object { $_.FullName.Substring($RepoRoot.Length + 1) } |
    Where-Object { -not (Test-IsExcluded -RelativePath $_ -IsTestFile:$true) } |
    Where-Object { Test-IsIncludedTestFile -RelativePath $_ } |
    Sort-Object -Unique

$reportLines = @()
$reportLines += "Sonar source files count: $($sourceFiles.Count)"
$reportLines += ""
$reportLines += "[Sources]"
$reportLines += $sourceFiles
$reportLines += ""
$reportLines += "Sonar test files count: $($testFiles.Count)"
$reportLines += ""
$reportLines += "[Tests]"
$reportLines += $testFiles

$reportText = ($reportLines -join [Environment]::NewLine)

if ($OutputPath) {
    $resolvedOutput = if ([System.IO.Path]::IsPathRooted($OutputPath)) {
        $OutputPath
    } else {
        Join-Path $RepoRoot $OutputPath
    }

    $outputDir = Split-Path -Parent $resolvedOutput
    if ($outputDir) {
        New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
    }

    Set-Content -LiteralPath $resolvedOutput -Value $reportText -Encoding UTF8
    Write-Host "Wrote Sonar scope report to $resolvedOutput"
}

$reportText
