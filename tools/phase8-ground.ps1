# Phase 8.3 gate: textured ground in the temperate capture scene (Phase 4 save, Phase 5 views),
# with flat-colour A/B shots, orbit, transparency, classic switching and read-only pick/coverage audits.
param([ValidateSet('town','farm')][string]$Scene = 'town', [string]$RunTag = 'phase8-ground')
$ErrorActionPreference = 'Stop'
$workspace = Split-Path -Parent $PSScriptRoot
$fixture = Join-Path $workspace 'OpenTTD-15.3/OpenTTD-15.3/docs/3d/fixtures'
$build = Join-Path $workspace 'build/baseline'
$run = Join-Path $workspace ".runtime/$RunTag-$Scene"
$exe = Join-Path $build "$RunTag-$Scene-console.exe"
$graphics = Join-Path $workspace '.runtime/baseline/baseset/4f474658-OpenGFX-7.1.tar'
$save = Join-Path $fixture 'phase4/infrastructure.sav'
foreach ($required in @("$build/Release/openttd.exe",$graphics,$save)) {
    if (!(Test-Path -LiteralPath $required)) { throw "Missing $required. See docs/3d/build_and_test.md." }
}
Copy-Item "$build/Release/openttd.exe" $exe
& 'C:/Program Files (x86)/Microsoft Visual Studio/2022/BuildTools/VC/Tools/MSVC/14.44.35207/bin/Hostx64/x64/editbin.exe' /nologo /subsystem:console $exe
if ($LASTEXITCODE -ne 0) { throw 'editbin failed' }
New-Item -ItemType Directory -Force "$run/baseset","$run/lang","$run/scripts","$run/ai/infrastructure3d" | Out-Null
Remove-Item "$run/screenshot/phase8-ground-*" -ErrorAction SilentlyContinue
Copy-Item (Join-Path $build 'lang/*.lng') "$run/lang"
Copy-Item (Join-Path $build 'baseset/*') "$run/baseset"
Copy-Item -LiteralPath $graphics -Destination "$run/baseset"
if ($Scene -eq 'town') {
    Copy-Item -LiteralPath (Join-Path $fixture 'phase5/infrastructure.cfg') -Destination "$run/openttd.cfg"
} else {
    # Generated 128x128 temperate map with industries: farm fields in every stage and rocky land.
    $config = (Get-Content -Raw (Join-Path $fixture 'phase6/coverage.cfg')).Replace('map_x = 6','map_x = 7').Replace('map_y = 6','map_y = 7')
    $config.Replace('number_towns = 1','number_towns = 4').Replace('industry_density = 0','industry_density = 3') | Set-Content -Encoding ascii "$run/openttd.cfg"
}
Copy-Item (Join-Path $fixture 'phase4/ai/*.nut') "$run/ai/infrastructure3d"
Remove-Item "$run/scripts/*" -ErrorAction SilentlyContinue
Copy-Item (Join-Path $fixture "phase8/ground/$Scene/*.scr") "$run/scripts"
$arguments = '-c "{0}" -x -X -QQ -I OpenGFX -v win32-opengl -b 32bpp-optimized -s null -m null -d driver=1,script=3' -f "$run/openttd.cfg"
$arguments += if ($Scene -eq 'town') { ' -g "{0}"' -f $save } else { ' -g -G 20261016' }
$started = Get-Date
$process = Start-Process -FilePath $exe -ArgumentList $arguments -WorkingDirectory $build -WindowStyle Hidden -PassThru -RedirectStandardOutput "$run/stdout.log" -RedirectStandardError "$run/stderr.log"
$handle = $process.Handle
while (!$process.WaitForExit(1000)) {
    if (((Get-Date)-$started).TotalSeconds -gt 900) { $process.Kill(); throw 'Phase 8.3 gate run timed out.' }
}
if ($process.ExitCode -ne 0) { throw "OpenTTD exited with $($process.ExitCode)." }
python (Join-Path $PSScriptRoot 'verify-phase8-ground.py') $run $Scene
if ($LASTEXITCODE -ne 0) { throw 'Phase 8.3 verification failed' }
