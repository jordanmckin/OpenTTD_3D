param(
    [ValidateRange(0,359)][int]$Yaw = 0,
    [ValidateRange(40,180)][int]$Tilt = 100
)
# Open the terrain fixture with isolated settings. Does not compile or change your normal OpenTTD profile.
$ErrorActionPreference = 'Stop'
$workspace = Split-Path -Parent $PSScriptRoot
$source = Join-Path $workspace 'OpenTTD-15.3/OpenTTD-15.3'
$build = Join-Path $workspace 'build/baseline'
$demo = Join-Path $workspace '.runtime/phase2-demo'
$exe = Join-Path $build 'openttd-3d.exe'
$fixture = Join-Path $source 'docs/3d/fixtures/phase2/terrain.sav'
$baseGraphics = Join-Path $workspace '.runtime/baseline/baseset/4f474658-OpenGFX-7.1.tar'
foreach ($required in @($exe, $fixture, $baseGraphics)) {
    if (!(Test-Path -LiteralPath $required)) { throw "Missing $required. See docs/3d/phase2.md." }
}
New-Item -ItemType Directory -Force (Join-Path $demo 'baseset'),(Join-Path $demo 'scripts') | Out-Null
Copy-Item -LiteralPath $baseGraphics -Destination (Join-Path $demo 'baseset')
Copy-Item -LiteralPath (Join-Path $source 'docs/3d/fixtures/phase2/terrain.cfg') -Destination (Join-Path $demo 'openttd.cfg')
@"
scrollto instant 32 32
zoomto 3
renderer_3d on
renderer_3d camera $Yaw $Tilt
pause
"@ | Set-Content -Encoding ascii (Join-Path $demo 'scripts/game_start.scr')
Write-Host '3D terrain: renderer_3d camera 90 65; renderer_3d camera 0 100; renderer_3d viewport; renderer_3d off.'
Write-Host 'Infrastructure, buildings and vehicles are not drawn yet. Unpause before terraforming.'
Push-Location $build
try {
    & $exe -c (Join-Path $demo 'openttd.cfg') -x -X -QQ -I OpenGFX -v win32-opengl -b 32bpp-optimized -s null -m null -g $fixture
} finally {
    Pop-Location
}
