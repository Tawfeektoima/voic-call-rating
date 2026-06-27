[CmdletBinding()]
param(
    [string]$PythonExe = "D:\voic call rating\.venv\Scripts\python.exe"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$coverageDir = Join-Path $repoRoot ".runtime\coverage"
$coverageXml = Join-Path $coverageDir "python-coverage.xml"
$runStamp = Get-Date -Format "yyyyMMddHHmmss"
$pytestTemp = Join-Path $repoRoot ".runtime\pytest-temp-$runStamp"
$performancePytestTemp = Join-Path $repoRoot ".runtime\pytest-temp-performance-$runStamp"
$systemTemp = Join-Path $repoRoot ".runtime\tmp\pytest"

New-Item -ItemType Directory -Force -Path $coverageDir | Out-Null
New-Item -ItemType Directory -Force -Path $pytestTemp | Out-Null
New-Item -ItemType Directory -Force -Path $systemTemp | Out-Null

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

$env:TMP = $systemTemp
$env:TEMP = $systemTemp

Invoke-CheckedNative -Description "Recording ingestion performance test" -Command {
    & $PythonExe -m pytest `
        --basetemp="$performancePytestTemp" `
        tests\test_recording_ingestion_worker.py::test_scheduled_worker_processes_100_records_with_bounded_download_concurrency
}

Invoke-CheckedNative -Description "Backend coverage test suite" -Command {
    & $PythonExe -m pytest `
        --basetemp="$pytestTemp" `
        --cov-config="$repoRoot\.coveragerc" `
        --cov=. `
        --cov-report="xml:$coverageXml" `
        --cov-report=term-missing `
        -k "not test_scheduled_worker_processes_100_records_with_bounded_download_concurrency" `
        tests
}
