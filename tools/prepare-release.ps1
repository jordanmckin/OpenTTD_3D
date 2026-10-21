param([string]$BuildDirectory = "$PSScriptRoot/../build/baseline")
$ErrorActionPreference = 'Stop'
$workspace = Split-Path -Parent $PSScriptRoot
$build = (Resolve-Path -LiteralPath $BuildDirectory).Path
$release = Join-Path $build 'Release'
if (!(Test-Path -LiteralPath "$release/openttd.exe")) { throw 'Build the Release executable first.' }
# Multi-config builds put generated data one directory above the executable.
# Stage matching data beside it so Explorer double-click startup also works.
foreach ($folder in @('lang','baseset','ai','game')) {
    if (Test-Path -LiteralPath "$build/$folder") {
        New-Item -ItemType Directory -Force "$release/$folder" | Out-Null
        Copy-Item "$build/$folder/*" -Destination "$release/$folder" -Recurse -Force
    }
}
# Keep the already installed OpenGFX archive, including its bundled notices.
Get-ChildItem -LiteralPath "$workspace/.runtime/baseline/baseset" -Filter '*.tar' | Copy-Item -Destination "$release/baseset" -Force
Write-Host "Ready for double-click startup: $release/openttd.exe"
