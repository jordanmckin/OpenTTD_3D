param([switch]$Show)
# Interactive rotated-management review, isolated from the user's configuration and saves.
$ErrorActionPreference = 'Stop'
$workspace = Split-Path -Parent $PSScriptRoot
$build = Join-Path $workspace 'build/baseline'
$fixture = Join-Path $workspace 'OpenTTD-15.3/OpenTTD-15.3/docs/3d/fixtures'
$demo = Join-Path $workspace '.runtime/phase95e-demo'
New-Item -ItemType Directory -Force "$demo/baseset","$demo/lang","$demo/scripts","$demo/ai/infrastructure3d" | Out-Null
Copy-Item "$build/baseset/*" "$demo/baseset"
Copy-Item "$build/lang/*.lng" "$demo/lang"
Copy-Item "$workspace/.runtime/baseline/baseset/*.tar" "$demo/baseset"
Copy-Item "$fixture/phase4/ai/*.nut" "$demo/ai/infrastructure3d"
Copy-Item "$fixture/phase6/coverage.cfg" "$demo/openttd.cfg"
@'
renderer_3d on
renderer_3d lod off
renderer_3d shadows contact
setting gui.renderer_3d_auto_visibility true
setting construction.command_pause_level 3
scrollto instant 29 33
zoomto 2
renderer_3d camera 45 80
pause
'@ | Set-Content -Encoding ascii "$demo/scripts/game_start.scr"
$arguments = '-c "{0}" -x -X -QQ -I OpenGFX -v win32-opengl -b 32bpp-optimized -s null -m null -g "{1}"' -f "$demo/openttd.cfg","$fixture/phase4/infrastructure.sav"
$style = if ($Show) { 'Normal' } else { 'Hidden' }
Start-Process "$build/Release/openttd.exe" -ArgumentList $arguments -WorkingDirectory $build -WindowStyle $style | Out-Null
Write-Host 'Rotated management: build at this angle, select vehicles and labels, and zoom under the pointer.'
Write-Host 'Comma/period rotate; Page Up/Down tilt; Ctrl+drag orbits; Home switches to/from classic.'
Write-Host 'Starts paused with construction allowed. Use -Show for a visible interactive review.'
