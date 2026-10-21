param([ValidateSet('Railway','AirWater')][string]$Save = 'Railway', [string]$RunTag = 'phase9-chase')
# Phase 9.3: chase views in vehicle windows.
# Step 0 checks the camera button and hotkey within one game tick; step 1 logs every chase camera update for a month at
# normal speed; step 2 pauses; step 3 captures one large chase window per type, then saves with it open and reloads.
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
$big = @()
$frame = 2
foreach ($type in $types) {
    $big += "renderer_3d after $frame renderer_3d vehiclewindows 0", "renderer_3d after $($frame + 1) renderer_3d view $type chase", "renderer_3d after $($frame + 2) renderer_3d windowsize all 1240 840"
    $big += "renderer_3d after $($frame + 300) screenshot p9-big-$type"
    $frame += 302
}
$steps = @(
    # Same tick: the button and the hotkey switch to the same chase view as the console, and back to normal exactly.
    # Three presses (cab, chase, normal) first bring the windows to the front in their own order, so later presses keep
    # the screen's stacking. Since 9.4 the cycle is normal, cab, chase, so chase is two presses away.
    "renderer_3d press all button`nrenderer_3d press all button`nrenderer_3d press all button`nscreenshot p9-c-normal`nrenderer_3d queued press all button`nrenderer_3d queued press all button`nscreenshot p9-c-button`nrenderer_3d queued view all normal`nrenderer_3d queued view all chase`nscreenshot p9-c-view`nrenderer_3d queued press all hotkey`nscreenshot p9-c-hotkey-off`nrenderer_3d queued press all hotkey`nrenderer_3d queued press all hotkey`nscreenshot p9-c-hotkey-on",
    # A month at normal speed with every chase camera update logged.
    "renderer_3d view all chase`nrenderer_3d chaselog on`nrenderer_3d fastforward off",
    # Paused: the cameras settle and stop redrawing, and the game stays paused.
    "renderer_3d chaselog off`npause`nrenderer_3d after 600 screenshot p9-paused-a`nrenderer_3d after 660 screenshot p9-paused-b`nrenderer_3d after 661 unpause",
    # One large chase window per type; then save with a chase view open and reload. Loading closes the old windows and runs
    # game_start.scr again, which opens normal vehicle windows, so the run quits before that script's next month comes round.
    ((@("renderer_3d vehiclewindows 0") + $big + "renderer_3d after $frame save p9-chase" + "renderer_3d after $($frame + 10) load p9-chase" + "renderer_3d after $($frame + 70) renderer_3d views" + "renderer_3d after $($frame + 71) screenshot p9-reload" + "renderer_3d after $($frame + 100) quit") -join "`n")
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
python "$PSScriptRoot/verify-phase9-chase.py" $run ($types -join ',')
if ($LASTEXITCODE -ne 0) { throw 'Phase 9.3 verification failed' }
