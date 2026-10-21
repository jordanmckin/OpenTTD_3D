param([ValidateSet('Climates','Coverage','Reload','Rail')][string]$Mode = 'Climates')
$ErrorActionPreference = 'Stop'
$workspace = Split-Path -Parent $PSScriptRoot
$build = Join-Path $workspace 'build/baseline'
$fixture = Join-Path $workspace 'OpenTTD-15.3/OpenTTD-15.3/docs/3d/fixtures/phase6'
$exe = Join-Path $build "phase6-$Mode-console.exe"
$editbin = 'C:/Program Files (x86)/Microsoft Visual Studio/2022/BuildTools/VC/Tools/MSVC/14.44.35207/bin/Hostx64/x64/editbin.exe'
Copy-Item -LiteralPath "$build/Release/openttd.exe" -Destination $exe
& $editbin /nologo /subsystem:console $exe
if ($LASTEXITCODE -ne 0) { throw 'Could not prepare console executable.' }
$cases = if ($Mode -eq 'Climates') { @('temperate','arctic','tropic','toyland') } else { @($Mode.ToLower()) }
foreach ($case in $cases) {
    $run = Join-Path $workspace ".runtime/phase6-$case"
    New-Item -ItemType Directory -Force "$run/baseset","$run/lang","$run/scripts","$run/ai/coverage3d" | Out-Null
    Copy-Item "$build/baseset/*" "$run/baseset"
    Copy-Item "$build/lang/*.lng" "$run/lang"
    Copy-Item "$workspace/.runtime/baseline/baseset/*.tar" "$run/baseset"
    Copy-Item "$fixture/ai/*.nut" "$run/ai/coverage3d"
    if ($Mode -eq 'Rail') {
        New-Item -ItemType Directory -Force "$run/ai/diagonal3d","$run/ai/infrastructure3d" | Out-Null
        Copy-Item "$fixture/rail/ai/*.nut" "$run/ai/diagonal3d"
        Copy-Item "$fixture/../phase4/ai/*.nut" "$run/ai/infrastructure3d"
    }
    $config = Get-Content -Raw "$fixture/coverage.cfg"
    if ($Mode -eq 'Climates') {
        $config = $config.Replace('landscape = temperate',"landscape = $case").Replace('land_generator = 0',"land_generator = 1`nsnow_line_height = 3").Replace('terrain_type = 0','terrain_type = 3').Replace('industry_density = 0','industry_density = 3')
    }
    $config | Set-Content -Encoding ascii "$run/openttd.cfg"
    if ($Mode -eq 'Coverage') {
        Copy-Item "$fixture/generate/*.scr" "$run/scripts"
    } elseif ($Mode -eq 'Rail') {
        Copy-Item "$fixture/rail/*.scr" "$run/scripts"
    } else {
        @'
renderer_3d on
renderer_3d camera 0 100
scrollto instant 32 32
zoomto 3
unpause
setting gui.fast_forward_speed_limit 1000
renderer_3d fastforward on
schedule on-next-calendar-month scripts/check.scr
'@ | Set-Content -Encoding ascii "$run/scripts/game_start.scr"
        @'
renderer_3d coverage
renderer_3d check
schedule on-next-calendar-month scripts/capture.scr
'@ | Set-Content -Encoding ascii "$run/scripts/check.scr"
        "screenshot phase6-$case`nschedule on-next-calendar-month scripts/finish.scr" | Set-Content -Encoding ascii "$run/scripts/capture.scr"
        "save phase6-$case`nquit" | Set-Content -Encoding ascii "$run/scripts/finish.scr"
        if ($Mode -eq 'Reload') {
            "screenshot phase6-reload`nschedule on-next-calendar-month scripts/ship-view.scr" | Set-Content -Encoding ascii "$run/scripts/capture.scr"
            "scrollto instant 23 44`nzoomto 1`nschedule on-next-calendar-month scripts/ship-capture.scr" | Set-Content -Encoding ascii "$run/scripts/ship-view.scr"
            "screenshot phase6-ship`nrenderer_3d coverage`nschedule on-next-calendar-month scripts/air-view.scr" | Set-Content -Encoding ascii "$run/scripts/ship-capture.scr"
            "scrollto instant 33 8`nzoomto 1`nschedule on-next-calendar-month scripts/air-capture.scr" | Set-Content -Encoding ascii "$run/scripts/air-view.scr"
            "screenshot phase6-aircraft`nrenderer_3d coverage`nschedule on-next-calendar-month scripts/finish.scr" | Set-Content -Encoding ascii "$run/scripts/air-capture.scr"
        }
    }
    $argsLine = '-c "{0}" -x -X -QQ -I OpenGFX -v win32-opengl -b 32bpp-optimized -s null -m null -d driver=1,script=3' -f "$run/openttd.cfg"
    if ($Mode -eq 'Reload') {
        $save = Join-Path $workspace '.runtime/phase6-coverage/save/phase6-coverage.sav'
        if (!(Test-Path $save)) { throw "Missing $save" }
        $argsLine += ' -g "{0}"' -f $save
    } elseif ($Mode -eq 'Rail') {
        $argsLine += ' -g "{0}"' -f "$fixture/../phase4/infrastructure.sav"
    } else { $argsLine += ' -g -G 20261016' }
    $started = Get-Date
    $process = Start-Process -FilePath $exe -ArgumentList $argsLine -WorkingDirectory $build -WindowStyle Hidden -RedirectStandardOutput "$run/stdout.log" -RedirectStandardError "$run/stderr.log" -PassThru
    $processHandle = $process.Handle # Retain the handle so ExitCode remains available on Windows PowerShell.
    while (!$process.WaitForExit(1000)) {
        if (((Get-Date)-$started).TotalSeconds -gt 600) { $process.Kill(); throw "$case timed out" }
    }
    if ($process.ExitCode -ne 0) { throw "$case exited $($process.ExitCode)" }
    $log = Get-Content -Raw "$run/stderr.log"
    if ($log -match 'DIAGONAL FAILED|PHASE6 FAILED|Your script made an error|Assertion failed|3D proof failed|3D proof OpenGL error|failures=[1-9]') { throw "$case failed: inspect $run/stderr.log" }
    if ($Mode -eq 'Rail') {
        if ($log -notmatch 'DIAGONAL READY pieces=24') { throw 'Diagonal fixture never became ready' }
    } elseif ($log -notmatch 'PHASE6 COVERAGE' -or $log -notmatch '3D CHECK:') { throw "$case missing diagnostics" }
    if ($Mode -eq 'Coverage' -and $log -notmatch 'PHASE6 READY') { throw 'Coverage fixture never became ready' }
    if ($Mode -eq 'Reload' -and $log -notmatch 'PHASE6 RELOADED') { throw 'AI did not resume its saved state' }
    $captures = if ($Mode -eq 'Rail') { @('phase6-diagonal-a','phase6-diagonal-b') } else { @("phase6-$case") }
    foreach ($name in $captures) {
        $capture = Get-Item "$run/screenshot/$name.bmp"
        if ($capture.LastWriteTime -lt $started) { throw "$case stale capture" }
    }
    Write-Host "$case passed; log and capture: $run"
}
