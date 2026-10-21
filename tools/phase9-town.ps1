param([string]$RunTag = 'phase9-dense-town')
# Grow a town in an isolated copy of the fleet fixture through OpenTTD's existing command.
$ErrorActionPreference = 'Stop'
if ($RunTag -notmatch '^[a-zA-Z0-9_-]+$') { throw 'Use a simple run tag' }
$workspace = Split-Path -Parent $PSScriptRoot
$build = Join-Path $workspace 'build/baseline'
$fixture = Join-Path $workspace 'OpenTTD-15.3/OpenTTD-15.3/docs/3d/fixtures'
$run = Join-Path $workspace ".runtime/$RunTag"
if (Test-Path -LiteralPath $run) { throw "Use a new run tag: $run already exists" }
New-Item -ItemType Directory -Force "$run/baseset","$run/lang","$run/scripts","$run/ai/fleet3d" | Out-Null
Copy-Item "$build/baseset/*" "$run/baseset"
Copy-Item "$build/lang/*.lng" "$run/lang"
Copy-Item "$workspace/.runtime/baseline/baseset/*.tar" "$run/baseset"
Copy-Item "$fixture/phase7/fleet/ai/*.nut" "$run/ai/fleet3d"
Copy-Item "$fixture/phase6/coverage.cfg" "$run/openttd.cfg"
@'
renderer_3d fixturetown 256 256 2000
setting gui.fast_forward_speed_limit 2000
renderer_3d fastforward on
unpause
schedule on-next-calendar-month scripts/month0.scr
'@ | Set-Content -Encoding ascii "$run/scripts/game_start.scr"
for ($i = 0; $i -lt 12; ++$i) {
    $step = if ($i -eq 11) { "save p96-dense-town`nquit" } else { "schedule on-next-calendar-month scripts/month$($i + 1).scr" }
    $step | Set-Content -Encoding ascii "$run/scripts/month$i.scr"
}
$exe = Join-Path $build "$RunTag-console.exe"
Copy-Item "$build/Release/openttd.exe" $exe
& 'C:/Program Files (x86)/Microsoft Visual Studio/2022/BuildTools/VC/Tools/MSVC/14.44.35207/bin/Hostx64/x64/editbin.exe' /nologo /subsystem:console $exe
if ($LASTEXITCODE -ne 0) { throw 'editbin failed' }
$arguments = '-c "{0}" -x -X -QQ -I OpenGFX -v null:ticks=40000 -s null -m null -d driver=1,script=3 -g "{1}"' -f "$run/openttd.cfg","$fixture/phase7/fleet/fleet-9.sav"
$process = Start-Process $exe -ArgumentList $arguments -WorkingDirectory $build -WindowStyle Hidden -PassThru -RedirectStandardOutput "$run/stdout.log" -RedirectStandardError "$run/stderr.log"
$handle = $process.Handle
try {
    $deadline = (Get-Date).AddSeconds(180)
    while (!$process.WaitForExit(1000)) { if ((Get-Date) -gt $deadline) { throw 'Town fixture timed out' } }
    if ($process.ExitCode -ne 0) { throw "Town fixture exit $($process.ExitCode)" }
} finally { if (!$process.HasExited) { $process.Kill(); $process.WaitForExit() } }
$log = Get-Content -Raw "$run/stderr.log"
if ($log -notmatch 'PHASE96 TOWN ok=true .*houses_after=(\d+) population=(\d+)' -or [int]$Matches[1] -lt 500) { throw 'Expected at least 500 houses; inspect stderr.log' }
$save = Join-Path $run 'save/p96-dense-town.sav'
if (!(Test-Path -LiteralPath $save)) { throw 'Town save missing' }
Select-String -Path "$run/stderr.log" -Pattern 'PHASE96 TOWN'
Write-Host "Fixture: $save"
