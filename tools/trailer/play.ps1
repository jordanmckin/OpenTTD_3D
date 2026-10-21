param(
    [string]$Shots = (Join-Path $PSScriptRoot 'shots.txt'),
    [string]$Resolution = '1920x1080',
    [switch]$Fullscreen,
    # Check: run hidden, screenshot every cue time into profile/screenshot, then quit.
    [switch]$Check
)
$ErrorActionPreference = 'Stop'
$workspace = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$bundle = Join-Path $workspace 'artifacts/trailer-city'
$profile = Join-Path $bundle 'profile'
$build = Join-Path $workspace 'build/baseline'
$save = Join-Path $bundle 'Trailer City.sav'
$exe = Join-Path $build 'Release/openttd.exe'
foreach ($required in @($Shots,$save,$exe,"$profile/openttd.cfg","$profile/ai/trailercity/main.nut")) {
    if (!(Test-Path -LiteralPath $required)) { throw "Missing trailer file: $required" }
}
if ($Resolution -notmatch '^(\d+)x(\d+)$') { throw "Resolution must look like 1920x1080." }

# The filming profile with this run's window size.
$config = (Get-Content -Raw "$profile/openttd.cfg") -replace '(?m)^resolution = .*$', "resolution = $($Matches[1]),$($Matches[2])" -replace '(?m)^fullscreen = .*$', "fullscreen = $(if ($Fullscreen) { 'true' } else { 'false' })"
$config | Set-Content -Encoding ascii "$profile/film.cfg"

# Each shot line becomes a cue on the trailer clock.
$cues = @()
$lastTime = 0.0
foreach ($line in Get-Content -LiteralPath $Shots) {
    $text = ($line -replace '#.*$', '').Trim()
    if ($text -eq '') { continue }
    if ($text -notmatch '^(\d+(?:\.\d+)?)\s+(.+)$') { throw "Shot line needs '<seconds> <command>': $line" }
    $time = [double]$Matches[1]
    $cues += [pscustomobject]@{ Time = $time; Command = $Matches[2].Trim() }
    if ($time -gt $lastTime) { $lastTime = $time }
}
$commands = @('setting gui.errmsg_duration 0','renderer_3d lod off','renderer_3d shadows contact','renderer_3d labeloptions 0 0','renderer_3d visibility 8 hidden','renderer_3d on','film start')
foreach ($cue in $cues) { $commands += 'film at {0} {1}' -f $cue.Time.ToString([Globalization.CultureInfo]::InvariantCulture), $cue.Command }
if ($Check) {
    $times = $cues.Time | Sort-Object -Unique
    foreach ($time in $times) {
        $at = ($time + 0.4).ToString([Globalization.CultureInfo]::InvariantCulture)
        $commands += "film at $at screenshot film-$(([int]($time * 10)).ToString('000'))"
    }
    $commands += 'film at {0} quit' -f ($lastTime + 4).ToString([Globalization.CultureInfo]::InvariantCulture)
    Remove-Item "$profile/screenshot/film-*" -ErrorAction SilentlyContinue
}
$commands -join "`n" | Set-Content -Encoding ascii "$profile/scripts/game_start.scr"

$arguments = '-c "{0}" -x -X -QQ -I OpenGFX -v win32-opengl -b 32bpp-optimized -s null -m null -g "{1}"' -f "$profile/film.cfg",$save
$style = if ($Check) { 'Hidden' } else { 'Normal' }
$process = Start-Process $exe -ArgumentList $arguments -WorkingDirectory $build -WindowStyle $style -PassThru
if ($Check) {
    if (!$process.WaitForExit(([int]$lastTime + 60) * 1000)) { $process.Kill(); throw 'Trailer check timed out.' }
    Get-ChildItem "$profile/screenshot/film-*" | Select-Object Name, Length
} else {
    Write-Output "Playing $([IO.Path]::GetFileName($Shots)): $($cues.Count) cues over $lastTime seconds. Close the game when done."
}
