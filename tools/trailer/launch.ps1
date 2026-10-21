param(
    [ValidateSet('City','Freight','Whitdon','Overview','Classic','Train','Truck')][string]$Scene = 'City',
    [switch]$SmokeTest
)
$ErrorActionPreference = 'Stop'
$workspace = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$bundle = Join-Path $workspace 'artifacts/trailer-city'
$profile = Join-Path $bundle 'profile'
$build = Join-Path $workspace 'build/baseline'
$save = Join-Path $bundle 'Trailer City.sav'
$exe = Join-Path $build 'Release/openttd.exe'
foreach ($required in @($save,$exe,"$profile/openttd.cfg","$profile/ai/trailercity/main.nut")) {
    if (!(Test-Path -LiteralPath $required)) { throw "Missing trailer file: $required" }
}
$commands = @('setting gui.errmsg_duration 0','renderer_3d on','renderer_3d lod off','renderer_3d shadows contact','renderer_3d labeloptions 0 0','renderer_3d camera 0 100')
switch ($Scene) {
    'City' { $commands += @('scrollto instant 936 175','zoomto 2') }
    'Freight' { $commands += @('scrollto instant 898 147','zoomto 3') }
    'Whitdon' { $commands += @('scrollto instant 627 78','zoomto 2') }
    'Overview' { $commands += @('scrollto instant 915 158','zoomto 3') }
    'Classic' { $commands += @('renderer_3d off','scrollto instant 936 175','zoomto 2') }
    'Train' { $commands += @('scrollto instant 898 160','zoomto 2','renderer_3d view 813 cab','renderer_3d windowsize 813 1500 760') }
    'Truck' { $commands += @('scrollto instant 931 170','zoomto 2','renderer_3d view 869 cab','renderer_3d windowsize 869 1500 760') }
}
$commands += 'renderer_3d after 20 pause'
if ($SmokeTest) { $commands += @('renderer_3d after 60 screenshot trailer-launch-check','renderer_3d after 80 quit') }
$commands -join "`n" | Set-Content -Encoding ascii "$profile/scripts/game_start.scr"
$arguments = '-c "{0}" -x -X -QQ -I OpenGFX -v win32-opengl -b 32bpp-optimized -s null -m null -g "{1}"' -f "$profile/openttd.cfg",$save
$style = if ($SmokeTest) { 'Hidden' } else { 'Normal' }
$process = Start-Process $exe -ArgumentList $arguments -WorkingDirectory $build -WindowStyle $style -PassThru
if ($SmokeTest) {
    if (!$process.WaitForExit(30000)) { $process.Kill(); throw 'Trailer launcher smoke test timed out.' }
    if ($process.ExitCode -ne 0) { throw "Trailer launcher exited with $($process.ExitCode)." }
    Get-Item -LiteralPath "$profile/screenshot/trailer-launch-check.bmp" | Select-Object FullName,Length,LastWriteTime
} else { Write-Output "Opened Trailer City: $Scene. Starts paused; click Pause to run." }
