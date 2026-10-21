# Phase 8.7 effects and moving industry parts in game: the generated 128x128 temperate map (seed 20261016, with sea) in
# 1975, with a fixture AI that funds the animated industries, runs steam, diesel and electric trains (breakdowns often),
# crashes two trains and rebuilds the town's roads. -Pass scan logs where everything is; capture takes the 3D shots and
# runs the checks; classic takes the classic-view shots.
param([ValidateSet('scan','capture','classic')][string]$Pass = 'capture', [string]$RunTag = 'phase8-effects')
$ErrorActionPreference = 'Stop'
$workspace = Split-Path -Parent $PSScriptRoot
$fixture = Join-Path $workspace 'OpenTTD-15.3/OpenTTD-15.3/docs/3d/fixtures'
$build = Join-Path $workspace 'build/baseline'
$run = Join-Path $workspace ".runtime/$RunTag-$Pass"
$exe = Join-Path $build "$RunTag-console.exe"
$graphics = Join-Path $workspace '.runtime/baseline/baseset/4f474658-OpenGFX-7.1.tar'
foreach ($required in @("$build/Release/openttd.exe",$graphics)) {
    if (!(Test-Path -LiteralPath $required)) { throw "Missing $required. See docs/3d/build_and_test.md." }
}
Copy-Item "$build/Release/openttd.exe" $exe
& 'C:/Program Files (x86)/Microsoft Visual Studio/2022/BuildTools/VC/Tools/MSVC/14.44.35207/bin/Hostx64/x64/editbin.exe' /nologo /subsystem:console $exe
if ($LASTEXITCODE -ne 0) { throw 'editbin failed' }
New-Item -ItemType Directory -Force "$run/baseset","$run/lang","$run/scripts","$run/ai/effects3d" | Out-Null
Remove-Item "$run/screenshot/phase8-effects-*" -ErrorAction SilentlyContinue
Copy-Item (Join-Path $build 'lang/*.lng') "$run/lang"
Copy-Item (Join-Path $build 'baseset/*') "$run/baseset"
Copy-Item -LiteralPath $graphics -Destination "$run/baseset"
$config = (Get-Content -Raw (Join-Path $fixture 'phase6/coverage.cfg')).Replace('map_x = 6','map_x = 7').Replace('map_y = 6','map_y = 7')
# 1975 has diesel and electric engines; with never-expiring vehicles the steam engines are still for sale. Oil rigs need sea.
$config = $config.Replace('starting_year = 1950','starting_year = 1975').Replace('quantity_sea_lakes = 0','quantity_sea_lakes = 1')
$config = $config.Replace('vehicle_breakdowns = 0','vehicle_breakdowns = 2')
# competitor_speed 4 runs the AI every tick, so its GetTick() counts game ticks (the crash is timed in ticks).
$config = $config.Replace('disasters = false',"disasters = false`ntown_council_tolerance = 3`ncompetitor_speed = 4")
$config = $config.Replace('[newgrf]',"[vehicle]`nnever_expire_vehicles = true`n[newgrf]")
# No news pop-ups over the shots (roadworks, floods, crashes).
$news = (@('arrival_player','arrival_other','accident','accident_other','company_info','open','close','economy','production_player','production_other','production_nobody','advice','new_vehicles','acceptance','subsidies','general') | ForEach-Object { "$_ = off" }) -join "`n"
$config = $config -replace '\[news_display\][^\[]*', "[news_display]`n$news`n"
$config.Replace('number_towns = 1','number_towns = 4') | Set-Content -Encoding ascii "$run/openttd.cfg"
Copy-Item (Join-Path $fixture 'phase8/effects/ai/*.nut') "$run/ai/effects3d"
Remove-Item "$run/scripts/*" -ErrorAction SilentlyContinue
Copy-Item (Join-Path $fixture "phase8/effects/$Pass/*.scr") "$run/scripts"
$arguments = '-c "{0}" -x -X -QQ -I OpenGFX -v win32-opengl -b 32bpp-optimized -s null -m null -d driver=1,script=3 -g -G 20261016' -f "$run/openttd.cfg"
$started = Get-Date
$process = Start-Process -FilePath $exe -ArgumentList $arguments -WorkingDirectory $build -WindowStyle Hidden -PassThru -RedirectStandardOutput "$run/stdout.log" -RedirectStandardError "$run/stderr.log"
$handle = $process.Handle
while (!$process.WaitForExit(1000)) {
    if (((Get-Date)-$started).TotalSeconds -gt 1800) { $process.Kill(); throw 'Phase 8.7 effects run timed out.' }
}
if ($process.ExitCode -ne 0) { throw "OpenTTD exited with $($process.ExitCode)." }
Get-Content "$run/stdout.log","$run/stderr.log" | Select-String -Pattern 'PHASE8 (EFFECT|FIXTURE)|PHASE7 missed|mismatch|ERROR'
