param([string]$RunTag = 'rotation-layer', [int]$Seconds = 12, [ValidateRange(0,4)][int]$Windows = 0, [switch]$FastForward, [switch]$Rotate, [ValidateSet('32bpp-optimized','40bpp-anim')][string]$Blitter = '32bpp-optimized', [string]$Resolution = '1280,900', [switch]$LOD)
$ErrorActionPreference = 'Stop'
$workspace = Split-Path -Parent $PSScriptRoot
$build = Join-Path $workspace 'build/baseline'
$fixture = Join-Path $workspace 'OpenTTD-15.3/OpenTTD-15.3/docs/3d/fixtures'
$run = Join-Path $workspace ".runtime/$RunTag"
$exe = Join-Path $build "$RunTag-console.exe"
New-Item -ItemType Directory -Force "$run/baseset","$run/lang","$run/scripts","$run/ai/infrastructure3d" | Out-Null
Copy-Item "$build/Release/openttd.exe" $exe
& 'C:/Program Files (x86)/Microsoft Visual Studio/2022/BuildTools/VC/Tools/MSVC/14.44.35207/bin/Hostx64/x64/editbin.exe' /nologo /subsystem:console $exe
if ($LASTEXITCODE -ne 0) { throw 'editbin failed' }
Copy-Item "$build/baseset/*" "$run/baseset"
Copy-Item "$build/lang/*.lng" "$run/lang"
Copy-Item "$workspace/.runtime/baseline/baseset/*.tar" "$run/baseset"
Copy-Item "$fixture/phase4/ai/*.nut" "$run/ai/infrastructure3d"
(Get-Content -Raw "$fixture/phase6/coverage.cfg").Replace('resolution = 1280,900', "resolution = $Resolution") | Set-Content -Encoding ascii "$run/openttd.cfg"
@"
renderer_3d on
renderer_3d verifylayer on
scrollto instant 29 33
zoomto $(if ($LOD) { 4 } else { 1 })
renderer_3d lod $(if ($LOD) { 'on' } else { 'off' })
renderer_3d vehiclewindows $Windows
renderer_3d camera 30 100
setting gui.fast_forward_speed_limit 2000
renderer_3d fastforward $(if ($FastForward) { 'on' } else { 'off' })
unpause
"@ | Set-Content -Encoding ascii "$run/scripts/game_start.scr"
if ($Rotate) {
    # Immediate camera changes use the same invalidation as Ctrl + right drag.
    # Stay away from classic: its banner transition forces a full UI redraw.
    for ($i = 0; $i -lt 8; $i++) {
        $yaw = 30 + 35 * $i
        "renderer_3d camera $yaw 100`nschedule on-next-calendar-month scripts/turn$((1+$i)%8).scr" | Set-Content -Encoding ascii "$run/scripts/turn$i.scr"
    }
    'schedule on-next-calendar-month scripts/turn1.scr' | Add-Content -Encoding ascii "$run/scripts/game_start.scr"
}
$arguments = '-c "{0}" -x -X -QQ -I OpenGFX -v win32-opengl -b {2} -s null -m null -d driver=2,script=3 -g "{1}"' -f "$run/openttd.cfg","$fixture/phase4/infrastructure.sav",$Blitter
$process = Start-Process $exe -ArgumentList $arguments -WorkingDirectory $build -WindowStyle Hidden -PassThru -RedirectStandardOutput "$run/stdout.log" -RedirectStandardError "$run/stderr.log"
try {
    $deadline = (Get-Date).AddSeconds(90)
    while (!(Select-String -Path "$run/stderr.log" -Pattern 'layer-reference' -Quiet)) {
        if ($process.HasExited -or (Get-Date) -gt $deadline) { throw "No layer reference: $run" }
        Start-Sleep -Milliseconds 250
    }
    $end = (Get-Date).AddSeconds($Seconds)
    while ((Get-Date) -lt $end) {
        if ($process.HasExited) { throw "Unexpected exit: $run" }
        Start-Sleep -Milliseconds 250
    }
} finally {
    if (!$process.HasExited) { $process.Kill(); $process.WaitForExit() }
}
$checks = @(Select-String -Path "$run/stderr.log" -Pattern 'layer-reference valid=(\w+) differing=(\d+) pixels=(\d+) view=(\d+)' | ForEach-Object {
    $m = $_.Matches[0].Groups
    [pscustomobject]@{ valid = $m[1].Value -eq 'true'; differing = [long]$m[2].Value; pixels = [long]$m[3].Value; view = [int]$m[4].Value }
})
$failed = @($checks | Where-Object { !$_.valid -or $_.differing -ne 0 })
$errors = @(Select-String -Path "$run/stderr.log" -Pattern 'OpenGL error|reverting to classic|3D proof failed')
$result = [pscustomobject]@{ comparisons = $checks.Count; failures = $failed.Count; pixels_checked = ($checks | Measure-Object pixels -Sum).Sum; max_differing = ($checks | Measure-Object differing -Maximum).Maximum; gl_errors = $errors.Count; windows = $Windows; fast_forward = [bool]$FastForward; rotate = [bool]$Rotate; blitter = $Blitter; resolution = $Resolution }
$result | ConvertTo-Json | Set-Content "$run/result.json"
$result | Format-List
if ($checks.Count -lt 10 -or $result.pixels_checked -eq 0 -or $failed.Count -gt 0 -or $errors.Count -gt 0) { throw "Layer comparison failed: $run/result.json" }
