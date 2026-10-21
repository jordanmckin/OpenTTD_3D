# Launch the local rendering proof with isolated settings and the Phase 0 map.
$ErrorActionPreference = 'Stop'
$workspace = Split-Path -Parent $PSScriptRoot
$source = Join-Path $workspace 'OpenTTD-15.3/OpenTTD-15.3'
$build = Join-Path $workspace 'build/baseline'
$demo = Join-Path $workspace '.runtime/phase1-demo'
$exe = Join-Path $build 'Release/openttd.exe'
$baseGraphics = Join-Path $workspace '.runtime/baseline/baseset/4f474658-OpenGFX-7.1.tar'
if (!(Test-Path -LiteralPath $exe)) { throw 'Build with OPTION_3D_PROOF=ON first; see docs/3d/phase1.md.' }
if (!(Test-Path -LiteralPath $baseGraphics)) { throw 'OpenGFX base data is missing; follow the Phase 0 base-data setup.' }
New-Item -ItemType Directory -Force (Join-Path $demo 'baseset'),(Join-Path $demo 'scripts') | Out-Null
Copy-Item -LiteralPath $baseGraphics -Destination (Join-Path $demo 'baseset')
Copy-Item -LiteralPath (Join-Path $source 'docs/3d/fixtures/baseline.cfg') -Destination (Join-Path $demo 'openttd.cfg')
@'
scrollto instant 32 32
zoomto 2
renderer_3d on
pause
'@ | Set-Content -Encoding ascii (Join-Path $demo 'scripts/game_start.scr')
Write-Host 'Legacy Phase 0 fixture. The current renderer now displays real terrain.'
Write-Host 'Use tools/phase2-demo.ps1 for the coastal terrain demo and camera controls.'
Push-Location $build
try {
    & $exe -c (Join-Path $demo 'openttd.cfg') -x -X -QQ -I OpenGFX -v win32-opengl -b 32bpp-optimized -s null -m null -g (Join-Path $source 'docs/3d/fixtures/phase0-baseline.sav')
} finally {
    Pop-Location
}
