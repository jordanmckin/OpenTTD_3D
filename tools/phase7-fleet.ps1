param([ValidateRange(9,10)][int]$MapBits = 9, [int]$Seed = 20261016)
# Generates docs/3d/fixtures/phase7/fleet/fleet-<bits>.sav: a generated map whose fixture AI
# runs bus services in the towns nearest the centre and shuttle trains beside them.
# The save is written once the AI reports FLEET_READY; benchmarks then reload it.
$ErrorActionPreference = 'Stop'
$workspace = Split-Path -Parent $PSScriptRoot
$build = Join-Path $workspace 'build/baseline'
$fixture = Join-Path $workspace 'OpenTTD-15.3/OpenTTD-15.3/docs/3d/fixtures'
$run = Join-Path $workspace ".runtime/phase7-fleet-generate-$MapBits"
$exe = Join-Path $build 'phase7-fleet-console.exe'
Copy-Item "$build/Release/openttd.exe" $exe
& 'C:/Program Files (x86)/Microsoft Visual Studio/2022/BuildTools/VC/Tools/MSVC/14.44.35207/bin/Hostx64/x64/editbin.exe' /nologo /subsystem:console $exe
if ($LASTEXITCODE -ne 0) { throw 'editbin failed' }
if (Test-Path $run) { Remove-Item -Recurse -Force $run }
New-Item -ItemType Directory -Force "$run/baseset","$run/lang","$run/scripts","$run/ai/fleet3d" | Out-Null
Copy-Item "$build/baseset/*" "$run/baseset"
Copy-Item "$build/lang/*.lng" "$run/lang"
Copy-Item "$workspace/.runtime/baseline/baseset/*.tar" "$run/baseset"
Copy-Item "$fixture/phase7/fleet/ai/*.nut" "$run/ai/fleet3d"
$config = (Get-Content -Raw "$fixture/phase6/coverage.cfg").Replace('map_x = 6',"map_x = $MapBits").Replace('map_y = 6',"map_y = $MapBits")
$config = $config.Replace('number_towns = 1','number_towns = 3').Replace('industry_density = 0','industry_density = 3').Replace('generation_seed = 20261016',"generation_seed = $Seed")
$config | Set-Content -Encoding ascii "$run/openttd.cfg"
@'
start_ai Fleet3DFixture
setting gui.fast_forward_speed_limit 2000
renderer_3d fastforward on
unpause
schedule on-next-calendar-month scripts/check.scr
'@ | Set-Content -Encoding ascii "$run/scripts/game_start.scr"
# Each month, run ready.scr if the harness has written it.
"exec scripts/ready.scr 0`nschedule on-next-calendar-month scripts/check.scr" | Set-Content -Encoding ascii "$run/scripts/check.scr"
$arguments = '-c "{0}" -x -X -QQ -I OpenGFX -v win32-opengl -b 32bpp-optimized -s null -m null -d script=3 -g -G {1}' -f "$run/openttd.cfg", $Seed
$process = Start-Process $exe -ArgumentList $arguments -WorkingDirectory $build -WindowStyle Hidden -PassThru -RedirectStandardOutput "$run/stdout.log" -RedirectStandardError "$run/stderr.log"
try {
    $deadline = (Get-Date).AddSeconds(900)
    while (!(Select-String -Path "$run/stderr.log" -Pattern 'PHASE7 FLEET_READY' -Quiet)) {
        if (Select-String -Path "$run/stderr.log" -Pattern 'Fixture failed|Your script made an error' -Quiet) { throw "Fleet fixture failed: $run/stderr.log" }
        if ($process.HasExited -or (Get-Date) -gt $deadline) { throw "Fleet fixture did not finish: $run" }
        Start-Sleep -Milliseconds 500
    }
    # Let the fleet spread out of its depots before saving.
    Start-Sleep -Seconds 20
    "save fleet-$MapBits`nquit" | Set-Content -Encoding ascii "$run/scripts/ready.scr"
    if (!$process.WaitForExit(300000)) { throw "Fleet save timed out: $run" }
} finally { if (!$process.HasExited) { $process.Kill(); $process.WaitForExit() } }
$save = Get-ChildItem -Recurse -Path $run -Filter "fleet-$MapBits.sav" | Select-Object -First 1
if ($null -eq $save) { throw "No save written: $run" }
New-Item -ItemType Directory -Force "$fixture/phase7/fleet" | Out-Null
Copy-Item $save.FullName "$fixture/phase7/fleet/fleet-$MapBits.sav"
Select-String -Path "$run/stderr.log" -Pattern 'PHASE7 FLEET' | ForEach-Object { $_.Line }
Write-Host "Saved $fixture/phase7/fleet/fleet-$MapBits.sav"
