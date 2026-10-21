param(
    [string]$RunTag = 'phase9-performance',
    [ValidateRange(5,120)][int]$Seconds = 20,
    [string]$Executable = '',
    [string]$FixtureSave = '',
    [string[]]$Cases = @('closed','normal4','cab1','chase1','mixed4','cablarge','chaselarge','mixedlarge'),
    [switch]$VerifyGPU,
    [int]$Yaw = 0,
    [ValidateRange(40,180)][int]$Tilt = 100,
    [ValidateSet('off','contact','sun')][string]$Shadows = 'off',
    [ValidateSet('on','off')][string]$AutoVisibility = 'on'
)
# Repeatable Phase 9.6 measurements. Each case reloads the same 512-square fleet save.
# Warm-up and screenshot readback are outside the timed interval. No user saves/configs are used.
$ErrorActionPreference = 'Stop'
if ($RunTag -notmatch '^[a-zA-Z0-9_-]+$') { throw 'Use a simple run tag' }
$workspace = Split-Path -Parent $PSScriptRoot
$build = Join-Path $workspace 'build/baseline'
$fixture = Join-Path $workspace 'OpenTTD-15.3/OpenTTD-15.3/docs/3d/fixtures'
if (!$Executable) { $Executable = Join-Path $build 'Release/openttd.exe' }
if ('town' -in $Cases -and !$FixtureSave) { throw 'Generate tools/phase9-town.ps1, then pass its save with -FixtureSave for the town case.' }
if (!$FixtureSave) { $FixtureSave = Join-Path $fixture 'phase7/fleet/fleet-9.sav' }
$binaryHash = (Get-FileHash -LiteralPath $Executable -Algorithm SHA256).Hash
$exe = Join-Path $build "$RunTag-console.exe"
Copy-Item -LiteralPath $Executable -Destination $exe
& 'C:/Program Files (x86)/Microsoft Visual Studio/2022/BuildTools/VC/Tools/MSVC/14.44.35207/bin/Hostx64/x64/editbin.exe' /nologo /subsystem:console $exe
if ($LASTEXITCODE -ne 0) { throw 'editbin failed' }
foreach ($case in $Cases) {
    if ($case -notin @('closed','normal4','cab1','chase1','mixed4','cablarge','chaselarge','mixedlarge','town')) { throw "Unknown case: $case" }
    $run = Join-Path $workspace ".runtime/$RunTag-$case"
    if (Test-Path -LiteralPath $run) { throw "Use a new run tag; evidence already exists: $run" }
    New-Item -ItemType Directory -Force "$run/baseset","$run/lang","$run/scripts","$run/ai/fleet3d" | Out-Null
    Copy-Item "$build/baseset/*" "$run/baseset"
    Copy-Item "$build/lang/*.lng" "$run/lang"
    Copy-Item "$workspace/.runtime/baseline/baseset/*.tar" "$run/baseset"
    Copy-Item "$fixture/phase7/fleet/ai/*.nut" "$run/ai/fleet3d"
    $config = (Get-Content -Raw "$fixture/phase6/coverage.cfg").Replace('resolution = 1280,900','resolution = 1920,1080').Replace('[gui]',"[gui]`nrefresh_rate = 1000")
    $config | Set-Content -Encoding ascii "$run/openttd.cfg"
    $windows = if ($case -eq 'closed') { 0 } elseif ($case -in @('normal4','mixed4','mixedlarge')) { 4 } else { 1 }
    $commands = @('renderer_3d on','renderer_3d performance optimized','renderer_3d lod off','setting gui.show_finances false','scrollto instant 256 256','zoomto 2',"renderer_3d vehiclewindows $windows")
    if ($Yaw -ne 0 -or $Tilt -ne 100) { $commands += "renderer_3d camera $Yaw $Tilt" }
    # Phase 9.5c: the shadow preference, always set (the default is contact); off is the 9.6 baseline.
    $commands += "renderer_3d shadows $Shadows"
    $commands += "setting gui.renderer_3d_auto_visibility $(if ($AutoVisibility -eq 'on') { 'true' } else { 'false' })"
    if ($case -like 'cab*') { $commands += 'renderer_3d view all cab' }
    if ($case -like 'chase*') { $commands += 'renderer_3d view all chase' }
    if ($case -like 'mixed*') { $commands += 'renderer_3d view all chase','renderer_3d view train cab' }
    if ($case -in @('cablarge','chaselarge','town')) { $commands += 'renderer_3d windowsize all 1800 960' }
    if ($case -eq 'mixedlarge') { $commands += 'renderer_3d windowsize all 850 450' }
    # Dense fixture: its first train starts at (3808,4104); look northwest from (4512,4800),
    # southeast of the grown town at (258,276), so buildings fill the view ahead.
    if ($case -eq 'town') { $commands += 'renderer_3d eye all 44 43.5 160 0 -16 70' }
    $commands += 'renderer_3d views','unpause'
    if ($VerifyGPU) { $commands += 'renderer_3d verifygpu on' }
    $commands += "renderer_3d after 30 screenshot p96-$case"
    $commands -join "`n" | Set-Content -Encoding ascii "$run/scripts/game_start.scr"
    $arguments = '-c "{0}" -x -X -QQ -I OpenGFX -v win32-opengl -b 32bpp-optimized -s null -m null -d driver=2,script=3 -g "{1}"' -f "$run/openttd.cfg",$FixtureSave
    $process = Start-Process $exe -ArgumentList $arguments -WorkingDirectory $build -WindowStyle Hidden -PassThru -RedirectStandardOutput "$run/stdout.log" -RedirectStandardError "$run/stderr.log"
    $handle = $process.Handle
    try {
        $deadline = (Get-Date).AddSeconds(180)
        while (!(Select-String -Path "$run/stderr.log" -Pattern 'PHASE7 FLEET_RELOADED' -Quiet)) {
            if ($process.HasExited -or (Get-Date) -gt $deadline) { throw "Fleet did not start: $run" }
            Start-Sleep -Milliseconds 250
        }
        Start-Sleep -Seconds 5
        $offset = (Get-Item "$run/stderr.log").Length
        $peak = 0L
        $end = (Get-Date).AddSeconds($Seconds)
        while ((Get-Date) -lt $end) {
            if ($process.HasExited) { throw "Unexpected exit: $run" }
            $process.Refresh(); $peak = [Math]::Max($peak,$process.WorkingSet64)
            Start-Sleep -Milliseconds 250
        }
        @{case=$case; seconds=$Seconds; offset=$offset; peak_bytes=$peak; verify_gpu=[bool]$VerifyGPU; lod=$false; camera_yaw=$Yaw; camera_tilt=$Tilt; shadows=$Shadows; auto_visibility=$AutoVisibility; executable=(Resolve-Path -LiteralPath $Executable).Path; executable_sha256=$binaryHash; fixture=(Resolve-Path -LiteralPath $FixtureSave).Path} | ConvertTo-Json | Set-Content "$run/measurement.json"
    } finally { if (!$process.HasExited) { $process.Kill(); $process.WaitForExit() } }
    Write-Host "Measured $case"
}
python "$PSScriptRoot/verify-phase9-performance.py" $RunTag
if ($LASTEXITCODE -ne 0) { throw 'Phase 9.6 verification failed' }
