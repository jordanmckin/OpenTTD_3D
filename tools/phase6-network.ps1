# Same-binary localhost synchronization check; does not assert upstream compatibility.
$ErrorActionPreference = 'Stop'
$workspace = Split-Path -Parent $PSScriptRoot
$build = Join-Path $workspace 'build/baseline'
$fixtures = Join-Path $workspace 'OpenTTD-15.3/OpenTTD-15.3/docs/3d/fixtures'
$exe = Join-Path $build 'phase6-Network-console.exe'
Copy-Item "$build/Release/openttd.exe" $exe
& 'C:/Program Files (x86)/Microsoft Visual Studio/2022/BuildTools/VC/Tools/MSVC/14.44.35207/bin/Hostx64/x64/editbin.exe' /nologo /subsystem:console $exe
if ($LASTEXITCODE -ne 0) { throw 'Could not prepare console executable.' }
foreach ($role in @('server','client')) {
    $run = Join-Path $workspace ".runtime/phase6-net-$role"
    New-Item -ItemType Directory -Force "$run/baseset","$run/lang","$run/scripts","$run/ai/infrastructure3d" | Out-Null
    Copy-Item "$build/baseset/*" "$run/baseset"
    Copy-Item "$build/lang/*.lng" "$run/lang"
    Copy-Item "$workspace/.runtime/baseline/baseset/*.tar" "$run/baseset"
    Copy-Item "$fixtures/phase4/ai/*.nut" "$run/ai/infrastructure3d"
    $config = Get-Content -Raw "$fixtures/phase6/coverage.cfg"
    $config += "`n[network]`nserver_game_type = local`nserver_port = 3976`nmin_active_clients = 0`npause_on_join = false`nclient_name = Phase6-$role`n"
    $config | Set-Content -Encoding ascii "$run/openttd.cfg"
}
$server = Join-Path $workspace '.runtime/phase6-net-server'
$client = Join-Path $workspace '.runtime/phase6-net-client'
"unpause`nschedule on-next-calendar-month scripts/month.scr" | Set-Content -Encoding ascii "$server/scripts/game_start.scr"
"schedule on-next-calendar-month scripts/finish.scr" | Set-Content -Encoding ascii "$server/scripts/month.scr"
"save phase6-network`nschedule on-next-calendar-month scripts/quit.scr" | Set-Content -Encoding ascii "$server/scripts/finish.scr"
'quit' | Set-Content -Encoding ascii "$server/scripts/quit.scr"
"renderer_3d on`nrenderer_3d camera 0 100`nschedule on-next-calendar-month scripts/classic.scr" | Set-Content -Encoding ascii "$client/scripts/on_client.scr"
"renderer_3d off`nschedule on-next-calendar-month scripts/restored.scr" | Set-Content -Encoding ascii "$client/scripts/classic.scr"
"renderer_3d on`nrenderer_3d coverage`nscreenshot phase6-network" | Set-Content -Encoding ascii "$client/scripts/restored.scr"
$serverArgs = '-c "{0}" -x -X -QQ -I OpenGFX -s null -m null -D 127.0.0.1:3976 -g "{1}" -d net=9,script=3' -f "$server/openttd.cfg","$fixtures/phase4/infrastructure.sav"
$clientArgs = '-c "{0}" -x -X -QQ -I OpenGFX -v win32-opengl -b 32bpp-optimized -s null -m null -n 127.0.0.1:3976 -d net=9,driver=1' -f "$client/openttd.cfg"
$serverProcess = $null
$clientProcess = $null
try {
    $started = Get-Date
    $serverProcess = Start-Process $exe -ArgumentList $serverArgs -WorkingDirectory $build -WindowStyle Hidden -RedirectStandardOutput "$server/stdout.log" -RedirectStandardError "$server/stderr.log" -PassThru
    $serverHandle = $serverProcess.Handle
    while (!(Select-String -LiteralPath "$server/stderr.log" -Pattern 'Listening on 127.0.0.1:3976' -Quiet)) {
        if ($serverProcess.HasExited -or ((Get-Date)-$started).TotalSeconds -gt 30) { throw 'Local server failed to listen.' }
        Start-Sleep -Milliseconds 100
    }
    $clientProcess = Start-Process $exe -ArgumentList $clientArgs -WorkingDirectory $build -WindowStyle Hidden -RedirectStandardOutput "$client/stdout.log" -RedirectStandardError "$client/stderr.log" -PassThru
    $clientHandle = $clientProcess.Handle
    while (!$serverProcess.WaitForExit(1000)) {
        if ($clientProcess.HasExited) { throw 'Client exited before server completed.' }
        if (((Get-Date)-$started).TotalSeconds -gt 360) { throw 'Network fixture timed out.' }
    }
    if ($serverProcess.ExitCode -ne 0) { throw "Server exited $($serverProcess.ExitCode)" }
    $deadline = (Get-Date).AddSeconds(10)
    while (!(Select-String -LiteralPath "$client/stderr.log" -Pattern 'Receive_SERVER_SHUTDOWN' -Quiet)) {
        if ((Get-Date) -gt $deadline) { throw 'Client did not observe normal server shutdown.' }
        Start-Sleep -Milliseconds 100
    }
    $log = Get-Content -Raw "$client/stderr.log"
    $syncs = [regex]::Matches($log,'Receive_SERVER_SYNC\(\): sync_frame=')
    if ($syncs.Count -lt 30 -or $log -notmatch 'PHASE6 COVERAGE' -or $log -match 'Sync error detected|Missed frame for sync-test|Assertion failed') { throw 'Network synchronization evidence incomplete or failed.' }
    Write-Host "Local multiplayer passed: $($syncs.Count) synchronization packets, restored 3D and normal server shutdown."
} finally {
    foreach ($process in @($clientProcess,$serverProcess)) {
        if ($null -ne $process -and !$process.HasExited) { $process.Kill(); $process.WaitForExit() }
    }
}
