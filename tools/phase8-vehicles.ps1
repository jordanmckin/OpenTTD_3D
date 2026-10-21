# Phase 8.5 vehicle review: load the Phase 4 fixture, follow a vehicle (-Engine, default 9) and capture it in 3D (three angles) and classic.
param([int]$Engine = 9)
$ErrorActionPreference = 'Stop'
$workspace = Split-Path -Parent $PSScriptRoot
$fixture = Join-Path $workspace 'OpenTTD-15.3/OpenTTD-15.3/docs/3d/fixtures'
$build = Join-Path $workspace 'build/baseline'
$demo = Join-Path $workspace '.runtime/phase8-vehicles'
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
Copy-Item (Join-Path $fixture 'phase8/vehicles/*.scr') "$demo/scripts"
Get-ChildItem "$demo/scripts/prepare*.scr" | ForEach-Object { (Get-Content $_.FullName) -replace '^renderer_3d follow \d+$', "renderer_3d follow $Engine" | Set-Content -Encoding ascii $_.FullName }
$arguments = '-c "{0}" -x -X -QQ -I OpenGFX -v win32-opengl -b 32bpp-optimized -s null -m null -g "{1}"' -f "$demo/openttd.cfg", $save
$started = Get-Date
$process = Start-Process -FilePath $exe -ArgumentList $arguments -WorkingDirectory $build -WindowStyle Hidden -PassThru
while (!$process.WaitForExit(1000)) {
    if (((Get-Date)-$started).TotalSeconds -gt 600) { $process.Kill(); throw 'Phase 8 vehicle review run timed out.' }
}
if ($process.ExitCode -ne 0) { throw "OpenTTD exited with $($process.ExitCode)." }
$shots = Get-ChildItem "$demo/screenshot/phase8-*" | Where-Object { $_.LastWriteTime -ge $started }
if ($shots.Count -lt 4) { throw "Expected 4 fresh screenshots, found $($shots.Count)." }
$shots | ForEach-Object { Write-Host "Capture: $($_.FullName)" }
