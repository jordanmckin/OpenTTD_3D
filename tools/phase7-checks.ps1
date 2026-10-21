param([ValidateSet('railway','construction','temperate','arctic','tropic','toyland')][string]$Scene = 'railway', [string]$RunTag = 'phase7', [ValidateRange(6,7)][int]$MapBits = 6, [switch]$Roam, [switch]$LOD, [switch]$LODOnly, [switch]$StaticModels, [switch]$StaticOnly, [switch]$InstanceStreams)
$ErrorActionPreference = 'Stop'
$LOD = $LOD -or $LODOnly
$StaticModels = $StaticModels -or $StaticOnly
$workspace = Split-Path -Parent $PSScriptRoot
$build = Join-Path $workspace 'build/baseline'
$fixture = Join-Path $workspace 'OpenTTD-15.3/OpenTTD-15.3/docs/3d/fixtures'
$run = Join-Path $workspace ".runtime/$RunTag-check-$Scene"
$exe = Join-Path $build "$RunTag-check-$Scene-console.exe"
Copy-Item "$build/Release/openttd.exe" $exe
& 'C:/Program Files (x86)/Microsoft Visual Studio/2022/BuildTools/VC/Tools/MSVC/14.44.35207/bin/Hostx64/x64/editbin.exe' /nologo /subsystem:console $exe
if ($LASTEXITCODE -ne 0) { throw 'editbin failed' }
New-Item -ItemType Directory -Force "$run/baseset","$run/lang","$run/scripts","$run/ai/infrastructure3d" | Out-Null
Copy-Item "$build/baseset/*" "$run/baseset"
Copy-Item "$build/lang/*.lng" "$run/lang"
Copy-Item "$workspace/.runtime/baseline/baseset/*.tar" "$run/baseset"
Copy-Item "$fixture/phase4/ai/*.nut" "$run/ai/infrastructure3d"
$config = Get-Content -Raw "$fixture/phase6/coverage.cfg"
$config = $config.Replace('map_x = 6',"map_x = $MapBits").Replace('map_y = 6',"map_y = $MapBits")
if ($Scene -notin @('railway','construction')) { $config = $config.Replace('landscape = temperate',"landscape = $Scene").Replace('land_generator = 0',"land_generator = 1`nsnow_line_height = 3").Replace('terrain_type = 0','terrain_type = 3').Replace('industry_density = 0','industry_density = 3') }
$config | Set-Content -Encoding ascii "$run/openttd.cfg"
@'
renderer_3d on
renderer_3d verifydirty on
renderer_3d verifygpu on
setting gui.show_finances false
scrollto instant 29 33
zoomto 2
renderer_3d vehiclewindows 4
setting gui.fast_forward_speed_limit 2000
renderer_3d fastforward on
unpause
schedule on-next-calendar-month scripts/step0.scr
'@ | Set-Content -Encoding ascii "$run/scripts/game_start.scr"
if ($LOD) { 'renderer_3d lod on' | Add-Content -Encoding ascii "$run/scripts/game_start.scr" }
$(if ($LOD) { 'on' } else { 'off' }) | Set-Content -Encoding ascii "$run/lod-requested.txt"
$(if ($LODOnly) { 'on' } else { 'off' }) | Set-Content -Encoding ascii "$run/lod-focused.txt"
$(if ($StaticModels) { 'on' } else { 'off' }) | Set-Content -Encoding ascii "$run/static-requested.txt"
if ($Scene -eq 'construction') { 'start_ai Infrastructure3DFixture' | Add-Content -Encoding ascii "$run/scripts/game_start.scr" }
$steps = @(
    "renderer_3d highlight 32 32`nrenderer_3d raise 32 32",
    "renderer_3d lower 32 32`nrenderer_3d highlight off`nrenderer_3d preview 25 31 29 31",
    "renderer_3d previewclear`nrenderer_3d visibility 1 transparent`nrenderer_3d visibility 2 transparent`nrenderer_3d visibility 3 transparent`nrenderer_3d visibility 4 transparent`nrenderer_3d visibility 5 transparent",
    "screenshot phase7-transparent",
    "renderer_3d visibility 1 hidden`nrenderer_3d visibility 2 hidden`nrenderer_3d visibility 3 hidden`nrenderer_3d visibility 4 hidden`nrenderer_3d visibility 5 hidden",
    "screenshot phase7-hidden",
    "renderer_3d visibility 1 solid`nrenderer_3d visibility 2 solid`nrenderer_3d visibility 3 solid`nrenderer_3d visibility 4 solid`nrenderer_3d visibility 5 solid`nrenderer_3d viewport",
    "screenshot phase7-restored",
    "renderer_3d camera 90 60`nrenderer_3d chunks 32",
    "screenshot phase7-rotated",
    "renderer_3d camera 270 140`nzoomto 3",
    "renderer_3d camera 0 100`nrenderer_3d chunks 16`nrenderer_3d off",
    "screenshot phase7-classic",
    "renderer_3d on`nsave phase7-check",
    "screenshot phase7-final",
    'load phase7-check.sav'
)
if ($LOD) {
    $steps = $steps[0..7] + @(
        "zoomto 4`nrenderer_3d lod on",
        "screenshot phase7-lod`nrenderer_3d instancing off",
        "screenshot phase7-lod-uniform`nrenderer_3d instancing on",
        "renderer_3d lod off`nscreenshot phase7-full-detail",
        "renderer_3d lod on`nzoomto 1"
    ) + $steps[8..($steps.Count-1)]
}
if ($StaticModels) {
    $steps = $steps[0..7] + @(
        "renderer_3d instancing off`nscreenshot phase7-static-uniform`nrenderer_3d instancing on",
        "renderer_3d instancing on`nrenderer_3d staticinstances off`nscreenshot phase7-static-baked",
        "renderer_3d staticinstances on`nscreenshot phase7-static-shared"
    ) + $steps[8..($steps.Count-1)]
}
if ($LODOnly) {
    # Focus on the new mesh selection and cache transitions. The full fixture above
    # remains available with -LOD for the broader construction/visibility gate.
    $steps = @(
        "zoomto 4`nrenderer_3d lod on`nrenderer_3d highlight 32 32`nrenderer_3d raise 32 32",
        "renderer_3d lower 32 32`nrenderer_3d highlight off`nscreenshot phase7-lod`nrenderer_3d instancing off",
        "screenshot phase7-lod-uniform`nrenderer_3d instancing on`nrenderer_3d camera 90 60",
        "renderer_3d lod off`nscreenshot phase7-full-detail",
        "renderer_3d lod on`nzoomto 1`nrenderer_3d visibility 1 transparent`nrenderer_3d viewport",
        "renderer_3d visibility 1 solid`nrenderer_3d camera 270 140`nzoomto 4`nscreenshot phase7-rotated",
        "renderer_3d camera 0 100`nrenderer_3d off`nscreenshot phase7-classic",
        "renderer_3d on`nsave phase7-check",
        "screenshot phase7-final",
        'load phase7-check.sav'
    )
}
if ($StaticOnly) {
    # Repeat the culling/placement boundary checks after a narrow renderer change.
    # Screenshots restore the uniform fallback immediately to keep game progress practical.
    $steps = @(
        "renderer_3d highlight 32 32`nrenderer_3d raise 32 32",
        "renderer_3d lower 32 32`nrenderer_3d highlight off`nrenderer_3d preview 25 31 29 31",
        "renderer_3d previewclear`nrenderer_3d visibility 1 transparent`nrenderer_3d visibility 2 transparent`nrenderer_3d visibility 3 transparent`nrenderer_3d visibility 4 transparent`nrenderer_3d visibility 5 transparent`nscreenshot phase7-transparent",
        "renderer_3d visibility 1 hidden`nrenderer_3d visibility 2 hidden`nrenderer_3d visibility 3 hidden`nrenderer_3d visibility 4 hidden`nrenderer_3d visibility 5 hidden`nscreenshot phase7-hidden",
        "renderer_3d visibility 1 solid`nrenderer_3d visibility 2 solid`nrenderer_3d visibility 3 solid`nrenderer_3d visibility 4 solid`nrenderer_3d visibility 5 solid`nrenderer_3d viewport`nscreenshot phase7-restored",
        "renderer_3d instancing off`nscreenshot phase7-static-uniform`nrenderer_3d instancing on`nrenderer_3d camera 90 60`nrenderer_3d chunks 32",
        "renderer_3d staticinstances off`nscreenshot phase7-static-baked`nrenderer_3d staticinstances on`nscreenshot phase7-static-shared`nrenderer_3d camera 270 140`nzoomto 3`nscreenshot phase7-rotated",
        "renderer_3d camera 0 100`nrenderer_3d chunks 16`nrenderer_3d off`nscreenshot phase7-classic`nrenderer_3d on`nsave phase7-check",
        "screenshot phase7-final",
        'load phase7-check.sav'
    )
}
0 | Set-Content -Encoding ascii "$run/roam-tile.txt"
if ($InstanceStreams) {
    'on' | Set-Content -Encoding ascii "$run/streams-requested.txt"
    $steps = $steps[0..7] + @(
        "renderer_3d instancestreams off`nscreenshot phase7-streamed",
        "renderer_3d instancestreams on`nscreenshot phase7-retained-stream"
    ) + $(if ($Scene -eq 'railway') {
        # Terraforming the tree at 20,25 clears it through the normal command,
        # exercising count-changing replacement after the cache has warmed up.
        @("renderer_3d raise 20 25", "renderer_3d lower 20 25")
    } else { @() }) + $steps[8..($steps.Count-1)]
}
if ($Roam) {
    $far = [int][Math]::Pow(2,$MapBits) - 24
    $far | Set-Content -Encoding ascii "$run/roam-tile.txt"
    # Edit a distant chunk more than once, then request it from a rotated view.
    # Keep the secondary view open at its previous position throughout the traversal.
    $roamSteps = @(
        "scrollto instant 8 8`nzoomto 1`nrenderer_3d raise $far $far",
        "renderer_3d lower $far $far`nrenderer_3d raise $far $far",
        "scrollto instant $far $far`nrenderer_3d camera 90 60",
        "renderer_3d pick 640 450`nscreenshot phase7-reentry",
        "renderer_3d lower $far $far`nrenderer_3d camera 270 140`nzoomto 3",
        "renderer_3d camera 0 100`nscrollto instant 29 33`nzoomto 2"
    )
    $steps = $steps[0..7] + $roamSteps + $steps[8..($steps.Count-1)]
}
for ($i=0; $i -lt $steps.Count; $i++) {
    $text = $steps[$i]
    if ($i+1 -lt $steps.Count) { $text += "`nschedule on-next-calendar-month scripts/step$($i+1).scr" }
    $text | Set-Content -Encoding ascii "$run/scripts/step$i.scr"
}
$arguments = '-c "{0}" -x -X -QQ -I OpenGFX -v win32-opengl -b 32bpp-optimized -s null -m null -d driver=1,script=3' -f "$run/openttd.cfg"
if ($Scene -eq 'railway') { $arguments += ' -g "{0}"' -f "$fixture/phase4/infrastructure.sav" } else { $arguments += ' -g -G 20261016' }
$process = Start-Process $exe -ArgumentList $arguments -WorkingDirectory $build -WindowStyle Hidden -PassThru -RedirectStandardOutput "$run/stdout.log" -RedirectStandardError "$run/stderr.log"
(Get-Date).ToUniversalTime().ToString('o') | Set-Content "$run/started.txt"
$handle = $process.Handle
try {
    $timeout = if ($MapBits -gt 6 -or $StaticModels) { 1200 } else { 600 }
    $deadline = (Get-Date).AddSeconds($timeout)
    while (!(Select-String -Path "$run/stderr.log" -Pattern 'dirty-reference' -Quiet)) {
        if ($process.HasExited -or (Get-Date) -gt $deadline) { throw 'No initial frame' }
        Start-Sleep -Milliseconds 500
    }
    # The first start script has executed. Reload the same-sized saved map in this
    # process with a different start script, exercising CPU and GPU invalidation.
    @'
renderer_3d on
renderer_3d verifydirty on
renderer_3d verifygpu on
unpause
renderer_3d fastforward on
schedule on-next-calendar-month scripts/reloaded.scr
'@ | Set-Content -Encoding ascii "$run/scripts/game_start.scr"
    "screenshot phase7-reloaded`nschedule on-next-calendar-month scripts/quit.scr" | Set-Content -Encoding ascii "$run/scripts/reloaded.scr"
    'quit' | Set-Content -Encoding ascii "$run/scripts/quit.scr"
    while (!$process.WaitForExit(1000)) { if ((Get-Date) -gt $deadline) { throw "Timed out: $run" } }
    if ($process.ExitCode -ne 0) { throw "Exit $($process.ExitCode): $run" }
} finally { if (!$process.HasExited) { $process.Kill(); $process.WaitForExit() } }
python "$PSScriptRoot/verify-phase7-checks.py" $run
if ($LASTEXITCODE -ne 0) { throw 'Correctness verification failed' }
