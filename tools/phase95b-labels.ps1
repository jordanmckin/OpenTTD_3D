param([string]$RunTag = 'phase95b-labels', [int]$Scale = 100, [string]$Blitter = '32bpp-optimized', [string]$FixtureSave = '', [switch]$Dense)
$ErrorActionPreference = 'Stop'
$workspace = Split-Path -Parent $PSScriptRoot
$build = Join-Path $workspace 'build/baseline'
$fixture = Join-Path $workspace 'OpenTTD-15.3/OpenTTD-15.3/docs/3d/fixtures'
if (!$FixtureSave) { $FixtureSave = "$fixture/phase4/infrastructure.sav" }
$run = Join-Path $workspace ".runtime/$RunTag"
if (Test-Path -LiteralPath $run) { throw "Use a fresh RunTag: $run" }
$exe = Join-Path $build "$RunTag-console.exe"
Copy-Item "$build/Release/openttd.exe" $exe
& 'C:/Program Files (x86)/Microsoft Visual Studio/2022/BuildTools/VC/Tools/MSVC/14.44.35207/bin/Hostx64/x64/editbin.exe' /nologo /subsystem:console $exe
if ($LASTEXITCODE -ne 0) { throw 'editbin failed' }
New-Item -ItemType Directory -Force "$run/baseset","$run/lang","$run/scripts","$run/ai/infrastructure3d" | Out-Null
Copy-Item "$build/baseset/*" "$run/baseset"
Copy-Item "$build/lang/*.lng" "$run/lang"
Copy-Item "$workspace/.runtime/baseline/baseset/*.tar" "$run/baseset"
Copy-Item "$fixture/phase4/ai/*.nut" "$run/ai/infrastructure3d"
if ($Dense) {
    New-Item -ItemType Directory -Force "$run/ai/fleet3d" | Out-Null
    Copy-Item "$fixture/phase7/fleet/ai/*.nut" "$run/ai/fleet3d"
}
$config = Get-Content -Raw "$fixture/phase6/coverage.cfg"
$config = $config.Replace('[misc]', "[misc]`ngui_scale = $Scale").Replace('[gui]', "[gui]`nrenderer_3d_camera_hints = false")
$config | Set-Content -Encoding ascii "$run/openttd.cfg"
$commands = @('pause', 'setting gui.errmsg_duration 0', 'renderer_3d on', 'renderer_3d fixturelabels', 'renderer_3d labeloptions 239 127', 'scrollto instant 29 33', 'zoomto 2')
$steps = @(
    "renderer_3d labels click classic`nscreenshot classic`nrenderer_3d queued labeloptions 0 127`nscreenshot classic-hidden`nrenderer_3d queued labeloptions 239 127",
    'renderer_3d camera 45 60',
    "renderer_3d labels click yaw45`nscreenshot yaw45",
    'renderer_3d camera 90 140',
    "renderer_3d labels click yaw90`nscreenshot yaw90`nrenderer_3d queued labeloptions 0 127`nscreenshot yaw90-hidden`nrenderer_3d queued labeloptions 239 127",
    'renderer_3d camera 180 100',
    "renderer_3d labels click yaw180`nscreenshot yaw180",
    'renderer_3d camera 270 80',
    "renderer_3d labels click yaw270`nscreenshot yaw270",
    'zoomto 4',
    "renderer_3d labels click small`nscreenshot small",
    "renderer_3d labeloptions 0 127`nrenderer_3d labels click hidden`nscreenshot hidden",
    "renderer_3d labeloptions 239 0`nrenderer_3d labels click facilities`nscreenshot facilities",
    "renderer_3d labeloptions 111 127`nrenderer_3d labels click competitors`nscreenshot competitors",
    "renderer_3d labeloptions 239 127`nrenderer_3d visibility 0 hidden`nrenderer_3d labels click invisible`nscreenshot invisible",
    "renderer_3d visibility 0 transparent`nrenderer_3d labels click transparent`nscreenshot transparent",
    "renderer_3d visibility 0 solid`nzoomto 2`nrenderer_3d camera 90 100`nscrollto instant 29 33",
    "renderer_3d labeleffects`nscreenshot effects`nrenderer_3d queued visibility 8 transparent`nscreenshot effects-hidden`nrenderer_3d queued visibility 8 solid",
    'renderer_3d viewport',
    "renderer_3d vehiclewindows 2`nrenderer_3d labels click secondary`nscreenshot secondary",
    'renderer_3d view all cab',
    "renderer_3d labels click cab`nscreenshot cab",
    'renderer_3d view all chase',
    "renderer_3d labels click chase`nscreenshot chase",
    "renderer_3d vehiclewindows 0`nrenderer_3d camera 0 100`nrenderer_3d off",
    "renderer_3d labels click classic2d`nscreenshot classic2d",
    "renderer_3d on`nscrollto instant 33 27`nzoomto 1",
    "renderer_3d labels click close`nscreenshot close",
    'renderer_3d toolbar resize 800 600',
    "renderer_3d labels click resized`nscreenshot resized",
    'quit'
)
if ($Dense) {
    $commands = @('pause', 'setting gui.errmsg_duration 0', 'renderer_3d on', 'renderer_3d labeloptions 239 127', 'scrollto instant 258 276', 'zoomto 2')
    $steps = @(
        "renderer_3d labels click dense-classic`nscreenshot dense-classic",
        'renderer_3d camera 45 60',
        "renderer_3d labels click dense45`nscreenshot dense45",
        'renderer_3d camera 90 140',
        "renderer_3d labels click dense90`nscreenshot dense90",
        'renderer_3d camera 180 100',
        "renderer_3d labels click dense180`nscreenshot dense180",
        "renderer_3d viewport`nrenderer_3d vehiclewindows 4",
        "renderer_3d labels click dense-secondary`nscreenshot dense-secondary",
        'quit'
    )
}
$frame = 40
foreach ($step in $steps) {
    foreach ($command in ($step -split "`n")) { $commands += "renderer_3d after $frame $command" }
    $frame += 45
}
$commands | Set-Content -Encoding ascii "$run/scripts/game_start.scr"
$arguments = '-c "{0}" -x -X -QQ -I OpenGFX -v win32-opengl -b {1} -s null -m null -d driver=1 -g "{2}"' -f "$run/openttd.cfg",$Blitter,$FixtureSave
$process = Start-Process $exe -ArgumentList $arguments -WorkingDirectory $build -WindowStyle Hidden -PassThru -RedirectStandardOutput "$run/stdout.log" -RedirectStandardError "$run/stderr.log"
$null = $process.Handle
try {
    $deadline = (Get-Date).AddSeconds(240)
    while (!$process.WaitForExit(1000)) { if ((Get-Date) -gt $deadline) { throw "Timed out: $run" } }
    if ($process.ExitCode -ne 0) { throw "Exit $($process.ExitCode): $run" }
} finally { if (!$process.HasExited) { $process.Kill(); $process.WaitForExit() } }
if ($Dense) { python "$PSScriptRoot/verify-phase95b-labels.py" $run --dense }
else { python "$PSScriptRoot/verify-phase95b-labels.py" $run }
if ($LASTEXITCODE -ne 0) { throw 'Phase 9.5b verification failed' }
