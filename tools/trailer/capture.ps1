param(
    [Parameter(Mandatory=$true)][string]$SourceSave,
    [string]$Tag = 'review',
    [int]$Train = -1,
    [int]$Truck = -1
)
$ErrorActionPreference = 'Stop'
$workspace = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$build = Join-Path $workspace 'build/baseline'
$run = Join-Path $workspace ".runtime/trailer-$Tag"
if (Test-Path -LiteralPath $run) { throw "Run exists: $run" }
New-Item -ItemType Directory -Force "$run/baseset","$run/lang","$run/scripts","$run/ai/trailercity","$run/ai/library" | Out-Null
Copy-Item "$build/baseset/*" "$run/baseset"
Copy-Item "$build/lang/english.lng" "$run/lang"
Copy-Item "$workspace/.runtime/baseline/baseset/*.tar" "$run/baseset"
Copy-Item "$build/ai/compat_*.nut" "$run/ai"
Copy-Item 'C:/Users/8bits/Documents/OpenTTD/content_download/ai/*.tar' "$run/ai"
Copy-Item 'C:/Users/8bits/Documents/OpenTTD/content_download/ai/library/*.tar' "$run/ai/library"
Copy-Item "$PSScriptRoot/ai/*.nut" "$run/ai/trailercity"
@'
[gui]
show_finances = false
autosave_interval = 0
autosave_on_exit = false
[misc]
language = english.lng
resolution = 1600,900
fullscreen = false
[news_display]
company_info = off
arrival_other = off
advice = off
new_vehicles = off
'@ | Set-Content -Encoding ascii "$run/openttd.cfg"
$commands = @(
    'script capture-console.log',
    'setting gui.errmsg_duration 0', 'renderer_3d labeloptions 0 0', 'pause',
    'renderer_3d off', 'scrollto instant 936 175', 'zoomto 3',
    'renderer_3d after 45 screenshot lewisworth-classic',
    'renderer_3d after 50 renderer_3d on',
    'renderer_3d after 51 renderer_3d lod off',
    'renderer_3d after 52 renderer_3d shadows contact',
    'renderer_3d after 53 renderer_3d camera 0 100',
    'renderer_3d after 110 screenshot lewisworth-3d',
    'renderer_3d after 115 renderer_3d camera 135 90',
    'renderer_3d after 180 screenshot lewisworth-orbit',
    'renderer_3d after 184 unpause',
    'renderer_3d after 185 renderer_3d camera 0 100',
    'renderer_3d after 186 scrollto instant 898 147',
    'renderer_3d after 187 zoomto 3',
    'renderer_3d after 250 screenshot freight-district',
    'renderer_3d after 255 scrollto instant 627 78',
    'renderer_3d after 320 screenshot whitdon-3d',
    'renderer_3d after 325 scrollto instant 915 158',
    'renderer_3d after 326 zoomto 4',
    'renderer_3d after 390 screenshot city-and-freight'
)
if ($Train -ge 0 -and $Truck -ge 0) {
    $commands += @(
        "renderer_3d after 395 renderer_3d view $Train cab",
        "renderer_3d after 396 renderer_3d windowsize $Train 1500 760",
        'renderer_3d after 490 screenshot train-cab',
        "renderer_3d after 495 renderer_3d view $Train chase",
        'renderer_3d after 580 screenshot train-chase',
        'renderer_3d after 585 renderer_3d vehiclewindows 0',
        "renderer_3d after 590 renderer_3d view $Truck cab",
        "renderer_3d after 591 renderer_3d windowsize $Truck 1500 760",
        'renderer_3d after 680 screenshot truck-cab',
        'renderer_3d after 700 quit'
    )
} else { $commands += 'renderer_3d after 410 quit' }
$commands -join "`n" | Set-Content -Encoding ascii "$run/scripts/game_start.scr"
$arguments = '-c "{0}" -x -X -QQ -I OpenGFX -v win32-opengl -b 32bpp-optimized -s null -m null -d driver=1,script=3 -g "{1}"' -f "$run/openttd.cfg",$SourceSave
$process = Start-Process "$build/Release/openttd.exe" -ArgumentList $arguments -WorkingDirectory $build -WindowStyle Hidden -PassThru -RedirectStandardOutput "$run/stdout.log" -RedirectStandardError "$run/stderr.log"
Write-Output "PID=$($process.Id) RUN=$run"
