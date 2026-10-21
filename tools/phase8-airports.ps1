# Phase 8.6 airports in game: the generated 128x128 temperate farm map (seed 20261016) in 2005, with a fixture AI that
# builds every airport type near the largest towns. -Pass scan logs where everything is; capture takes the shots.
param([ValidateSet('scan','capture')][string]$Pass = 'capture', [string]$RunTag = 'phase8-airports')
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
New-Item -ItemType Directory -Force "$run/baseset","$run/lang","$run/scripts","$run/ai/airports3d" | Out-Null
Remove-Item "$run/screenshot/phase8-airports-*" -ErrorAction SilentlyContinue
Copy-Item (Join-Path $build 'lang/*.lng') "$run/lang"
Copy-Item (Join-Path $build 'baseset/*') "$run/baseset"
Copy-Item -LiteralPath $graphics -Destination "$run/baseset"
# The Phase 8.3 farm scene: generated 128x128 temperate map with industries, fields in every stage and rocky land.
$config = (Get-Content -Raw (Join-Path $fixture 'phase6/coverage.cfg')).Replace('map_x = 6','map_x = 7').Replace('map_y = 6','map_y = 7')
# All nine types exist from 2002; the 1959 country airfield stays buildable; a permissive council allows them all at one town.
$config = $config.Replace('starting_year = 1950','starting_year = 2005').Replace('[economy]',"[station]`nnever_expire_airports = true`n[economy]")
$config = $config.Replace('disasters = false',"disasters = false`ntown_council_tolerance = 3")
$config.Replace('number_towns = 1','number_towns = 4').Replace('industry_density = 0','industry_density = 3') | Set-Content -Encoding ascii "$run/openttd.cfg"
Copy-Item (Join-Path $fixture 'phase8/airports/ai/*.nut') "$run/ai/airports3d"
Remove-Item "$run/scripts/*" -ErrorAction SilentlyContinue
Copy-Item (Join-Path $fixture "phase8/airports/$Pass/*.scr") "$run/scripts"
$arguments = '-c "{0}" -x -X -QQ -I OpenGFX -v win32-opengl -b 32bpp-optimized -s null -m null -d driver=1,script=3 -g -G 20261016' -f "$run/openttd.cfg"
$started = Get-Date
$process = Start-Process -FilePath $exe -ArgumentList $arguments -WorkingDirectory $build -WindowStyle Hidden -PassThru -RedirectStandardOutput "$run/stdout.log" -RedirectStandardError "$run/stderr.log"
$handle = $process.Handle
while (!$process.WaitForExit(1000)) {
    if (((Get-Date)-$started).TotalSeconds -gt 900) { $process.Kill(); throw 'Phase 8.6 airports run timed out.' }
}
if ($process.ExitCode -ne 0) { throw "OpenTTD exited with $($process.ExitCode)." }
Get-Content "$run/stdout.log","$run/stderr.log" | Select-String -Pattern 'PHASE8 (STATION|FIXTURE)|PHASE7 missed|mismatch|ERROR'
