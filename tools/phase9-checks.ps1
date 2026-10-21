param([string]$RunTag = 'phase9')
# Phase 9.1: vehicle windows with their own cameras, on the Phase 4 railway fixture.
# Each comparison is taken within one game tick, so views that should not change can be compared pixel for pixel.
$ErrorActionPreference = 'Stop'
$workspace = Split-Path -Parent $PSScriptRoot
$build = Join-Path $workspace 'build/baseline'
$fixture = Join-Path $workspace 'OpenTTD-15.3/OpenTTD-15.3/docs/3d/fixtures'
$run = Join-Path $workspace ".runtime/$RunTag-check"
$exe = Join-Path $build "$RunTag-check-console.exe"
Copy-Item "$build/Release/openttd.exe" $exe
& 'C:/Program Files (x86)/Microsoft Visual Studio/2022/BuildTools/VC/Tools/MSVC/14.44.35207/bin/Hostx64/x64/editbin.exe' /nologo /subsystem:console $exe
if ($LASTEXITCODE -ne 0) { throw 'editbin failed' }
if (Test-Path "$run/screenshot") { Remove-Item -Recurse -Force "$run/screenshot" }
New-Item -ItemType Directory -Force "$run/baseset","$run/lang","$run/scripts","$run/ai/infrastructure3d" | Out-Null
Copy-Item "$build/baseset/*" "$run/baseset"
Copy-Item "$build/lang/*.lng" "$run/lang"
Copy-Item "$workspace/.runtime/baseline/baseset/*.tar" "$run/baseset"
Copy-Item "$fixture/phase4/ai/*.nut" "$run/ai/infrastructure3d"
Get-Content -Raw "$fixture/phase6/coverage.cfg" | Set-Content -Encoding ascii "$run/openttd.cfg"
@'
renderer_3d on
renderer_3d verifygpu on
setting gui.show_finances false
scrollto instant 29 33
zoomto 2
renderer_3d vehiclewindows 4
setting gui.fast_forward_speed_limit 2000
renderer_3d fastforward on
unpause
schedule on-next-calendar-month scripts/step0.scr
'@ | Set-Content -Encoding ascii "$run/scripts/game_start.scr"
# Console screenshots are taken later on the main thread; 'renderer_3d queued' orders a change between them.
$steps = @(
    # Same tick: own cameras change only the vehicle windows, and normal restores them exactly.
    "screenshot phase9-normal`nrenderer_3d queued view all chase`nscreenshot phase9-chase`nrenderer_3d queued view all cab`nscreenshot phase9-cab`nrenderer_3d queued view all normal`nscreenshot phase9-back",
    # Same tick: turning the shared camera leaves the cab views alone.
    "renderer_3d view all cab`nscreenshot phase9-cab-shared`nrenderer_3d queued camera 90 60`nscreenshot phase9-cab-orbit`nrenderer_3d queued camera 0 100",
    # Cab cameras follow moving vehicles for a month under the GPU references.
    "screenshot phase9-moving-start",
    "screenshot phase9-moving-end`nrenderer_3d view all chase",
    # Classic 2D ignores the cameras; switching back on resumes them.
    "renderer_3d queued off`nscreenshot phase9-classic`nrenderer_3d queued on`nscreenshot phase9-resumed",
    'quit'
)
for ($i=0; $i -lt $steps.Count; $i++) {
    $text = $steps[$i]
    if ($i+1 -lt $steps.Count) { $text += "`nschedule on-next-calendar-month scripts/step$($i+1).scr" }
    $text | Set-Content -Encoding ascii "$run/scripts/step$i.scr"
}
$arguments = '-c "{0}" -x -X -QQ -I OpenGFX -v win32-opengl -b 32bpp-optimized -s null -m null -d driver=1,script=3' -f "$run/openttd.cfg"
$arguments += ' -g "{0}"' -f "$fixture/phase4/infrastructure.sav"
$process = Start-Process $exe -ArgumentList $arguments -WorkingDirectory $build -WindowStyle Hidden -PassThru -RedirectStandardOutput "$run/stdout.log" -RedirectStandardError "$run/stderr.log"
$handle = $process.Handle
try {
    $deadline = (Get-Date).AddSeconds(600)
    while (!$process.WaitForExit(1000)) { if ((Get-Date) -gt $deadline) { throw "Timed out: $run" } }
    if ($process.ExitCode -ne 0) { throw "Exit $($process.ExitCode): $run" }
} finally { if (!$process.HasExited) { $process.Kill(); $process.WaitForExit() } }
python "$PSScriptRoot/verify-phase9-checks.py" $run
if ($LASTEXITCODE -ne 0) { throw 'Phase 9 verification failed' }
