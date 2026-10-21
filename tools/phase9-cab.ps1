param([ValidateSet('Railway','AirWater')][string]$Save = 'Railway', [string]$RunTag = 'phase9-cab')
# Phase 9.4: cab views in vehicle windows.
# Step 0 checks the camera button cycle (normal, cab, chase, normal) and the hotkey within one game tick; step 1 logs
# every cab camera update and every cab render for a month at normal speed; step 2 captures a series of large cab
# windows per type for the hole check and review, then quits.
# Railway uses the Phase 4 save (train and trucks); AirWater the Phase 6 coverage save (aircraft and ship).
$ErrorActionPreference = 'Stop'
$workspace = Split-Path -Parent $PSScriptRoot
$build = Join-Path $workspace 'build/baseline'
$fixture = Join-Path $workspace 'OpenTTD-15.3/OpenTTD-15.3/docs/3d/fixtures'
$RunTag += "-$($Save.ToLower())"
$run = Join-Path $workspace ".runtime/$RunTag"
$exe = Join-Path $build "$RunTag-console.exe"
Copy-Item "$build/Release/openttd.exe" $exe
& 'C:/Program Files (x86)/Microsoft Visual Studio/2022/BuildTools/VC/Tools/MSVC/14.44.35207/bin/Hostx64/x64/editbin.exe' /nologo /subsystem:console $exe
if ($LASTEXITCODE -ne 0) { throw 'editbin failed' }
foreach ($old in @("$run/screenshot", "$run/save")) { if (Test-Path $old) { Remove-Item -Recurse -Force $old } }
New-Item -ItemType Directory -Force "$run/baseset","$run/lang","$run/scripts","$run/ai/infrastructure3d","$run/ai/coverage3d" | Out-Null
Copy-Item "$build/baseset/*" "$run/baseset"
Copy-Item "$build/lang/*.lng" "$run/lang"
Copy-Item "$workspace/.runtime/baseline/baseset/*.tar" "$run/baseset"
Copy-Item "$fixture/phase4/ai/*.nut" "$run/ai/infrastructure3d"
Copy-Item "$fixture/phase6/ai/*.nut" "$run/ai/coverage3d"
Get-Content -Raw "$fixture/phase6/coverage.cfg" | Set-Content -Encoding ascii "$run/openttd.cfg"
$railway = $Save -eq 'Railway'
$types = if ($railway) { @('train', 'road') } else { @('ship', 'aircraft') }
@"
renderer_3d on
renderer_3d verifygpu on
setting gui.show_finances false
scrollto instant $(if ($railway) { '29 33' } else { '32 32' })
zoomto 2
renderer_3d vehiclewindows $(if ($railway) { 4 } else { 2 })
setting gui.fast_forward_speed_limit 2000
renderer_3d fastforward on
unpause
schedule on-next-calendar-month scripts/step0.scr
"@ | Set-Content -Encoding ascii "$run/scripts/game_start.scr"
# Large cab windows: one per type at a time, captured several times as it drives.
$big = @()
$frame = 2
foreach ($type in $types) {
    $big += "renderer_3d after $frame renderer_3d vehiclewindows 0", "renderer_3d after $($frame + 1) renderer_3d view $type cab", "renderer_3d after $($frame + 2) renderer_3d windowsize all 1240 840"
    # The views line logs each cab's pitch at the capture, which places its horizon.
    for ($shot = 0; $shot -lt 6; $shot++) { $big += "renderer_3d after $($frame + 200 + $shot * 450) renderer_3d views", "renderer_3d after $($frame + 200 + $shot * 450) screenshot p9-cab-$type-$shot" }
    $frame += 200 + 6 * 450
}
$steps = @(
    # Same tick: the button goes normal, cab, chase, normal; each matches the console's view exactly. Three presses first
    # bring the windows to the front in their own order, so later presses keep the screen's stacking.
    "renderer_3d press all button`nrenderer_3d press all button`nrenderer_3d press all button`nscreenshot p9-k-normal`nrenderer_3d queued press all button`nscreenshot p9-k-cab-button`nrenderer_3d queued view all normal`nrenderer_3d queued view all cab`nscreenshot p9-k-cab-view`nrenderer_3d queued press all button`nscreenshot p9-k-chase-button`nrenderer_3d queued view all normal`nrenderer_3d queued view all chase`nscreenshot p9-k-chase-view`nrenderer_3d queued press all button`nscreenshot p9-k-back`nrenderer_3d queued press all hotkey`nscreenshot p9-k-hotkey-cab",
    # A month at normal speed with every cab camera update and render logged.
    "renderer_3d view all cab`nrenderer_3d chaselog on`nrenderer_3d fastforward off",
    ((@("renderer_3d chaselog off", "renderer_3d vehiclewindows 0") + $big + "renderer_3d after $($frame + 10) quit") -join "`n")
)
for ($i=0; $i -lt $steps.Count; $i++) {
    $text = $steps[$i]
    if ($i+1 -lt $steps.Count) { $text += "`nschedule on-next-calendar-month scripts/step$($i+1).scr" }
    $text | Set-Content -Encoding ascii "$run/scripts/step$i.scr"
}
$arguments = '-c "{0}" -x -X -QQ -I OpenGFX -v win32-opengl -b 32bpp-optimized -s null -m null -d driver=1,script=3' -f "$run/openttd.cfg"
$arguments += ' -g "{0}"' -f $(if ($railway) { "$fixture/phase4/infrastructure.sav" } else { "$fixture/phase6/coverage.sav" })
$process = Start-Process $exe -ArgumentList $arguments -WorkingDirectory $build -WindowStyle Hidden -PassThru -RedirectStandardOutput "$run/stdout.log" -RedirectStandardError "$run/stderr.log"
$handle = $process.Handle
try {
    $deadline = (Get-Date).AddSeconds(900)
    while (!$process.WaitForExit(1000)) { if ((Get-Date) -gt $deadline) { throw "Timed out: $run" } }
    if ($process.ExitCode -ne 0) { throw "Exit $($process.ExitCode): $run" }
} finally { if (!$process.HasExited) { $process.Kill(); $process.WaitForExit() } }
python "$PSScriptRoot/verify-phase9-cab.py" $run ($types -join ',')
if ($LASTEXITCODE -ne 0) { throw 'Phase 9.4 verification failed' }
