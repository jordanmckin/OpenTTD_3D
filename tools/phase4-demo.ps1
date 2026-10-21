param([switch]$Generate, [switch]$SmokeTest)
# Reproducible infrastructure demo using an isolated OpenTTD profile.
$ErrorActionPreference = 'Stop'
if ($Generate -and $SmokeTest) { throw 'Use -Generate or -SmokeTest, not both.' }
$workspace = Split-Path -Parent $PSScriptRoot
$fixture = Join-Path $workspace 'OpenTTD-15.3/OpenTTD-15.3/docs/3d/fixtures/phase4'
$build = Join-Path $workspace 'build/baseline'
$demo = Join-Path $workspace '.runtime/phase4-demo'
$exe = Join-Path $build 'Release/openttd.exe'
$graphics = Join-Path $workspace '.runtime/baseline/baseset/4f474658-OpenGFX-7.1.tar'
$save = Join-Path $fixture 'infrastructure.sav'
foreach ($required in @($exe,$graphics,(Join-Path $build 'lang/english.lng'),(Join-Path $build 'baseset/openttd.grf'))) {
    if (!(Test-Path -LiteralPath $required)) { throw "Missing $required. See docs/3d/phase4.md." }
}
if (!$Generate -and !(Test-Path -LiteralPath $save)) { throw "Missing demo save: $save" }
New-Item -ItemType Directory -Force "$demo/baseset","$demo/lang","$demo/scripts","$demo/ai/infrastructure3d" | Out-Null
Copy-Item (Join-Path $build 'lang/*.lng') "$demo/lang"
Copy-Item (Join-Path $build 'baseset/*') "$demo/baseset"
Copy-Item -LiteralPath $graphics -Destination "$demo/baseset"
Copy-Item -LiteralPath (Join-Path $fixture 'infrastructure.cfg') -Destination "$demo/openttd.cfg"
Copy-Item (Join-Path $fixture 'ai/*.nut') "$demo/ai/infrastructure3d"
$arguments = '-c "{0}" -x -X -QQ -I OpenGFX -v win32-opengl -b 32bpp-optimized -s null -m null' -f "$demo/openttd.cfg"
if ($Generate) {
    Copy-Item (Join-Path $fixture 'generate/*.scr') "$demo/scripts"
    $arguments += ' -g -G 20261016'
} else {
    $arguments += ' -g "{0}"' -f $save
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
}
if ($Generate -or $SmokeTest) {
    $started = Get-Date
    $process = Start-Process -FilePath $exe -ArgumentList $arguments -WorkingDirectory $build -WindowStyle Hidden -PassThru
    while (!$process.WaitForExit(1000)) {
        if (((Get-Date)-$started).TotalSeconds -gt 240) {
            $process.Kill()
            throw 'Phase 4 scripted run timed out.'
        }
    }
    if ($process.ExitCode -ne 0) { throw "OpenTTD exited with $($process.ExitCode)." }
    $captureName = if ($Generate) { 'phase4-generated.bmp' } else { 'phase4-reloaded.bmp' }
    $capture = Get-Item "$demo/screenshot/$captureName" -ErrorAction Stop
    if ($capture.LastWriteTime -lt $started) { throw 'No fresh screenshot was produced.' }
    if ($Generate) {
        $generated = Get-Item "$demo/save/phase4-generated.sav" -ErrorAction Stop
        if ($generated.LastWriteTime -lt $started) { throw 'No fresh save was produced.' }
        Write-Host "Generated fixture: $($generated.FullName). Review the route and AI log before replacing the checked-in fixture."
    }
    Write-Host "Phase 4 Release run exited normally. Capture: $($capture.FullName)"
    return
}
Write-Host 'Phase 4: coal train, road traffic, bridges, tunnels, slopes, and a level crossing.'
Write-Host 'Starts paused. Use the pause toolbar button to run. Console: renderer_3d off/on.'
Write-Host 'The routes belong to company 2. Offline cheat window: Ctrl+Alt+C > Change company.'
Start-Process -FilePath $exe -ArgumentList $arguments -WorkingDirectory $build | Out-Null
