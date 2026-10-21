param(
    [string]$RunTag = 'vehicle-follow',
    [string]$Executable = '',
    [ValidateRange(120,1200)][int]$Frames = 360,
    [switch]$AllowLag
)
# Exercise the actual render loop: a moving vehicle and its following viewport must use the same state.
$ErrorActionPreference = 'Stop'
if ($RunTag -notmatch '^[a-zA-Z0-9_-]+$') { throw 'Use a simple run tag.' }
$workspace = Split-Path -Parent $PSScriptRoot
$build = Join-Path $workspace 'build/baseline'
$fixtures = Join-Path $workspace 'OpenTTD-15.3/OpenTTD-15.3/docs/3d/fixtures'
if (!$Executable) { $Executable = Join-Path $build 'Release/openttd.exe' }
$exe = Join-Path $build "$RunTag-console.exe"
Copy-Item -LiteralPath $Executable -Destination $exe
& 'C:/Program Files (x86)/Microsoft Visual Studio/2022/BuildTools/VC/Tools/MSVC/14.44.35207/bin/Hostx64/x64/editbin.exe' /nologo /subsystem:console $exe
if ($LASTEXITCODE -ne 0) { throw 'editbin failed.' }
$results = @()
foreach ($scene in @('railway', 'airwater')) {
    foreach ($yaw in @(0, 90)) {
        $run = Join-Path $workspace ".runtime/$RunTag-$scene-$yaw"
        if (Test-Path -LiteralPath $run) { throw "Evidence already exists: $run" }
        New-Item -ItemType Directory -Force "$run/baseset","$run/lang","$run/scripts","$run/ai/infrastructure3d","$run/ai/coverage3d" | Out-Null
        Copy-Item "$build/baseset/*" "$run/baseset"
        Copy-Item "$build/lang/*.lng" "$run/lang"
        Copy-Item "$workspace/.runtime/baseline/baseset/*.tar" "$run/baseset"
        Copy-Item "$fixtures/phase4/ai/*.nut" "$run/ai/infrastructure3d"
        Copy-Item "$fixtures/phase6/ai/*.nut" "$run/ai/coverage3d"
        Get-Content -Raw "$fixtures/phase6/coverage.cfg" | Set-Content -Encoding ascii "$run/openttd.cfg"
        $commands = @('renderer_3d on', 'renderer_3d performance optimized', 'renderer_3d lod off',
            'setting gui.show_finances false', 'renderer_3d vehiclewindows 16', 'renderer_3d view all normal',
            "renderer_3d camera $yaw 100", 'unpause', "renderer_3d after $Frames pause",
            "renderer_3d after $($Frames + 10) screenshot follow-paused",
            "renderer_3d after $($Frames + 20) quit")
        $commands -join "`n" | Set-Content -Encoding ascii "$run/scripts/game_start.scr"
        $save = if ($scene -eq 'railway') { "$fixtures/phase4/infrastructure.sav" } else { "$fixtures/phase6/coverage.sav" }
        $arguments = '-c "{0}" -x -X -QQ -I OpenGFX -v win32-opengl -b 32bpp-optimized -s null -m null -d driver=3,script=3 -g "{1}"' -f "$run/openttd.cfg",$save
        $process = Start-Process $exe -ArgumentList $arguments -WorkingDirectory $build -WindowStyle Hidden -PassThru -RedirectStandardOutput "$run/stdout.log" -RedirectStandardError "$run/stderr.log"
        $handle = $process.Handle
        try {
            $deadline = (Get-Date).AddSeconds(90)
            while (!$process.WaitForExit(500)) { if ((Get-Date) -gt $deadline) { throw "Timed out: $run" } }
            if ($process.ExitCode -ne 0) { throw "Exit $($process.ExitCode): $run" }
        } finally { if (!$process.HasExited) { $process.Kill(); $process.WaitForExit() } }
        $log = Get-Content -Raw "$run/stderr.log"
        if ($log -match '3D proof failed|OpenGL error|Assertion failed|Your script made an error|Fixture failed') { throw "Runtime error: $run" }
        $samples = [regex]::Matches($log, '3D FOLLOW vehicle=(\d+) type=(\d+) position=(-?\d+),(-?\d+),(-?\d+) lag=(-?\d+),(-?\d+)')
        $types = if ($scene -eq 'railway') { @(0, 1) } else { @(2, 3) }
        foreach ($type in $types) {
            $rows = @($samples | Where-Object { [int]$_.Groups[2].Value -eq $type })
            if ($rows.Count -lt 60) { throw "Too few samples for type $type in $run" }
            $positions = @($rows | ForEach-Object { "$($_.Groups[1].Value):$($_.Groups[3].Value),$($_.Groups[4].Value),$($_.Groups[5].Value)" } | Select-Object -Unique)
            $vehicles = @($rows | ForEach-Object { $_.Groups[1].Value } | Select-Object -Unique)
            if ($positions.Count -le $vehicles.Count + 5) { throw "Type $type did not move in $run" }
            $lagging = @($rows | Where-Object { [int]$_.Groups[6].Value -ne 0 -or [int]$_.Groups[7].Value -ne 0 })
            $row = [ordered]@{scene=$scene; yaw=$yaw; type=$type; samples=$rows.Count; positions=$positions.Count; lagging=$lagging.Count}
            $results += $row
            Write-Host ($row | ConvertTo-Json -Compress)
        }
    }
}
$results | ConvertTo-Json | Set-Content "$workspace/.runtime/$RunTag-results.json"
if (!$AllowLag -and @($results | Where-Object { $_.lagging -ne 0 }).Count -ne 0) { throw 'The following camera lagged behind its rendered vehicle.' }
Write-Host "Vehicle following checks completed: $RunTag"
