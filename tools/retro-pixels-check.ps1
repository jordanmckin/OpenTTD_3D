param([string]$RunTag = 'retro-pixels', [string]$Executable = '')
# Exercise real toolbar/panel handlers, GPU/CPU parity, paused toggles, and local persistence.
$ErrorActionPreference = 'Stop'
if ($RunTag -notmatch '^[a-zA-Z0-9_-]+$') { throw 'Use a simple run tag' }
$workspace = Split-Path -Parent $PSScriptRoot
$build = Join-Path $workspace 'build/baseline'
$fixture = Join-Path $workspace 'OpenTTD-15.3/OpenTTD-15.3/docs/3d/fixtures'
$run = Join-Path $workspace ".runtime/$RunTag"
if (Test-Path -LiteralPath $run) { throw "Use a fresh RunTag: $run" }
$exe = Join-Path $build "$RunTag-console.exe"
if (!$Executable) { $Executable = "$build/Release/openttd.exe" }
Copy-Item -LiteralPath $Executable -Destination $exe
& 'C:/Program Files (x86)/Microsoft Visual Studio/2022/BuildTools/VC/Tools/MSVC/14.44.35207/bin/Hostx64/x64/editbin.exe' /nologo /subsystem:console $exe
if ($LASTEXITCODE -ne 0) { throw 'editbin failed' }
New-Item -ItemType Directory -Force "$run/baseset","$run/lang","$run/scripts","$run/ai/infrastructure3d" | Out-Null
Copy-Item "$build/baseset/*" "$run/baseset"
Copy-Item "$build/lang/*.lng" "$run/lang"
Copy-Item "$workspace/.runtime/baseline/baseset/*.tar" "$run/baseset"
Copy-Item "$fixture/phase4/ai/*.nut" "$run/ai/infrastructure3d"
$config = (Get-Content -Raw "$fixture/phase6/coverage.cfg").Replace('[gui]', "[gui]`nrenderer_3d_camera_hints = false`ngui_scale = 100")
$config | Set-Content -Encoding ascii "$run/openttd.cfg"

function Open-Panel {
    $commands = @('renderer_3d toolbar key menu')
    # Enable, terrain, hints, visibility, three shadow choices, retro panel.
    for ($i = 0; $i -lt 7; $i++) { $commands += 'renderer_3d toolbar key down' }
    $commands += 'renderer_3d toolbar key enter'
    return $commands -join "`n"
}
function Invoke-Case([string]$Name, [string[]]$Steps, [string]$Blitter = '32bpp-optimized') {
    $commands = @('pause', 'setting gui.errmsg_duration 0', 'renderer_3d on', 'scrollto instant 29 33', 'zoomto 1')
    $frame = 40
    foreach ($step in $Steps) {
        foreach ($command in ($step -split "`n")) { $commands += "renderer_3d after $frame $command" }
        $frame += 45
    }
    $commands += "renderer_3d after $frame quit"
    $commands | Set-Content -Encoding ascii "$run/scripts/game_start.scr"
    $arguments = '-c "{0}" -X -QQ -I OpenGFX -v win32-opengl -b {1} -s null -m null -d driver=1 -g "{2}"' -f "$run/openttd.cfg",$Blitter,"$fixture/phase4/infrastructure.sav"
    $process = Start-Process $exe -ArgumentList $arguments -WorkingDirectory $build -WindowStyle Hidden -PassThru -RedirectStandardOutput "$run/$Name-stdout.log" -RedirectStandardError "$run/$Name.log"
    $null = $process.Handle
    try {
        $deadline = (Get-Date).AddSeconds(180)
        while (!$process.WaitForExit(1000)) { if ((Get-Date) -gt $deadline) { throw "Timed out: $Name" } }
        if ($process.ExitCode -ne 0) { throw "Exit $($process.ExitCode): $Name" }
    } finally { if (!$process.HasExited) { $process.Kill(); $process.WaitForExit() } }
    Copy-Item "$run/openttd.cfg" "$run/$Name.cfg"
}

Invoke-Case 'controls' @(
    'renderer_3d retro status',
    # Exercise the original comparison matrix independently of shipping defaults.
    "setting gui.renderer_3d_retro false`nsetting gui.renderer_3d_pixel_size 2`nsetting gui.renderer_3d_retro_colours true`nsetting gui.renderer_3d_retro_dither true",
    'renderer_3d verifylayer on',
    'renderer_3d retro status',
    'screenshot original',
    (Open-Panel),
    'renderer_3d retro status',
    "renderer_3d retro enable`nscreenshot panel",
    "renderer_3d retro size1`nrenderer_3d retro close`nscreenshot colour-1x",
    (Open-Panel),
    "renderer_3d retro size2`nrenderer_3d retro close`nscreenshot retro-2x",
    (Open-Panel),
    "renderer_3d retro size3`nrenderer_3d retro close`nscreenshot retro-3x",
    (Open-Panel),
    "renderer_3d retro size4`nrenderer_3d retro dither`nrenderer_3d retro close`nscreenshot nodither-4x",
    (Open-Panel),
    "renderer_3d retro colours`nrenderer_3d retro close`nscreenshot pixels-4x",
    (Open-Panel),
    "renderer_3d retro size1`nrenderer_3d retro dither`nrenderer_3d retro close`nscreenshot passthrough-1x",
    (Open-Panel),
    "renderer_3d retro enable`nrenderer_3d retro close`nscreenshot restored",
    (Open-Panel),
    "renderer_3d retro enable`nrenderer_3d retro size2`nrenderer_3d retro colours`nrenderer_3d retro dither`nrenderer_3d retro close",
    'screenshot dither-2x',
    (Open-Panel),
    "renderer_3d retro dither`nrenderer_3d retro close`nscreenshot nodither-2x",
    (Open-Panel),
    "renderer_3d retro dither`nrenderer_3d retro close",
    "renderer_3d vehiclewindows 3`nrenderer_3d camera 45 80",
    'screenshot windows-direct',
    'renderer_3d performance readback',
    'screenshot windows-readback',
    "renderer_3d performance optimized`nrenderer_3d view all chase",
    'screenshot chase',
    "renderer_3d view all cab`nunpause",
    'screenshot cab-moving',
    'pause'
)
Invoke-Case 'restart' @(
    'renderer_3d retro status',
    (Open-Panel),
    'screenshot panel-restart',
    'renderer_3d toolbar key escape',
    'renderer_3d retro status',
    "renderer_3d off`nscreenshot classic-2d",
    "renderer_3d on`nscreenshot animated"
) '40bpp-anim'
# Scaled panel layout in a narrow window; this does not simulate an OS DPI change.
$config = (Get-Content -Raw "$run/openttd.cfg") -replace '(?m)^gui_scale\s*=.*$', 'gui_scale = 200'
[System.IO.File]::WriteAllText("$run/openttd.cfg", $config, [System.Text.UTF8Encoding]::new($false))
Invoke-Case 'scaled' @(
    'renderer_3d toolbar resize 800 600',
    (Open-Panel),
    'screenshot panel-scaled'
)
python "$PSScriptRoot/verify-retro-pixels.py" $run
if ($LASTEXITCODE -ne 0) { throw 'Retro pixel verification failed' }
