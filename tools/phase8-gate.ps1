# Phase 8.2 gate: load the Phase 4 fixture and capture Phase 8 truck models in the 3D view.
$ErrorActionPreference = 'Stop'
$workspace = Split-Path -Parent $PSScriptRoot
$fixture = Join-Path $workspace 'OpenTTD-15.3/OpenTTD-15.3/docs/3d/fixtures'
$build = Join-Path $workspace 'build/baseline'
$demo = Join-Path $workspace '.runtime/phase8-gate'
$exe = Join-Path $build 'Release/openttd.exe'
$graphics = Join-Path $workspace '.runtime/baseline/baseset/4f474658-OpenGFX-7.1.tar'
$save = Join-Path $fixture 'phase4/infrastructure.sav'
foreach ($required in @($exe,$graphics,$save)) {
    if (!(Test-Path -LiteralPath $required)) { throw "Missing $required. See docs/3d/build_and_test.md." }
}
New-Item -ItemType Directory -Force "$demo/baseset","$demo/lang","$demo/scripts","$demo/ai/infrastructure3d" | Out-Null
Remove-Item "$demo/screenshot/phase8-*" -ErrorAction SilentlyContinue
Copy-Item (Join-Path $build 'lang/*.lng') "$demo/lang"
Copy-Item (Join-Path $build 'baseset/*') "$demo/baseset"
Copy-Item -LiteralPath $graphics -Destination "$demo/baseset"
Copy-Item -LiteralPath (Join-Path $fixture 'phase5/infrastructure.cfg') -Destination "$demo/openttd.cfg"
Copy-Item (Join-Path $fixture 'phase4/ai/*.nut') "$demo/ai/infrastructure3d"
Copy-Item (Join-Path $fixture 'phase8/gate/*.scr') "$demo/scripts"
$arguments = '-c "{0}" -x -X -QQ -I OpenGFX -v win32-opengl -b 32bpp-optimized -s null -m null -g "{1}"' -f "$demo/openttd.cfg", $save
$started = Get-Date
$process = Start-Process -FilePath $exe -ArgumentList $arguments -WorkingDirectory $build -WindowStyle Hidden -PassThru
while (!$process.WaitForExit(1000)) {
    if (((Get-Date)-$started).TotalSeconds -gt 600) { $process.Kill(); throw 'Phase 8 gate run timed out.' }
}
if ($process.ExitCode -ne 0) { throw "OpenTTD exited with $($process.ExitCode)." }
$shots = Get-ChildItem "$demo/screenshot/phase8-*" | Where-Object { $_.LastWriteTime -ge $started }
if ($shots.Count -lt 3) { throw "Expected 3 fresh screenshots, found $($shots.Count)." }
$shots | ForEach-Object { Write-Host "Capture: $($_.FullName)" }
