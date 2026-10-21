param([int[]]$MapBits = @(6), [int[]]$Windows = @(0,1,4), [int]$Seconds = 15, [switch]$Stress, [string]$RunTag = "phase7", [string[]]$Modes = @("baseline","optimized"), [switch]$VerifyDirty, [switch]$Pan, [ValidateSet("on","off")][string]$Ground = "on", [switch]$Fleet, [int]$Zoom = 2, [switch]$Capped, [string]$Resolution = "1280,900", [string]$Camera = "", [string]$Executable = "")
$ErrorActionPreference = 'Stop'
# From PowerShell, -Resolution 3840,2160 binds as the array text '3840 2160'.
$Resolution = ($Resolution -split '[ ,x]+') -join ','
$workspace = Split-Path -Parent $PSScriptRoot
$build = Join-Path $workspace 'build/baseline'
$fixture = Join-Path $workspace 'OpenTTD-15.3/OpenTTD-15.3/docs/3d/fixtures'
$exe = Join-Path $build 'phase7-console.exe'
if (!$Executable) { $Executable = Join-Path $build 'Release/openttd.exe' }
Copy-Item -LiteralPath $Executable -Destination $exe
& 'C:/Program Files (x86)/Microsoft Visual Studio/2022/BuildTools/VC/Tools/MSVC/14.44.35207/bin/Hostx64/x64/editbin.exe' /nologo /subsystem:console $exe
if ($LASTEXITCODE -ne 0) { throw 'editbin failed' }
foreach ($bits in $MapBits) { foreach ($views in $Windows) { foreach ($mode in $Modes) {
    if ($bits -lt 6 -or $bits -gt 10 -or $views -lt 0 -or $views -gt 16) { throw 'Invalid case' }
    if ($bits -ne 6 -and $views -ne 0 -and !$Fleet) { throw 'Generated maps have no fleet; use -Windows 0 or -Fleet.' }
    if ($Fleet -and !(Test-Path "$fixture/phase7/fleet/fleet-$bits.sav")) { throw "Run tools/phase7-fleet.ps1 -MapBits $bits first." }
    if ($Stress -and $bits -ne 6) { throw 'Stress uses the existing 64-square route.' }
    $suffix = if ($Stress) { '-stress' } else { '' }
    if ($Pan) { $suffix += '-pan' }
    if ($Fleet) { $suffix += '-fleet' }
    if ($Zoom -ne 2) { $suffix += "-z$Zoom" }
    if ($Resolution -ne '1280,900') { $suffix += '-' + $Resolution.Replace(',','x') }
    $run = Join-Path $workspace ".runtime/$RunTag-$bits-$views-$mode$suffix"
    New-Item -ItemType Directory -Force "$run/baseset","$run/lang","$run/scripts","$run/ai/infrastructure3d" | Out-Null
    Copy-Item "$build/baseset/*" "$run/baseset"
    Copy-Item "$build/lang/*.lng" "$run/lang"
    Copy-Item "$workspace/.runtime/baseline/baseset/*.tar" "$run/baseset"
    Copy-Item "$fixture/phase4/ai/*.nut" "$run/ai/infrastructure3d"
    if ($Fleet) {
        New-Item -ItemType Directory -Force "$run/ai/fleet3d" | Out-Null
        Copy-Item "$fixture/phase7/fleet/ai/*.nut" "$run/ai/fleet3d"
    }
    if ($Stress) {
        $ai = Get-Content -Raw "$run/ai/infrastructure3d/main.nut"
        $ai = $ai.Replace('function Monitor() {', @'
function Monitor() {
  for (local i=0; i<200; i++) {
   local v=AIVehicle.CloneVehicle(Tile(14,37),truck_id,true);
   Check(AIVehicle.IsValidVehicle(v),"stress clone");
   Check(AIVehicle.StartStopVehicle(v),"stress start");
  }
  print("PHASE7 STRESS_READY clones=200");
'@)
        $ai | Set-Content -Encoding ascii "$run/ai/infrastructure3d/main.nut"
    }
    $config = (Get-Content -Raw "$fixture/phase6/coverage.cfg").Replace('map_x = 6',"map_x = $bits").Replace('map_y = 6',"map_y = $bits")
    if ($bits -ne 6) { $config = $config.Replace('number_towns = 1','number_towns = 4').Replace('industry_density = 0','industry_density = 3') }
    # Uncapped by default: the draw interval otherwise hides frame cost below the 60 Hz refresh rate.
    $config = $config.Replace('resolution = 1280,900',"resolution = $Resolution")
    if (!$Capped) { $config = $config.Replace('[gui]',"[gui]`nrefresh_rate = 1000") }
    $config | Set-Content -Encoding ascii "$run/openttd.cfg"
    @"
renderer_3d on
renderer_3d performance $(if ($mode -in @('unscoped','uninstanced','lod','baked','streamed')) { 'optimized' } else { $mode })
renderer_3d scoped $(if ($mode -eq 'unscoped') { 'off' } else { 'on' })
$(if ($mode -eq 'uninstanced') { 'renderer_3d instancing off' })
renderer_3d lod $(if ($mode -eq 'lod') { 'on' } else { 'off' })
renderer_3d staticinstances $(if ($mode -eq 'baked') { 'off' } else { 'on' })
renderer_3d instancestreams $(if ($mode -eq 'streamed') { 'off' } else { 'on' })
renderer_3d ground $Ground
scrollto instant $(if ($Fleet) { "$([Math]::Pow(2,$bits)/2) $([Math]::Pow(2,$bits)/2)" } else { '29 33' })
zoomto $Zoom
renderer_3d vehiclewindows $views
unpause
"@ | Set-Content -Encoding ascii "$run/scripts/game_start.scr"
    if ($Camera) { "renderer_3d $Camera" | Add-Content -Encoding ascii "$run/scripts/game_start.scr" }
    if ($VerifyDirty) { "renderer_3d verifydirty on" | Add-Content -Encoding ascii "$run/scripts/game_start.scr" }
    if ($Pan) {
        # A repeatable traversal spanning the map, then a return to the first views.
        # Fast-forward uses the existing user control in both diagnostic policies.
        $side = [int][Math]::Pow(2,$bits)
        for ($i=0; $i -lt 16; $i++) {
            $px = [int](($i % 4 + 0.5) * $side / 4)
            $py = [int](([Math]::Floor($i / 4) + 0.5) * $side / 4)
            $next = ($i+1) % 16
            $zoom = if ($i % 3 -eq 0) { 3 } else { 2 }
            "scrollto instant $px $py`nzoomto $zoom`nschedule on-next-calendar-month scripts/pan$next.scr" | Set-Content -Encoding ascii "$run/scripts/pan$i.scr"
        }
        "setting gui.fast_forward_speed_limit 2000`nrenderer_3d fastforward on`nschedule on-next-calendar-month scripts/pan0.scr" | Add-Content -Encoding ascii "$run/scripts/game_start.scr"
    }
    if ($Stress) {
        "setting gui.fast_forward_speed_limit 1000`nrenderer_3d fastforward on" | Add-Content -Encoding ascii "$run/scripts/game_start.scr"
    }
    $arguments = '-c "{0}" -x -X -QQ -I OpenGFX -v win32-opengl -b 32bpp-optimized -s null -m null -d driver=2,script=3' -f "$run/openttd.cfg"
    if ($Fleet) { $arguments += ' -g "{0}"' -f "$fixture/phase7/fleet/fleet-$bits.sav" }
    elseif ($bits -eq 6) { $arguments += ' -g "{0}"' -f "$fixture/phase4/infrastructure.sav" } else { $arguments += ' -g -G 20261016' }
    $process = Start-Process $exe -ArgumentList $arguments -WorkingDirectory $build -WindowStyle Hidden -PassThru -RedirectStandardOutput "$run/stdout.log" -RedirectStandardError "$run/stderr.log"
    try {
        $deadline = (Get-Date).AddSeconds(300)
        $ready = if ($Stress) { 'PHASE7 STRESS_READY' } elseif ($Fleet) { 'PHASE7 FLEET_RELOADED' } else { 'PHASE7 frame' }
        while (!(Select-String -Path "$run/stderr.log" -Pattern $ready -Quiet)) {
            if ($process.HasExited -or (Get-Date) -gt $deadline) { throw "No frames: $run" }
            Start-Sleep -Milliseconds 500
        }
        $peak = 0L
        # Large-map baseline scans need a longer window for enough samples.
        $duration = if ($bits -ge 9) { [Math]::Max(45, $Seconds) } else { $Seconds }
        $end = (Get-Date).AddSeconds($duration)
        while ((Get-Date) -lt $end) {
            if ($process.HasExited) { throw "Unexpected exit: $run" }
            $process.Refresh(); $peak = [Math]::Max($peak,$process.WorkingSet64)
            Start-Sleep -Milliseconds 500
        }
        $peak | Set-Content "$run/working-set-bytes.txt"
    } finally { if (!$process.HasExited) { $process.Kill(); $process.WaitForExit() } }
    # Timed benchmark processes are deliberately terminated; no save is requested.
    Write-Host "Measured $run"
} } }
python "$PSScriptRoot/verify-phase7.py" $RunTag
if ($LASTEXITCODE -ne 0) { throw 'Benchmark verification failed' }
