param([switch]$SmokeTest, [ValidateSet('Railway','AirWater')][string]$Scene = 'Railway')
# Reproducible asset-library demo using an isolated OpenTTD profile.
$ErrorActionPreference = 'Stop'
$workspace = Split-Path -Parent $PSScriptRoot
$fixture = Join-Path $workspace 'OpenTTD-15.3/OpenTTD-15.3/docs/3d/fixtures/phase6'
$build = Join-Path $workspace 'build/baseline'
$demo = Join-Path $workspace $(if ($Scene -eq 'AirWater') { '.runtime/phase6-airwater-demo' } else { '.runtime/phase6-demo' })
$exe = Join-Path $build 'Release/openttd.exe'
$graphics = Join-Path $workspace '.runtime/baseline/baseset/4f474658-OpenGFX-7.1.tar'
$save = Join-Path $workspace $(if ($Scene -eq 'AirWater') { 'OpenTTD-15.3/OpenTTD-15.3/docs/3d/fixtures/phase6/coverage.sav' } else { 'OpenTTD-15.3/OpenTTD-15.3/docs/3d/fixtures/phase4/infrastructure.sav' })
foreach ($required in @($exe,$graphics,(Join-Path $build 'lang/english.lng'),(Join-Path $build 'baseset/openttd.grf'))) {
    if (!(Test-Path -LiteralPath $required)) { throw "Missing $required. See docs/3d/phase6.md." }
}
if (!(Test-Path -LiteralPath $save)) { throw "Missing demo save: $save" }
New-Item -ItemType Directory -Force "$demo/baseset","$demo/lang","$demo/scripts","$demo/ai/infrastructure3d","$demo/ai/coverage3d" | Out-Null
Copy-Item (Join-Path $build 'lang/*.lng') "$demo/lang"
Copy-Item (Join-Path $build 'baseset/*') "$demo/baseset"
Copy-Item -LiteralPath $graphics -Destination "$demo/baseset"
Copy-Item -LiteralPath (Join-Path $fixture 'coverage.cfg') -Destination "$demo/openttd.cfg"
Copy-Item (Join-Path $workspace 'OpenTTD-15.3/OpenTTD-15.3/docs/3d/fixtures/phase4/ai/*.nut') "$demo/ai/infrastructure3d"
Copy-Item (Join-Path $fixture 'ai/*.nut') "$demo/ai/coverage3d"
$arguments = '-c "{0}" -x -X -QQ -I OpenGFX -v win32-opengl -b 32bpp-optimized -s null -m null' -f "$demo/openttd.cfg"
$arguments += ' -g "{0}"' -f $save
if ($SmokeTest -and $Scene -eq 'AirWater') { throw 'Use phase6-checks.ps1 -Mode Reload for the automated air/water check.' }
if ($SmokeTest) {
    Copy-Item (Join-Path $fixture 'capture/*.scr') "$demo/scripts"
} else {
    @'
renderer_3d on
renderer_3d camera 0 100
scrollto instant 29 33
zoomto 2
pause
'@ | Set-Content -Encoding ascii "$demo/scripts/game_start.scr"
}
if (!$SmokeTest -and $Scene -eq 'AirWater') {
    "renderer_3d on`nrenderer_3d camera 0 100`nscrollto instant 23 44`nzoomto 1`npause" | Set-Content -Encoding ascii "$demo/scripts/game_start.scr"
}
if ($SmokeTest) {
    $started = Get-Date
    $process = Start-Process -FilePath $exe -ArgumentList $arguments -WorkingDirectory $build -WindowStyle Hidden -PassThru
    $processHandle = $process.Handle # Retain the handle so ExitCode remains available on Windows PowerShell.
    while (!$process.WaitForExit(1000)) {
        if (((Get-Date)-$started).TotalSeconds -gt 600) {
            $process.Kill()
            throw 'Phase 6 scripted run timed out.'
        }
    }
    if ($process.ExitCode -ne 0) { throw "OpenTTD exited with $($process.ExitCode)." }
    $captureName = 'phase6-restored.bmp'
    $capture = Get-Item "$demo/screenshot/$captureName" -ErrorAction Stop
    if ($capture.LastWriteTime -lt $started) { throw 'No fresh screenshot was produced.' }
    Write-Host "Phase 6 Release run exited normally. Capture: $($capture.FullName)"
    return
}
Write-Host 'Phase 6: fixed-camera construction, visibility controls and secondary viewports.'
Write-Host 'Starts paused. Use the pause toolbar button to run. Console: renderer_3d off/on.'
Write-Host 'Press X for transparency; Ctrl+X opens the transparency toolbar. See docs/3d/phase6-manual-tests.md.'
if ($Scene -eq 'AirWater') { Write-Host 'Aircraft view: console scrollto instant 33 8. Ship view: scrollto instant 23 44.' }
Write-Host 'The routes belong to company 2. Offline cheat window: Ctrl+Alt+C > Change company.'
Start-Process -FilePath $exe -ArgumentList $arguments -WorkingDirectory $build | Out-Null
