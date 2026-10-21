param([string]$RunTag = 'phase95a-toolbar')
$ErrorActionPreference = 'Stop'
$workspace = Split-Path -Parent $PSScriptRoot
$build = Join-Path $workspace 'build/baseline'
$fixture = Join-Path $workspace 'OpenTTD-15.3/OpenTTD-15.3/docs/3d/fixtures'
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
Get-Content -Raw "$fixture/phase6/coverage.cfg" | Set-Content -Encoding ascii "$run/openttd.cfg"
function Invoke-Case([string]$Name, [string[]]$Steps, [string]$Driver = 'win32-opengl', [string]$Blitter = '32bpp-optimized') {
    # All input here is dispatched by the application's own handlers. No OS input claim.
    $commands = @('pause', 'setting gui.errmsg_duration 0')
    $frame = 40
    foreach ($step in $Steps) {
        foreach ($command in ($step -split "`n")) { $commands += "renderer_3d after $frame $command" }
        $frame += 90
    }
    $commands += "renderer_3d after $frame quit"
    $commands | Set-Content -Encoding ascii "$run/scripts/game_start.scr"
    # Config writes are intentionally enabled, in this isolated directory only.
    $arguments = '-c "{0}" -X -QQ -I OpenGFX -s null -m null -d driver=1 -g "{1}"' -f "$run/openttd.cfg","$fixture/phase4/infrastructure.sav"
    if ($Driver) { $arguments += " -v $Driver" }
    if ($Blitter) { $arguments += " -b $Blitter" }
    $process = Start-Process $exe -ArgumentList $arguments -WorkingDirectory $build -WindowStyle Hidden -PassThru -RedirectStandardOutput "$run/$Name-stdout.log" -RedirectStandardError "$run/$Name.log"
    $null = $process.Handle
    try {
        $deadline = (Get-Date).AddSeconds(180)
        while (!$process.WaitForExit(1000)) { if ((Get-Date) -gt $deadline) { throw "Timed out: $Name" } }
        if ($process.ExitCode -ne 0) { throw "Exit $($process.ExitCode): $Name" }
    } finally { if (!$process.HasExited) { $process.Kill(); $process.WaitForExit() } }
    Copy-Item "$run/openttd.cfg" "$run/$Name.cfg"
}
function Menu-Select([int]$Down) {
    $commands = @('renderer_3d toolbar key menu')
    for ($i = 0; $i -lt $Down; $i++) { $commands += 'renderer_3d toolbar key down' }
    $commands += 'renderer_3d toolbar key enter'
    return $commands -join "`n"
}
Invoke-Case 'controls' @(
    "renderer_3d toolbar status fresh`nscreenshot fresh",
    "renderer_3d toolbar open`nscreenshot menu-2d",
    "renderer_3d toolbar key escape`nrenderer_3d toolbar status escape",
    (Menu-Select 0),
    "renderer_3d toolbar status enabled`nscreenshot enabled",
    'renderer_3d vehiclewindows 2',
    "renderer_3d toolbar key menu`nrenderer_3d toolbar key up`nrenderer_3d toolbar key enter",
    "renderer_3d toolbar status help`nscreenshot help",
    "renderer_3d toolbar key escape`nrenderer_3d vehiclewindows 0",
    (Menu-Select 1),
    (Menu-Select 2),
    "renderer_3d toolbar status prefs`nscreenshot flat",
    (Menu-Select 4),
    "renderer_3d toolbar status orbit`nscreenshot orbit",
    (Menu-Select 3),
    "renderer_3d toolbar status classic`nscreenshot classic",
    "renderer_3d toolbar open`nrenderer_3d toolbar key enter",
    "renderer_3d toolbar status disabled`nscreenshot disabled",
    (Menu-Select 0)
) '' ''
# Force a reproducible scale where an 800px window uses the split toolbar.
$scaledConfig = (Get-Content -Raw -Encoding UTF8 "$run/openttd.cfg") -replace '(?m)^gui_scale\s*=.*$', 'gui_scale = 200'
[System.IO.File]::WriteAllText("$run/openttd.cfg", $scaledConfig, [System.Text.UTF8Encoding]::new($false))
Invoke-Case 'restart' @(
    "renderer_3d toolbar status restart`nscreenshot restart",
    "renderer_3d toolbar resize 800 600",
    "renderer_3d toolbar status narrow`nrenderer_3d toolbar open`nscreenshot narrow-upper",
    "renderer_3d toolbar key escape`nrenderer_3d toolbar switch",
    "renderer_3d toolbar status lower`nrenderer_3d toolbar open`nscreenshot narrow-lower",
    "renderer_3d toolbar key escape`nrenderer_3d toolbar resize 1280 900",
    "renderer_3d toolbar status resized`nscreenshot resized"
)
Invoke-Case 'fallback' @(
    "renderer_3d toolbar status fallback`nrenderer_3d toolbar open`nscreenshot fallback",
    "renderer_3d toolbar key enter",
    "renderer_3d toolbar status fallback-help`nscreenshot fallback-help"
) 'win32'
Invoke-Case 'restored' @("renderer_3d toolbar status restored`nscreenshot restored")
# Check the second supported blitter, and persistence of disabling 3D.
Invoke-Case 'animated' @(
    "renderer_3d toolbar status animated`nscreenshot animated",
    (Menu-Select 0),
    'renderer_3d toolbar status off-saved'
) 'win32-opengl' '40bpp-anim'
Invoke-Case 'off-restart' @('renderer_3d toolbar status off-restart')
# Scaling is isolated in the same test config; it exercises layout, not a native DPI transition.
$scaledConfig = (Get-Content -Raw -Encoding UTF8 "$run/openttd.cfg") -replace '(?m)^gui_scale\s*=.*$', 'gui_scale = 200'
[System.IO.File]::WriteAllText("$run/openttd.cfg", $scaledConfig, [System.Text.UTF8Encoding]::new($false))
Invoke-Case 'scaled' @(
    "renderer_3d toolbar status scaled`nrenderer_3d toolbar open`nscreenshot scaled-menu",
    "renderer_3d toolbar key up`nrenderer_3d toolbar key enter",
    'screenshot scaled-help'
)
python "$PSScriptRoot/verify-phase95a-toolbar.py" $run
if ($LASTEXITCODE -ne 0) { throw 'Phase 9.5a verification failed' }
