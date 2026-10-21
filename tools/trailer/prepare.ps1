param([string]$Tag = 'build', [string]$SourceSave = 'C:\Users\8bits\Documents\OpenTTD\save\city_save.sav', [int]$Ticks = 40000, [int]$Months = 12, [switch]$Reload)
$ErrorActionPreference = 'Stop'
$workspace = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$build = Join-Path $workspace 'build/baseline'
$run = Join-Path $workspace ".runtime/trailer-$Tag"
if (Test-Path -LiteralPath $run) { throw "Run exists: $run" }
New-Item -ItemType Directory -Force "$run/baseset","$run/lang","$run/scripts","$run/ai/trailercity","$run/save" | Out-Null
New-Item -ItemType Directory -Force "$run/ai/library" | Out-Null
Copy-Item 'C:/Users/8bits/Documents/OpenTTD/content_download/ai/*.tar' "$run/ai"
Copy-Item 'C:/Users/8bits/Documents/OpenTTD/content_download/ai/library/*.tar' "$run/ai/library"
Copy-Item "$build/ai/compat_*.nut" "$run/ai"
Copy-Item "$build/baseset/*" "$run/baseset"
Copy-Item "$build/lang/english.lng" "$run/lang"
Copy-Item "$workspace/.runtime/baseline/baseset/*.tar" "$run/baseset"
Copy-Item "$PSScriptRoot/ai/*.nut" "$run/ai/trailercity"
Copy-Item -LiteralPath $SourceSave -Destination "$run/source.sav"
@'
[gui]
show_finances = false
autosave_interval = 0
autosave_on_exit = false
pause_on_newgame = false
[misc]
language = english.lng
resolution = 1600,900
fullscreen = false
savegame_format = zlib
[news_display]
company_info = off
arrival_other = off
advice = off
new_vehicles = off
'@ | Set-Content -Encoding ascii "$run/openttd.cfg"
@'
script console.log
setting difficulty.infinite_money true
setting difficulty.town_council_tolerance 3
setting construction.raw_industry_construction 1
setting construction.terraform_per_64k_frames 1000000
setting construction.terraform_frame_burst 32768
setting economy.multiple_industry_per_town true
setting difficulty.vehicle_breakdowns 0
setting difficulty.disasters false
start_ai TrailerCityBuilder
unpause
schedule on-next-calendar-month scripts/month0.scr
'@ | Set-Content -Encoding ascii "$run/scripts/game_start.scr"
if ($Reload) {
    (Get-Content -Raw -LiteralPath "$run/scripts/game_start.scr").Replace('start_ai TrailerCityBuilder','echo Replaying existing trailer fleet') | Set-Content -Encoding ascii "$run/scripts/game_start.scr"
}
@'
save trailer-city
quit
'@ | Set-Content -Encoding ascii "$run/scripts/finish.scr"
for ($i=0;$i -lt $Months;$i++) {
    $nextStep = if ($i -eq $Months-1) { 'exec scripts/finish.scr' } else { "schedule on-next-calendar-month scripts/month$($i+1).scr" }
    $nextStep | Set-Content -Encoding ascii "$run/scripts/month$i.scr"
}
$exe = "$run/openttd-console.exe"
Copy-Item "$build/Release/openttd.exe" $exe
Copy-Item "$build/Release/*.dll" $run
& 'C:/Program Files (x86)/Microsoft Visual Studio/2022/BuildTools/VC/Tools/MSVC/14.44.35207/bin/Hostx64/x64/editbin.exe' /nologo /subsystem:console $exe
if ($LASTEXITCODE -ne 0) { throw 'editbin failed' }
$arguments = '-c "{0}" -x -X -QQ -I OpenGFX -v null:ticks={1} -s null -m null -d script=3 -g "{2}"' -f "$run/openttd.cfg",$Ticks,"$run/source.sav"
$process = Start-Process $exe -ArgumentList $arguments -WorkingDirectory $run -WindowStyle Hidden -PassThru -RedirectStandardOutput "$run/stdout.log" -RedirectStandardError "$run/stderr.log"
Write-Output "PID=$($process.Id) RUN=$run"
