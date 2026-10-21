param(
    [string]$RunTag = 'phase95g',
    [ValidateRange(5,120)][int]$Seconds = 15,
    [string]$Executable = '',
    [string[]]$Maps = @('sq512','wide','tall'),
    [int[]]$Zooms = @(2,3,4,5),
    [string[]]$Cameras = @('classic','rotated'),
    [string[]]$Motions = @('still','pan'),
    [switch]$Paused,
    [string]$Resolution = '3840,2160',
    [ValidateSet('off','contact','sun')][string]$Shadows = 'off',
    [switch]$VerifyGPU,
    [string[]]$Extra = @(),
    [string]$Label = ''
)
# Phase 9.5g: zoomed-out management-view cost on fresh seeded maps (no vehicles), LOD off.
# Each case starts its own process from the same save. Warm-up and screenshot readback are outside
# the timed interval. Fixture saves are generated once from fixed seeds by tools/newmap-3d-check.ps1.
$ErrorActionPreference = 'Stop'
if ($RunTag -notmatch '^[a-zA-Z0-9_-]+$') { throw 'Use a simple run tag' }
# From PowerShell, -Resolution 3840,2160 binds as the array text '3840 2160'.
$Resolution = ($Resolution -split '[ ,x]+') -join ','
$workspace = Split-Path -Parent $PSScriptRoot
$build = Join-Path $workspace 'build/baseline'
$fixture = Join-Path $workspace 'OpenTTD-15.3/OpenTTD-15.3/docs/3d/fixtures'
$saves = Join-Path $workspace '.runtime/phase95g-fixtures'
if (!$Executable) { $Executable = Join-Path $build 'Release/openttd.exe' }
$sizes = @{ sq512 = @(9,9); wide = @(11,9); tall = @(9,11) }
New-Item -ItemType Directory -Force $saves | Out-Null
foreach ($map in $Maps) {
    if (!$sizes.ContainsKey($map)) { throw "Unknown map: $map" }
    if (Test-Path -LiteralPath "$saves/$map.sav") { continue }
    # Same seed and generator as the new-map startup regression; the save is paused and has no vehicles.
    $tag = "phase95g-fixture-$map-$(Get-Date -Format yyyyMMddHHmmss)"
    & "$PSScriptRoot/newmap-3d-check.ps1" -RunTag $tag -MapX $sizes[$map][0] -MapY $sizes[$map][1] -Executable $Executable
    Copy-Item -LiteralPath (Join-Path $workspace ".runtime/$tag/save/newmap.sav") -Destination "$saves/$map.sav"
}
$binaryHash = (Get-FileHash -LiteralPath $Executable -Algorithm SHA256).Hash
$exe = Join-Path $build "$RunTag-console.exe"
Copy-Item -LiteralPath $Executable -Destination $exe
& 'C:/Program Files (x86)/Microsoft Visual Studio/2022/BuildTools/VC/Tools/MSVC/14.44.35207/bin/Hostx64/x64/editbin.exe' /nologo /subsystem:console $exe
if ($LASTEXITCODE -ne 0) { throw 'editbin failed' }
foreach ($map in $Maps) { foreach ($camera in $Cameras) { foreach ($zoom in $Zooms) { foreach ($motion in $Motions) {
    if ($camera -notin @('classic','rotated') -or $motion -notin @('still','pan') -or $zoom -lt 2 -or $zoom -gt 5) { throw 'Invalid case' }
    $case = "$map-$camera-z$zoom-$motion$(if ($Paused) { '-paused' })$(if ($Label) { "-$Label" })"
    $run = Join-Path $workspace ".runtime/$RunTag-$case"
    if (Test-Path -LiteralPath $run) { throw "Use a new run tag; evidence already exists: $run" }
    New-Item -ItemType Directory -Force "$run/baseset","$run/lang","$run/scripts" | Out-Null
    Copy-Item "$build/baseset/*" "$run/baseset"
    Copy-Item "$build/lang/*.lng" "$run/lang"
    Copy-Item "$workspace/.runtime/baseline/baseset/*.tar" "$run/baseset"
    # Uncapped: the 60 Hz draw interval otherwise hides frame cost.
    $config = (Get-Content -Raw "$fixture/phase6/coverage.cfg").Replace('resolution = 1280,900',"resolution = $Resolution").Replace('[gui]',"[gui]`nrefresh_rate = 1000`nrenderer_3d_camera_hints = false")
    $config | Set-Content -Encoding ascii "$run/openttd.cfg"
    $mx = [int][Math]::Pow(2,$sizes[$map][0]); $my = [int][Math]::Pow(2,$sizes[$map][1])
    $commands = @('setting gui.errmsg_duration 0','renderer_3d on','renderer_3d performance optimized','renderer_3d lod off',"renderer_3d shadows $Shadows",
        "scrollto instant $($mx/2) $($my/2)","zoomto $zoom")
    if ($camera -eq 'rotated') { $commands += 'renderer_3d camera 45 100' }
    if (!$Paused) { $commands += 'unpause' }
    if ($VerifyGPU) { $commands += 'renderer_3d verifygpu on' }
    # Diagnostic-only console commands (for example hiding a scenery class); never used for gate cases.
    $commands += $Extra
    if ($motion -eq 'pan') {
        # A repeatable traversal: a 4x4 grid of positions across the map, a new one every 10 drawn frames, looped.
        # Every step is a new view; returning to earlier positions exercises cache reuse and eviction.
        $frame = 30
        for ($loop = 0; $loop -lt 40; $loop++) { for ($i = 0; $i -lt 16; $i++) {
            $px = [int](($i % 4 + 0.5) * $mx / 4); $py = [int](([Math]::Floor($i / 4) + 0.5) * $my / 4)
            $commands += "renderer_3d after $frame scrollto instant $px $py"
            $frame += 10
        } }
    }
    $commands -join "`n" | Set-Content -Encoding ascii "$run/scripts/game_start.scr"
    $arguments = '-c "{0}" -x -X -QQ -I OpenGFX -v win32-opengl -b 32bpp-optimized -s null -m null -d driver=2 -g "{1}"' -f "$run/openttd.cfg","$saves/$map.sav"
    $process = Start-Process $exe -ArgumentList $arguments -WorkingDirectory $build -WindowStyle Hidden -PassThru -RedirectStandardOutput "$run/stdout.log" -RedirectStandardError "$run/stderr.log"
    $null = $process.Handle
    try {
        $deadline = (Get-Date).AddSeconds(180)
        while (!(Select-String -Path "$run/stderr.log" -Pattern 'PHASE7 frame' -Quiet)) {
            if ($process.HasExited -or (Get-Date) -gt $deadline) { throw "No frames: $run" }
            Start-Sleep -Milliseconds 250
        }
        # Startup and the first cold build are reported separately by the verifier, before the offset.
        Start-Sleep -Seconds 5
        $offset = (Get-Item "$run/stderr.log").Length
        $peak = 0L
        $end = (Get-Date).AddSeconds($Seconds)
        while ((Get-Date) -lt $end) {
            if ($process.HasExited) { throw "Unexpected exit: $run" }
            $process.Refresh(); $peak = [Math]::Max($peak,$process.WorkingSet64)
            Start-Sleep -Milliseconds 250
        }
        @{case=$case; map=$map; map_x=$mx; map_y=$my; camera=$camera; zoom=$zoom; motion=$motion; paused=[bool]$Paused; seconds=$Seconds; offset=$offset; peak_bytes=$peak;
          resolution=$Resolution; shadows=$Shadows; extra=($Extra -join '; '); lod=$false; verify_gpu=[bool]$VerifyGPU; executable=(Resolve-Path -LiteralPath $Executable).Path; executable_sha256=$binaryHash;
          fixture=(Resolve-Path -LiteralPath "$saves/$map.sav").Path; fixture_sha256=(Get-FileHash -LiteralPath "$saves/$map.sav").Hash} | ConvertTo-Json | Set-Content "$run/measurement.json"
    } finally { if (!$process.HasExited) { $process.Kill(); $process.WaitForExit() } }
    Write-Host "Measured $case"
} } } }
python "$PSScriptRoot/verify-phase95g-zoomout.py" $RunTag
if ($LASTEXITCODE -ne 0) { throw 'Phase 9.5g verification failed' }
