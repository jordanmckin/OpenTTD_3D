param([string]$RunTag = 'phase95c-shadows', [ValidateSet('infrastructure','town','fleet')][string]$Scene = 'infrastructure', [string]$FixtureSave = '')
# Phase 9.5c visual comparison: each view is captured paused, once per shadow mode (off, contact, sun), in one run,
# so the three images of a view differ only by shadows. No user saves/configs are used.
$ErrorActionPreference = 'Stop'
if ($RunTag -notmatch '^[a-zA-Z0-9_-]+$') { throw 'Use a simple run tag' }
$workspace = Split-Path -Parent $PSScriptRoot
$build = Join-Path $workspace 'build/baseline'
$fixture = Join-Path $workspace 'OpenTTD-15.3/OpenTTD-15.3/docs/3d/fixtures'
if (!$FixtureSave) {
    $FixtureSave = switch ($Scene) {
        'infrastructure' { "$fixture/phase4/infrastructure.sav" }
        'fleet' { "$fixture/phase7/fleet/fleet-9.sav" }
        'town' { throw 'Pass the dense town save from tools/phase9-town.ps1 with -FixtureSave.' }
    }
}
$run = Join-Path $workspace ".runtime/$RunTag"
if (Test-Path -LiteralPath $run) { throw "Use a fresh RunTag: $run" }
$exe = Join-Path $build "$RunTag-console.exe"
Copy-Item "$build/Release/openttd.exe" $exe
& 'C:/Program Files (x86)/Microsoft Visual Studio/2022/BuildTools/VC/Tools/MSVC/14.44.35207/bin/Hostx64/x64/editbin.exe' /nologo /subsystem:console $exe
if ($LASTEXITCODE -ne 0) { throw 'editbin failed' }
New-Item -ItemType Directory -Force "$run/baseset","$run/lang","$run/scripts","$run/ai/infrastructure3d","$run/ai/fleet3d" | Out-Null
Copy-Item "$build/baseset/*" "$run/baseset"
Copy-Item "$build/lang/*.lng" "$run/lang"
Copy-Item "$workspace/.runtime/baseline/baseset/*.tar" "$run/baseset"
Copy-Item "$fixture/phase4/ai/*.nut" "$run/ai/infrastructure3d"
Copy-Item "$fixture/phase7/fleet/ai/*.nut" "$run/ai/fleet3d"
$config = (Get-Content -Raw "$fixture/phase6/coverage.cfg").Replace('resolution = 1280,900','resolution = 1920,1080').Replace('[gui]', "[gui]`nrenderer_3d_camera_hints = false")
$config | Set-Content -Encoding ascii "$run/openttd.cfg"

# Each view: one capture per mode, queued so the mode changes only after the previous capture.
function Views([string[]]$setups) {
    $result = @()
    foreach ($setup in $setups) {
        $name, $command = $setup -split '\|', 2
        $result += $command
        $result += "renderer_3d shadows off`nscreenshot $name-off`nrenderer_3d queued shadows contact`nscreenshot $name-contact`nrenderer_3d queued shadows sun`nscreenshot $name-sun`nrenderer_3d queued shadowstats"
    }
    return $result
}
switch ($Scene) {
    'infrastructure' {
        $commands = @('pause', 'setting gui.errmsg_duration 0', 'renderer_3d on', 'scrollto instant 29 33', 'zoomto 2')
        $steps = Views @('classic|renderer_3d camera 0 100', 'yaw45|renderer_3d camera 45 60', 'yaw135|renderer_3d camera 135 80', 'close|zoomto 1', 'far|zoomto 4')
    }
    'town' {
        $commands = @('pause', 'setting gui.errmsg_duration 0', 'renderer_3d on', 'scrollto instant 258 276', 'zoomto 2')
        # The street view is the 9.6 town case: a still eye in an enlarged vehicle window, southeast of the town.
        $steps = Views @('town-classic|renderer_3d camera 0 100', 'town90|renderer_3d camera 90 80', 'town-close|zoomto 1',
            "town-street|renderer_3d camera 0 100`nzoomto 2`nrenderer_3d vehiclewindows 1`nrenderer_3d windowsize all 1800 960`nrenderer_3d eye all 44 43.5 160 0 -16 70")
    }
    'fleet' {
        $commands = @('setting gui.errmsg_duration 0', 'renderer_3d on', 'scrollto instant 256 256', 'zoomto 2', 'renderer_3d vehiclewindows 4', 'renderer_3d windowsize all 850 450')
        $steps = @('pause') + (Views @('fleet-normal|renderer_3d views', 'fleet-chase|renderer_3d view all chase', 'fleet-cab|renderer_3d view all cab'))
    }
}
$steps += 'quit'
$frame = if ($Scene -eq 'fleet') { 400 } else { 40 }
foreach ($step in $steps) {
    foreach ($command in ($step -split "`n")) { $commands += "renderer_3d after $frame $command" }
    $frame += 60
}
$commands | Set-Content -Encoding ascii "$run/scripts/game_start.scr"
$arguments = '-c "{0}" -x -X -QQ -I OpenGFX -v win32-opengl -b 32bpp-optimized -s null -m null -d driver=1 -g "{1}"' -f "$run/openttd.cfg",$FixtureSave
$process = Start-Process $exe -ArgumentList $arguments -WorkingDirectory $build -WindowStyle Hidden -PassThru -RedirectStandardOutput "$run/stdout.log" -RedirectStandardError "$run/stderr.log"
$null = $process.Handle
try {
    $deadline = (Get-Date).AddSeconds(300)
    while (!$process.WaitForExit(1000)) { if ((Get-Date) -gt $deadline) { throw "Timed out: $run" } }
    if ($process.ExitCode -ne 0) { throw "Exit $($process.ExitCode): $run" }
} finally { if (!$process.HasExited) { $process.Kill(); $process.WaitForExit() } }
Get-ChildItem "$run/screenshot" -Filter *.png | Select-Object -ExpandProperty Name
