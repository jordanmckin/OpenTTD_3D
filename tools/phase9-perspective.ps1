param([string]$RunTag = 'phase9-perspective', [switch]$Fleet)
# Phase 9.2: still perspective cameras in vehicle windows, on the Phase 4 railway fixture.
# Step 0 compares views within one game tick; later steps capture one large window from several placements.
# -Fleet uses the 512x512 Phase 7 fleet map instead, where the draw distance and fog cut off most of the map.
$ErrorActionPreference = 'Stop'
$workspace = Split-Path -Parent $PSScriptRoot
$build = Join-Path $workspace 'build/baseline'
$fixture = Join-Path $workspace 'OpenTTD-15.3/OpenTTD-15.3/docs/3d/fixtures'
if ($Fleet) { $RunTag += '-fleet' }
$run = Join-Path $workspace ".runtime/$RunTag"
$exe = Join-Path $build "$RunTag-console.exe"
Copy-Item "$build/Release/openttd.exe" $exe
& 'C:/Program Files (x86)/Microsoft Visual Studio/2022/BuildTools/VC/Tools/MSVC/14.44.35207/bin/Hostx64/x64/editbin.exe' /nologo /subsystem:console $exe
if ($LASTEXITCODE -ne 0) { throw 'editbin failed' }
if (Test-Path "$run/screenshot") { Remove-Item -Recurse -Force "$run/screenshot" }
New-Item -ItemType Directory -Force "$run/baseset","$run/lang","$run/scripts","$run/ai/infrastructure3d" | Out-Null
Copy-Item "$build/baseset/*" "$run/baseset"
Copy-Item "$build/lang/*.lng" "$run/lang"
Copy-Item "$workspace/.runtime/baseline/baseset/*.tar" "$run/baseset"
Copy-Item "$fixture/phase4/ai/*.nut" "$run/ai/infrastructure3d"
if ($Fleet) {
    New-Item -ItemType Directory -Force "$run/ai/fleet3d" | Out-Null
    Copy-Item "$fixture/phase7/fleet/ai/*.nut" "$run/ai/fleet3d"
}
Get-Content -Raw "$fixture/phase6/coverage.cfg" | Set-Content -Encoding ascii "$run/openttd.cfg"
@"
renderer_3d on
renderer_3d verifygpu on
setting gui.show_finances false
scrollto instant $(if ($Fleet) { '256 256' } else { '29 33' })
zoomto 2
renderer_3d vehiclewindows 4
setting gui.fast_forward_speed_limit 2000
renderer_3d fastforward on
unpause
schedule on-next-calendar-month scripts/step0.scr
"@ | Set-Content -Encoding ascii "$run/scripts/game_start.scr"
$steps = @(
    # Same tick: perspective cameras change only the vehicle windows, and normal restores them exactly.
    "screenshot p9-normal`nrenderer_3d queued eye all 0 0 24 ahead -8`nscreenshot p9-eye`nrenderer_3d queued view all normal`nscreenshot p9-back",
    # Perspective cameras stay still while their vehicles move on, under the GPU references.
    "renderer_3d eye all 0 0 24 ahead -8`nscreenshot p9-still-start",
    "screenshot p9-still-end`nrenderer_3d vehiclewindows 1`nrenderer_3d windowsize all 1240 840`nrenderer_3d eye all 0 0 24 ahead -6",
    # One large window: along the track, then the four compass headings from above the vehicle.
    "screenshot p9-big-ahead`nrenderer_3d queued eye all 0 0 64 0 -15`nscreenshot p9-big-n`nrenderer_3d queued eye all 0 0 64 90 -15`nscreenshot p9-big-e`nrenderer_3d queued eye all 0 0 64 180 -15`nscreenshot p9-big-s`nrenderer_3d queued eye all 0 0 64 270 -15`nscreenshot p9-big-w",
    # Level with the horizon: sky above, fog towards the draw distance.
    "renderer_3d eye all 0 0 12 ahead 0`nscreenshot p9-horizon",
    # Close to the ground, where the near plane matters.
    "renderer_3d eye all 0 0 6 ahead -4 75`nscreenshot p9-low",
    'quit'
)
if ($Fleet) {
    $steps = @(
        # Eye level, nearly flat: the ground runs out to the draw distance in every direction.
        "renderer_3d vehiclewindows 1`nrenderer_3d windowsize all 1240 840`nrenderer_3d eye all 0 0 40 0 -2",
        "screenshot p9-far-n`nrenderer_3d queued eye all 0 0 40 90 -2`nscreenshot p9-far-e`nrenderer_3d queued eye all 0 0 40 180 -2`nscreenshot p9-far-s`nrenderer_3d queued eye all 0 0 40 270 -2`nscreenshot p9-far-w",
        "renderer_3d eye all 0 0 400 ahead -12`nscreenshot p9-far-high",
        'quit'
    )
}
for ($i=0; $i -lt $steps.Count; $i++) {
    $text = $steps[$i]
    if ($i+1 -lt $steps.Count) { $text += "`nschedule on-next-calendar-month scripts/step$($i+1).scr" }
    $text | Set-Content -Encoding ascii "$run/scripts/step$i.scr"
}
$arguments = '-c "{0}" -x -X -QQ -I OpenGFX -v win32-opengl -b 32bpp-optimized -s null -m null -d driver=1,script=3' -f "$run/openttd.cfg"
$arguments += ' -g "{0}"' -f $(if ($Fleet) { "$fixture/phase7/fleet/fleet-9.sav" } else { "$fixture/phase4/infrastructure.sav" })
$process = Start-Process $exe -ArgumentList $arguments -WorkingDirectory $build -WindowStyle Hidden -PassThru -RedirectStandardOutput "$run/stdout.log" -RedirectStandardError "$run/stderr.log"
$handle = $process.Handle
try {
    $deadline = (Get-Date).AddSeconds(600)
    while (!$process.WaitForExit(1000)) { if ((Get-Date) -gt $deadline) { throw "Timed out: $run" } }
    if ($process.ExitCode -ne 0) { throw "Exit $($process.ExitCode): $run" }
} finally { if (!$process.HasExited) { $process.Kill(); $process.WaitForExit() } }
python "$PSScriptRoot/verify-phase9-perspective.py" $run
if ($LASTEXITCODE -ne 0) { throw 'Phase 9.2 verification failed' }
