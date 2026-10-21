param([switch]$Generate, [switch]$SmokeTest)
# Isolated base-game railway fixture; does not modify the normal OpenTTD profile.
$ErrorActionPreference = 'Stop'
$workspace = Split-Path -Parent $PSScriptRoot
$source = Join-Path $workspace 'OpenTTD-15.3/OpenTTD-15.3'
$fixture = Join-Path $source 'docs/3d/fixtures/phase3'
$build = Join-Path $workspace 'build/baseline'
$demo = Join-Path $workspace '.runtime/phase3-demo'
$exe = Join-Path $build 'Release/openttd.exe'
$graphics = Join-Path $workspace '.runtime/baseline/baseset/4f474658-OpenGFX-7.1.tar'
foreach ($required in @($exe,$graphics,(Join-Path $fixture 'railway.sav'),(Join-Path $build 'lang/english.lng'),(Join-Path $build 'baseset/openttd.grf'))) {
    if (!(Test-Path -LiteralPath $required)) { throw "Missing $required. See docs/3d/phase3.md." }
}
New-Item -ItemType Directory -Force (Join-Path $demo 'baseset'),(Join-Path $demo 'lang'),(Join-Path $demo 'scripts'),(Join-Path $demo 'ai/railway3d') | Out-Null
# With -c and -X, OpenTTD searches the config folder and executable folder,
# not the caller's working directory. Release/ does not contain the built data.
Copy-Item (Join-Path $build 'lang/*.lng') (Join-Path $demo 'lang')
Copy-Item (Join-Path $build 'baseset/*') (Join-Path $demo 'baseset')
Copy-Item -LiteralPath $graphics -Destination (Join-Path $demo 'baseset')
Copy-Item -LiteralPath (Join-Path $fixture 'railway.cfg') -Destination (Join-Path $demo 'openttd.cfg')
Copy-Item (Join-Path $fixture 'ai/*.nut') (Join-Path $demo 'ai/railway3d')
if ($Generate) {
    Copy-Item (Join-Path $fixture 'generate/*.scr') (Join-Path $demo 'scripts')
    $gameArgs = @('-g','-G','20261016')
} else {
    @'
renderer_3d on
scrollto instant 28 27
zoomto 3
pause
'@ | Set-Content -Encoding ascii (Join-Path $demo 'scripts/game_start.scr')
    $gameArgs = @('-g',(Join-Path $fixture 'railway.sav'))
}
if ($SmokeTest) {
    if ($Generate) { throw 'Use -SmokeTest without -Generate.' }
    @'
unpause
renderer_3d on
scrollto instant 28 27
zoomto 3
setting gui.fast_forward_speed_limit 500
renderer_3d fastforward on
schedule on-next-calendar-month scripts/launcher-capture.scr
'@ | Set-Content -Encoding ascii (Join-Path $demo 'scripts/game_start.scr')
    @'
screenshot phase3-launcher-smoke
schedule on-next-calendar-month scripts/launcher-exit.scr
'@ | Set-Content -Encoding ascii (Join-Path $demo 'scripts/launcher-capture.scr')
    'quit' | Set-Content -Encoding ascii (Join-Path $demo 'scripts/launcher-exit.scr')
    $arguments = '-c "{0}" -x -X -QQ -I OpenGFX -v win32-opengl -b 32bpp-optimized -s null -m null -g "{1}"' -f (Join-Path $demo 'openttd.cfg'),(Join-Path $fixture 'railway.sav')
    $started = Get-Date
    $process = Start-Process -FilePath $exe -ArgumentList $arguments -WorkingDirectory $build -WindowStyle Hidden -PassThru
    if (!$process.WaitForExit(90000)) { Stop-Process -Id $process.Id; throw 'Launcher smoke test timed out.' }
    $capture = Get-Item (Join-Path $demo 'screenshot/phase3-launcher-smoke.bmp') -ErrorAction Stop
    if ($process.ExitCode -ne 0 -or $capture.LastWriteTime -lt $started) { throw 'Launcher smoke test failed.' }
    Write-Host "Launcher smoke test passed: $($capture.FullName)"
    return
}
Write-Host 'Use the original pause button to run the train. Console: renderer_3d off/on; renderer_3d camera 0 100.'
Write-Host 'The route belongs to company 2. In this offline fixture, Ctrl+Alt+C > Change company lets you manage it.'
Push-Location $build
try {
    & $exe -c (Join-Path $demo 'openttd.cfg') -x -X -QQ -I OpenGFX -v win32-opengl -b 32bpp-optimized -s null -m null @gameArgs
} finally {
    Pop-Location
}
