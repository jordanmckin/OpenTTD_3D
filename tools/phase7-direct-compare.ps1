param([int]$Windows = 3, [string]$Camera = '')
# Phase 7 priority 8: the same paused frame in direct and readback presentation; screenshots are compared pixel by pixel.
$ErrorActionPreference = 'Stop'
$workspace = Split-Path -Parent $PSScriptRoot
$build = Join-Path $workspace 'build/baseline'
$fixture = Join-Path $workspace 'OpenTTD-15.3/OpenTTD-15.3/docs/3d/fixtures'
$exe = Join-Path $build 'phase7-direct-compare-console.exe'
Copy-Item "$build/Release/openttd.exe" $exe
& 'C:/Program Files (x86)/Microsoft Visual Studio/2022/BuildTools/VC/Tools/MSVC/14.44.35207/bin/Hostx64/x64/editbin.exe' /nologo /subsystem:console $exe
foreach ($mode in @('optimized','readback')) {
    $run = Join-Path $workspace ".runtime/phase7-direct-compare-$mode"
    Remove-Item -Recurse -Force $run -ErrorAction SilentlyContinue
    New-Item -ItemType Directory -Force "$run/baseset","$run/lang","$run/scripts" | Out-Null
    Copy-Item "$build/baseset/*" "$run/baseset"
    Copy-Item "$build/lang/*.lng" "$run/lang"
    Copy-Item "$workspace/.runtime/baseline/baseset/*.tar" "$run/baseset"
    (Get-Content -Raw "$fixture/phase6/coverage.cfg") | Set-Content -Encoding ascii "$run/openttd.cfg"
    $cam = if ($Camera) { "renderer_3d camera $Camera" } else { '' }
    @"
pause
renderer_3d on
renderer_3d performance $mode
$cam
scrollto instant 29 33
zoomto 2
renderer_3d vehiclewindows $Windows
screenshot phase7-direct-compare
quit
"@ | Set-Content -Encoding ascii "$run/scripts/game_start.scr"
    $arguments = '-c "{0}" -x -X -QQ -I OpenGFX -v win32-opengl -b 32bpp-optimized -s null -m null -d driver=1 -g "{1}"' -f "$run/openttd.cfg", "$fixture/phase4/infrastructure.sav"
    $p = Start-Process $exe -ArgumentList $arguments -WorkingDirectory $build -WindowStyle Hidden -PassThru -RedirectStandardOutput "$run/stdout.log" -RedirectStandardError "$run/stderr.log"
    if (!$p.WaitForExit(120000)) { $p.Kill(); throw "Timed out: $mode" }
}
python "$PSScriptRoot/compare-screenshots.py" "$workspace/.runtime/phase7-direct-compare-optimized/screenshot/phase7-direct-compare.bmp" "$workspace/.runtime/phase7-direct-compare-readback/screenshot/phase7-direct-compare.bmp" "$workspace/.runtime/phase7-direct-compare-diff.png"
