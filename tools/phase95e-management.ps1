param([string]$RunTag = 'phase95e-management', [int]$Scale = 100, [string]$Blitter = '32bpp-optimized', [switch]$VerifyGPU, [string]$Executable = '', [switch]$Construction)
$ErrorActionPreference = 'Stop'
if ($RunTag -notmatch '^[a-zA-Z0-9_-]+$') { throw 'Use a simple run tag' }
$workspace = Split-Path -Parent $PSScriptRoot
$build = Join-Path $workspace 'build/baseline'
if (!$Executable) { $Executable = Join-Path $build 'Release/openttd.exe' }
$Executable = (Resolve-Path -LiteralPath $Executable).Path
$fixture = Join-Path $workspace 'OpenTTD-15.3/OpenTTD-15.3/docs/3d/fixtures'
$run = Join-Path $workspace ".runtime/$RunTag"
if (Test-Path -LiteralPath $run) { throw "Use a fresh RunTag: $run" }
$exe = Join-Path $build "$RunTag-console.exe"
Copy-Item -LiteralPath $Executable -Destination $exe
& 'C:/Program Files (x86)/Microsoft Visual Studio/2022/BuildTools/VC/Tools/MSVC/14.44.35207/bin/Hostx64/x64/editbin.exe' /nologo /subsystem:console $exe
if ($LASTEXITCODE -ne 0) { throw 'editbin failed' }
New-Item -ItemType Directory -Force "$run/baseset","$run/lang","$run/scripts","$run/ai/infrastructure3d" | Out-Null
Copy-Item "$build/baseset/*" "$run/baseset"
Copy-Item "$build/lang/*.lng" "$run/lang"
Copy-Item "$workspace/.runtime/baseline/baseset/*.tar" "$run/baseset"
Copy-Item "$fixture/phase4/ai/*.nut" "$run/ai/infrastructure3d"
$config = (Get-Content -Raw "$fixture/phase6/coverage.cfg").Replace('[misc]',"[misc]`ngui_scale = $Scale").Replace('[gui]',"[gui]`nrenderer_3d_camera_hints = false")
$config | Set-Content -Encoding ascii "$run/openttd.cfg"
$commands = @('pause','setting construction.command_pause_level 3','setting gui.errmsg_duration 0','setting gui.measure_tooltip true','renderer_3d on','renderer_3d lod off','renderer_3d shadows contact','renderer_3d fixturelabels','renderer_3d labeloptions 239 127','scrollto instant 29 33','zoomto 2')
if ($VerifyGPU) { $commands += 'renderer_3d verifygpu on' }
$steps = @()
if ($Construction) {
    $steps = @(& "$PSScriptRoot/phase95e-construction-steps.ps1")
} else {
foreach ($angle in @('0 100','45 40','90 80','135 180','180 100','225 60','270 140','315 100')) {
    $yaw = ($angle -split ' ')[0]
    $steps += "renderer_3d camera $angle"
    $steps += "renderer_3d managecheck angle$yaw`nrenderer_3d labels click angle$yaw`nscreenshot angle$yaw"
}
# This region was levelled by the infrastructure fixture; construction remains through its normal commands.
$steps += 'renderer_3d labeloptions 0 127'
foreach ($case in @('45|40 41 44 41|42 41 1','90|40 41 40 44|40 42 2','135|40 41 44 45|42 43 32','180|44 41 40 45|42 43 8','225|44 45 40 41|42 43 32','270|40 45 44 41|42 43 8')) {
    $yaw,$coords,$result = $case -split '\|'
    $steps += "renderer_3d camera $yaw 100`nscrollto instant 42 42`nzoomto 1"
    $steps += "renderer_3d managedrag preview $coords"
    $emptyBefore = (($result -split ' ')[0..1] -join ' ') + ' 0'
    $steps += "renderer_3d manageresult preview$yaw $emptyBefore`nrenderer_3d managecheck preview$yaw`nscreenshot preview$yaw"
    $steps += "renderer_3d managedrag build $coords"
    $steps += "renderer_3d manageresult build$yaw $result`nrenderer_3d previewclear"
    $steps += "screenshot build$yaw"
    if ($yaw -eq '135') { $steps += 'renderer_3d manageresult build-left 41 43 16' }
    if ($yaw -eq '180') { $steps += 'renderer_3d manageresult build-upper 43 43 4' }
    $steps += "renderer_3d managedrag remove $coords"
    $empty = (($result -split ' ')[0..1] -join ' ') + ' 0'
    $steps += "renderer_3d manageresult remove$yaw $empty`nrenderer_3d previewclear"
}
$steps += 'renderer_3d managedrag area 40 41 44 45'
$steps += "renderer_3d managecheck area`nscreenshot area"
$steps += 'renderer_3d previewclear'
$steps += 'renderer_3d managedrag diagonal 44 41 40 45'
$steps += "renderer_3d managecheck diagonal`nscreenshot diagonal"
$steps += 'renderer_3d previewclear'
$steps += 'renderer_3d managedrag preview 40 41 44 41'
$steps += 'renderer_3d orbit 45 20'
$steps += "renderer_3d managecheck orbit-tool`nscreenshot orbit-tool"
$steps += 'renderer_3d home'
$steps += "renderer_3d managecheck home-tool`nscreenshot home-tool"
$steps += 'renderer_3d home'
$steps += "renderer_3d managecheck restored-tool`nrenderer_3d previewclear"
$steps += 'renderer_3d managezoom 41 41'
$steps += 'renderer_3d managedrag cancel 40 41 44 41'
$steps += "renderer_3d manageresult cancelled 42 41 0`nrenderer_3d managecheck cancelled"
$steps += "renderer_3d labeloptions 239 127`nscrollto instant 29 33`nzoomto 2`nrenderer_3d camera 90 80`nrenderer_3d viewport`nrenderer_3d vehiclewindows 2"
$steps += "renderer_3d managecheck secondary`nrenderer_3d labels click secondary`nscreenshot secondary"
$steps += 'renderer_3d view all cab'
$steps += "renderer_3d managecheck cab`nrenderer_3d labels click cab`nscreenshot cab"
$steps += 'renderer_3d view all chase'
$steps += "renderer_3d managecheck chase`nrenderer_3d labels click chase`nscreenshot chase"
$steps += 'renderer_3d toolbar resize 800 600'
$steps += "renderer_3d managecheck resized`nrenderer_3d labels click resized`nscreenshot resized"
$steps += "renderer_3d vehiclewindows 0`nrenderer_3d camera 180 100`nscrollto instant 1 1"
$steps += "renderer_3d managecheck edge`nscreenshot edge"
$steps += "renderer_3d camera 0 100`nscrollto instant 29 33"
$steps += "renderer_3d managecheck returned`nscreenshot returned`nrenderer_3d off"
$steps += "renderer_3d labels click classic2d`nscreenshot classic2d"
}
$steps += 'quit'
$frame = 40
foreach ($step in $steps) {
    foreach ($line in ($step -split "`n")) { $commands += "renderer_3d after $frame $line" }
    $frame += $(if ($Construction) { 12 } else { 35 })
}
$commands | Set-Content -Encoding ascii "$run/scripts/game_start.scr"
$arguments = '-c "{0}" -x -X -QQ -I OpenGFX -v win32-opengl -b {1} -s null -m null -d driver=1 -g "{2}"' -f "$run/openttd.cfg",$Blitter,"$fixture/phase4/infrastructure.sav"
$process = Start-Process $exe -ArgumentList $arguments -WorkingDirectory $build -WindowStyle Hidden -PassThru -RedirectStandardOutput "$run/stdout.log" -RedirectStandardError "$run/stderr.log"
$null = $process.Handle
try {
    $deadline = (Get-Date).AddSeconds(420)
    while (!$process.WaitForExit(1000)) { if ((Get-Date) -gt $deadline) { throw "Timed out: $run" } }
    if ($process.ExitCode -ne 0) { throw "Exit $($process.ExitCode): $run" }
} finally { if (!$process.HasExited) { $process.Kill(); $process.WaitForExit() } }
@{scale=$Scale; blitter=$Blitter; verify_gpu=[bool]$VerifyGPU; construction=[bool]$Construction; executable=$Executable; sha256=(Get-FileHash -LiteralPath $Executable).Hash; fixture_sha256=(Get-FileHash "$fixture/phase4/infrastructure.sav").Hash; native_input=$false} | ConvertTo-Json | Set-Content "$run/environment.json"
$verifier = if ($Construction) { 'verify-phase95e-construction.py' } else { 'verify-phase95e-management.py' }
python "$PSScriptRoot/$verifier" $run
if ($LASTEXITCODE -ne 0) { throw 'Phase 9.5e verification failed' }
