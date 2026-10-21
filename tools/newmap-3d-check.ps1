param(
    [string]$RunTag = 'newmap-3d-check',
    [int]$MapX = 11,
    [int]$MapY = 9,
    [string]$Blitter = '32bpp-optimized',
    [string]$Executable = '',
    [switch]$DirectStart,
    [switch]$VerifyDirty,
    [int]$Seed = 20261020,
    [int]$Generator = 1
)
$ErrorActionPreference = 'Stop'
if ($RunTag -notmatch '^[a-zA-Z0-9_-]+$') { throw 'Use a simple run tag' }
$workspace = Split-Path -Parent $PSScriptRoot
$build = Join-Path $workspace 'build/baseline'
$run = Join-Path $workspace ".runtime/$RunTag"
if (Test-Path -LiteralPath $run) { throw 'Use a fresh run tag' }
if (!$Executable) { $Executable = Join-Path $build 'Release/openttd.exe' }
$exe = Join-Path $build "$RunTag-console.exe"
Copy-Item -LiteralPath $Executable -Destination $exe
& 'C:/Program Files (x86)/Microsoft Visual Studio/2022/BuildTools/VC/Tools/MSVC/14.44.35207/bin/Hostx64/x64/editbin.exe' /nologo /subsystem:console $exe
if ($LASTEXITCODE -ne 0) { throw 'editbin failed' }
New-Item -ItemType Directory -Force "$run/baseset","$run/lang","$run/scripts" | Out-Null
Copy-Item "$build/baseset/*" "$run/baseset"
Copy-Item "$build/lang/*.lng" "$run/lang"
Copy-Item "$workspace/.runtime/baseline/baseset/*.tar" "$run/baseset"
@"
[game_creation]
map_x = $MapX
map_y = $MapY
generation_seed = $Seed
landscape = temperate
starting_year = 1950
land_generator = $Generator
[difficulty]
terrain_type = 2
quantity_sea_lakes = 0
number_towns = 2
industry_density = 1
disasters = false
[gui]
renderer_3d = true
renderer_3d_camera_hints = false
renderer_3d_shadows = 1
show_finances = false
autosave_interval = 0
autosave_on_exit = false
pause_on_newgame = true
[misc]
language = english.lng
resolution = 1280,900
fullscreen = false
savegame_format = none
[newgrf]
"@ | Set-Content -Encoding ascii "$run/openttd.cfg"
@"
setting gui.errmsg_duration 0
renderer_3d lod off
scrollto instant $([int][Math]::Pow(2,$MapX-1)) $([int][Math]::Pow(2,$MapY-1))
zoomto 2
renderer_3d after 10 screenshot initial
renderer_3d after 15 save newmap
renderer_3d after 20 $(if ($VerifyDirty) { 'renderer_3d verifydirty on' } else { 'renderer_3d off' })
renderer_3d after 22 $(if ($VerifyDirty) { 'renderer_3d verifydirty off' } else { 'renderer_3d on' })
renderer_3d after 35 screenshot refreshed
renderer_3d after 40 quit
"@ | Set-Content -Encoding ascii "$run/scripts/game_start.scr"
if (!$DirectStart) { "renderer_3d after 30 newgame $Seed" | Set-Content -Encoding ascii "$run/scripts/autoexec.scr" }
$arguments = '-c "{0}" -x -X -QQ -I OpenGFX -v win32-opengl -b {1} -s null -m null -d driver=1,map=1' -f "$run/openttd.cfg",$Blitter
if ($DirectStart) { $arguments += " -g -G $Seed" }
$process = Start-Process $exe -ArgumentList $arguments -WorkingDirectory $build -WindowStyle Hidden -PassThru -RedirectStandardOutput "$run/stdout.log" -RedirectStandardError "$run/stderr.log"
$null = $process.Handle
try {
    $deadline = (Get-Date).AddSeconds(300)
    while (!$process.WaitForExit(1000)) { if ((Get-Date) -gt $deadline) { throw "Timed out: $run" } }
    if ($process.ExitCode -ne 0) { throw "Exit $($process.ExitCode): $run" }
} finally { if (!$process.HasExited) { $process.Kill(); $process.WaitForExit() } }
@{map_x=$MapX;map_y=$MapY;seed=$Seed;generator=$Generator;blitter=$Blitter;direct_start=[bool]$DirectStart;verify_dirty=[bool]$VerifyDirty;sha256=(Get-FileHash -LiteralPath $Executable).Hash} | ConvertTo-Json | Set-Content "$run/environment.json"
if (!(Test-Path -LiteralPath "$run/screenshot/initial.bmp") -or !(Test-Path -LiteralPath "$run/screenshot/refreshed.bmp")) { throw "Missing captures: $run" }
python "$PSScriptRoot/verify-newmap-3d.py" $run
if ($LASTEXITCODE -ne 0) { throw "New-map rendering verification failed: $run" }
Write-Host "New-map captures ready: $run"
