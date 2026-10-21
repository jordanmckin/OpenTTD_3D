param(
    [string]$RunTag = 'phase95d-visibility',
    [ValidateSet('infrastructure','town','fleet')][string]$Scene = 'infrastructure',
    [string]$FixtureSave = '',
    [int]$Scale = 100,
    [string]$Blitter = '32bpp-optimized',
    [switch]$VerifyGPU
)
# Paused off/on/restored comparisons, ground-picking fingerprints, manual choices and per-view focus.
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
$FixtureSave = (Resolve-Path -LiteralPath $FixtureSave).Path
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
$config = (Get-Content -Raw "$fixture/phase6/coverage.cfg").Replace('[misc]',"[misc]`ngui_scale = $Scale").Replace('[gui]',"[gui]`nrenderer_3d_camera_hints = false")
$config | Set-Content -Encoding ascii "$run/openttd.cfg"
$commands = @('pause','setting gui.errmsg_duration 0','renderer_3d on','renderer_3d lod off','renderer_3d shadows contact')
if ($VerifyGPU) { $commands += 'renderer_3d verifygpu on' }
switch ($Scene) {
    'infrastructure' {
        $commands += 'scrollto instant 29 33','zoomto 1'
        $views = @(
            "station|scrollto instant 15 29`nrenderer_3d highlight 15 29",
            "industry|scrollto instant 14 27`nrenderer_3d highlight 14 27",
            "bridge|scrollto instant 20 29`nrenderer_3d highlight 20 29",
            "slope|scrollto instant 34 30`nrenderer_3d highlight 34 30",
            "preview|scrollto instant 28 29`nrenderer_3d highlight off`nrenderer_3d preview 25 29 30 29",
            "rotated|renderer_3d previewclear`nscrollto instant 29 30`nrenderer_3d highlight 29 30`nrenderer_3d camera 45 80",
            "secondary|renderer_3d viewport",
            "manual-hidden|renderer_3d visibility 2 hidden`nrenderer_3d visibility 4 hidden",
            "manual-transparent|renderer_3d visibility 2 transparent`nrenderer_3d visibility 4 transparent",
            "locked|renderer_3d visibility 2 solid`nrenderer_3d visibility 4 solid`nrenderer_3d visibilitylock 2 on`nrenderer_3d visibilitylock 4 on",
            "unfocused|renderer_3d visibilitylock 2 off`nrenderer_3d visibilitylock 4 off`nrenderer_3d highlight off`nrenderer_3d previewclear`nrenderer_3d camera 0 100",
            'selected|renderer_3d vehiclewindows 2',
            'chase|renderer_3d view all chase',
            'cab|renderer_3d view all cab',
            "closed|renderer_3d vehiclewindows 0"
        )
    }
    'town' {
        $commands += 'scrollto instant 258 276','zoomto 1'
        $views = @(
            'town|renderer_3d highlight 258 276',
            'town-moved|renderer_3d highlight 260 276',
            'town90|renderer_3d camera 90 80',
            'town180|renderer_3d camera 180 100',
            "town-hidden|renderer_3d visibility 2 hidden",
            "town-transparent|renderer_3d visibility 2 transparent",
            "town-locked|renderer_3d visibility 2 solid`nrenderer_3d visibilitylock 2 on",
            "town-unlocked|renderer_3d visibilitylock 2 off",
            "town-far|zoomto 4",
            "town-clear|renderer_3d highlight off"
        )
    }
    'fleet' {
        # Populate camera follow state before pausing the comparison sequence.
        $commands = @('setting gui.errmsg_duration 0','renderer_3d on','renderer_3d lod off','renderer_3d shadows contact','scrollto instant 256 256','zoomto 2','renderer_3d vehiclewindows 4','renderer_3d windowsize all 550 300')
        if ($VerifyGPU) { $commands += 'renderer_3d verifygpu on' }
        $views = @("fleet|pause",'fleet-chase|renderer_3d view all chase','fleet-cab|renderer_3d view all cab',"fleet-closed|renderer_3d vehiclewindows 0")
    }
}
$frame = if ($Scene -eq 'fleet') { 300 } else { 50 }
foreach ($view in $views) {
    $name,$setup = $view -split '\|',2
    foreach ($line in ($setup -split "`n")) { $commands += "renderer_3d after $frame $line" }
    $frame += 30
    foreach ($mode in @('off','on','restored')) {
        $value = if ($mode -eq 'on') { 'true' } else { 'false' }
        $commands += "renderer_3d after $frame setting gui.renderer_3d_auto_visibility $value"
        $commands += "renderer_3d after $frame renderer_3d focusstats $name-$mode"
        $commands += "renderer_3d after $frame screenshot $name-$mode"
        $frame += 35
    }
}
$commands += "renderer_3d after $frame quit"
$commands | Set-Content -Encoding ascii "$run/scripts/game_start.scr"
# Save only this isolated fixture's config, then verify restart and the actual menu keyboard handler.
$arguments = '-c "{0}" -X -QQ -I OpenGFX -v win32-opengl -b {1} -s null -m null -d driver=1 -g "{2}"' -f "$run/openttd.cfg",$Blitter,$FixtureSave
function Invoke-VisibilityRun([string]$Prefix) {
    $process = Start-Process $exe -ArgumentList $arguments -WorkingDirectory $build -WindowStyle Hidden -PassThru -RedirectStandardOutput "$run/${Prefix}stdout.log" -RedirectStandardError "$run/${Prefix}stderr.log"
    $null = $process.Handle
    try {
        $deadline = (Get-Date).AddSeconds(300)
        while (!$process.WaitForExit(1000)) { if ((Get-Date) -gt $deadline) { throw "Timed out: $run" } }
        if ($process.ExitCode -ne 0) { throw "Exit $($process.ExitCode): $run" }
    } finally { if (!$process.HasExited) { $process.Kill(); $process.WaitForExit() } }
}
Invoke-VisibilityRun ''
@'
pause
renderer_3d after 40 renderer_3d focusstats persisted-off
renderer_3d after 50 renderer_3d toolbar key menu
renderer_3d after 50 renderer_3d toolbar key down
renderer_3d after 50 renderer_3d toolbar key down
renderer_3d after 50 renderer_3d toolbar key down
renderer_3d after 50 renderer_3d toolbar key enter
renderer_3d after 80 renderer_3d focusstats menu-on
renderer_3d after 90 renderer_3d toolbar open
renderer_3d after 110 screenshot menu
renderer_3d after 130 renderer_3d toolbar key escape
renderer_3d after 140 quit
'@ | Set-Content -Encoding ascii "$run/scripts/game_start.scr"
Invoke-VisibilityRun 'restart-'
@{scene=$Scene; scale=$Scale; blitter=$Blitter; verify_gpu=[bool]$VerifyGPU; sha256=(Get-FileHash "$build/Release/openttd.exe").Hash; fixture=$FixtureSave} | ConvertTo-Json | Set-Content "$run/environment.json"
python "$PSScriptRoot/verify-phase95d-visibility.py" $run
if ($LASTEXITCODE -ne 0) { throw 'Phase 9.5d verification failed' }
