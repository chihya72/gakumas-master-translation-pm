[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$repository = Split-Path -Parent $PSScriptRoot
$campus = Join-Path $repository 'tools\campus'
$binary = Join-Path $campus 'campus.exe'
$cache = Join-Path $campus 'cache'
$versionFile = Join-Path $repository 'gakumasu-diff\master-version.txt'
$generatedVersion = Join-Path $cache 'master_version'

if (-not $env:CAMPUS_REFRESH_TOKEN) {
    throw 'Set the GitHub Actions secret CAMPUS_REFRESH_TOKEN before running this workflow.'
}
if (-not (Test-Path -LiteralPath $binary)) { throw 'Build tools\campus\campus.exe first.' }
$env:CAMPUS_MASTER_VERSION = ''
if (Test-Path -LiteralPath $versionFile) {
    $env:CAMPUS_MASTER_VERSION = (Get-Content -LiteralPath $versionFile -Raw).Trim()
}
if (Test-Path -LiteralPath $generatedVersion) {
    Remove-Item -LiteralPath $generatedVersion -Force
}
# Clear only generated master data. The same ignored cache may hold a local
# encrypted account credential or a portable build toolchain.
foreach ($name in @('masterRaw','masterYaml')) {
    $generatedFolder = Join-Path $cache $name
    if (Test-Path -LiteralPath $generatedFolder) {
        $resolvedFolder = (Resolve-Path -LiteralPath $generatedFolder).Path
        $expectedFolder = Join-Path (Resolve-Path -LiteralPath $campus).Path ('cache\' + $name)
        if ($resolvedFolder -ne $expectedFolder) { throw 'Generated cache path is outside tools\campus' }
        Remove-Item -LiteralPath $resolvedFolder -Recurse -Force
    }
}

Push-Location -LiteralPath $campus
try {
    [string[]]$arguments = @()
    & $binary @arguments
    if ($LASTEXITCODE -ne 0) { throw 'Downloading master data failed' }
} finally {
    Pop-Location
}

if (-not (Test-Path -LiteralPath $generatedVersion)) {
    Write-Output 'Game master data is already up to date.'
    if ($env:GITHUB_OUTPUT) { Add-Content -LiteralPath $env:GITHUB_OUTPUT -Value 'changed=false' }
    return
}

$yamlSource = Join-Path $cache 'masterYaml'
$destination = Join-Path $repository 'gakumasu-diff\orig'
if (-not (Test-Path -LiteralPath $destination -PathType Container)) { throw "Missing destination: $destination" }
$sourceFiles = @(Get-ChildItem -LiteralPath $yamlSource -File -Filter '*.yaml')
if ($sourceFiles.Count -eq 0) { throw "No generated YAML files in $yamlSource" }
$sourceNames = @($sourceFiles.Name)
foreach ($file in $sourceFiles) {
    Copy-Item -LiteralPath $file.FullName -Destination (Join-Path $destination $file.Name) -Force
}
foreach ($file in @(Get-ChildItem -LiteralPath $destination -File -Filter '*.yaml')) {
    if ($file.Name -notin $sourceNames) { Remove-Item -LiteralPath $file.FullName -Force }
}
Copy-Item -LiteralPath $generatedVersion -Destination $versionFile -Force
if ($env:GITHUB_OUTPUT) { Add-Content -LiteralPath $env:GITHUB_OUTPUT -Value 'changed=true' }
Write-Output 'Updated gakumasu-diff\orig YAML. Convert JSON locally after pulling.'
