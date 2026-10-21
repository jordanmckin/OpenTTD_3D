param([ValidateSet('Railway','Air')][string]$Save = 'Railway', [string]$RunTag = 'phase9-exits', [switch]$DryRun)
# Phase 9.5: exits and edge cases of cab and chase views.
# Railway loads the Phase 4 save, whose fixture AI also builds a dead-end road where trucks turn round and one overtakes
# another (fixtures/phase9/edges). It rides the train and trucks through tunnels, reverses the train, turns a truck,
# sends one to its depot and sells it, and crashes one that an extra viewport also chases.
# Air generates the Phase 8.6 map in 2005, where the fixture AI (fixtures/phase9/air) builds airports, planes and
# helicopters; it rides them through take-off, climbing, holding, landing and into a hangar.
# Event screenshots are taken by `renderer_3d onride` as each case happens.
$ErrorActionPreference = 'Stop'
$workspace = Split-Path -Parent $PSScriptRoot
$build = Join-Path $workspace 'build/baseline'
$fixture = Join-Path $workspace 'OpenTTD-15.3/OpenTTD-15.3/docs/3d/fixtures'
$RunTag += "-$($Save.ToLower())"
$run = Join-Path $workspace ".runtime/$RunTag"
$exe = Join-Path $build "$RunTag-console.exe"
Copy-Item "$build/Release/openttd.exe" $exe
& 'C:/Program Files (x86)/Microsoft Visual Studio/2022/BuildTools/VC/Tools/MSVC/14.44.35207/bin/Hostx64/x64/editbin.exe' /nologo /subsystem:console $exe
if ($LASTEXITCODE -ne 0) { throw 'editbin failed' }
# Emptied rather than removed: a shell left inside one keeps the folder itself busy.
foreach ($old in @("$run/screenshot", "$run/save", "$run/scripts", "$run/ai")) { if (Test-Path $old) { Get-ChildItem -Force $old | Remove-Item -Recurse -Force } }
New-Item -ItemType Directory -Force "$run/baseset","$run/lang","$run/scripts" | Out-Null
Copy-Item "$build/baseset/*" "$run/baseset"
Copy-Item "$build/lang/*.lng" "$run/lang"
Copy-Item "$workspace/.runtime/baseline/baseset/*.tar" "$run/baseset"
$railway = $Save -eq 'Railway'
$config = Get-Content -Raw "$fixture/phase6/coverage.cfg"
if ($railway) {
    # The Phase 4 fixture AI, which on reload also builds the Phase 9.5 dead-end road.
    New-Item -ItemType Directory -Force "$run/ai/infrastructure3d" | Out-Null
    Copy-Item "$fixture/phase4/ai/*.nut" "$run/ai/infrastructure3d"
    Copy-Item "$fixture/phase9/edges/ai/edges.nut" "$run/ai/infrastructure3d"
    $main = Get-Content -Raw "$run/ai/infrastructure3d/main.nut"
    $reload = 'print("PHASE4 RELOADED train=" + train_id);  Monitor();'
    if (!$main.Contains($reload)) { throw 'Phase 4 fixture AI reload line not found' }
    ('require("edges.nut");' + "`n" + $main.Replace($reload, 'print("PHASE4 RELOADED train=" + train_id); Phase95Edges(this); Monitor();')) | Set-Content -Encoding ascii "$run/ai/infrastructure3d/main.nut"
    $config | Set-Content -Encoding ascii "$run/openttd.cfg"
} else {
    # The Phase 8.6 farm map, generated in 2005 with every airport type available and a permissive council.
    New-Item -ItemType Directory -Force "$run/ai/air3d" | Out-Null
    Copy-Item "$fixture/phase9/air/ai/*.nut" "$run/ai/air3d"
    $config = $config.Replace('map_x = 6','map_x = 7').Replace('map_y = 6','map_y = 7')
    $config = $config.Replace('starting_year = 1950','starting_year = 2005').Replace('[economy]',"[station]`nnever_expire_airports = true`n[economy]")
    $config = $config.Replace('disasters = false',"disasters = false`ntown_council_tolerance = 3")
    $config.Replace('number_towns = 1','number_towns = 4').Replace('industry_density = 0','industry_density = 3') | Set-Content -Encoding ascii "$run/openttd.cfg"
}
# Each step runs at the start of a month. The events install as soon as the first onride is registered.
if ($railway) {
    $train = 3; $tunnel_truck = 0; $chase_truck = 1; $turn_truck = 2; $front = 12; $behind = 15
    $start = @"
renderer_3d on
renderer_3d verifygpu on
setting gui.show_finances false
scrollto instant 29 33
zoomto 2
unpause
schedule on-next-calendar-month scripts/step0.scr
"@
    $fade = @()
    foreach ($v in @($train, $tunnel_truck, $chase_truck)) {
        foreach ($e in @('entering', 'black', 'leaving', 'clear')) { $fade += "renderer_3d onride $v $e screenshot p95-tunnel-$v-$e" }
    }
    $steps = @(
        # Ride through the tunnels and along the dead-end road, where the trucks turn round and, later, one overtakes.
        ((@("renderer_3d view $train cab", "renderer_3d view $tunnel_truck cab", "renderer_3d view $chase_truck chase", "renderer_3d view $front cab", "renderer_3d view $behind cab",
            "renderer_3d chaselog on") + $fade + @("renderer_3d onride $front turning renderer_3d after 20 screenshot p95-turning-end", "renderer_3d onride $behind overtaking screenshot p95-overtaking",
            "renderer_3d onride $behind overtaking renderer_3d after 40 screenshot p95-overtaking-passing")) -join "`n"),
        # The train reverses, a truck turns round on the road.
        ("renderer_3d views`nscreenshot p95-reverse-before`nrenderer_3d queued ride $train reverse`nrenderer_3d after 8 screenshot p95-reverse-after`n" +
         "renderer_3d view $turn_truck cab`nrenderer_3d onride $turn_truck turning screenshot p95-turn-start`nrenderer_3d onride $turn_truck turning renderer_3d after 30 screenshot p95-turn-end`nrenderer_3d after 60 renderer_3d ride $turn_truck turn"),
        # Exits: a truck into its depot, another crashed while an extra viewport also chases it.
        ("renderer_3d view $tunnel_truck cab`nrenderer_3d onride $tunnel_truck snapback screenshot p95-depot-snapback`nrenderer_3d ride $tunnel_truck depot`n" +
         "renderer_3d view $chase_truck chase`nrenderer_3d ride $chase_truck extra`nrenderer_3d after 60 screenshot p95-crash-before`nrenderer_3d after 60 renderer_3d queued ride $chase_truck crash`nrenderer_3d onride $chase_truck snapback renderer_3d after 2 screenshot p95-crash-snapback`nrenderer_3d after 120 renderer_3d views"),
        # Sold from the depot; the crashed truck is cleared away during the month.
        "renderer_3d views`nrenderer_3d ride $tunnel_truck sell`nrenderer_3d after 2 renderer_3d views",
        "renderer_3d views`nrenderer_3d after 2 quit"
    )
} else {
    $start = @"
renderer_3d on
renderer_3d verifygpu on
setting gui.show_finances false
setting gui.fast_forward_speed_limit 2000
renderer_3d fastforward on
start_ai Air3DFixture
unpause
schedule on-next-calendar-month scripts/wait.scr
"@
    "renderer_3d fastforward off`nschedule on-next-calendar-month scripts/step0.scr" | Set-Content -Encoding ascii "$run/scripts/wait.scr"
    $plane = 2; $plane_chase = 4; $heli = 8; $heli_chase = 11
    $events = @()
    foreach ($e in @('takeoff', 'landing')) { $events += "renderer_3d onride $plane $e screenshot p95-air-plane-$e", "renderer_3d onride $plane $e renderer_3d after 90 screenshot p95-air-plane-$e-later" }
    foreach ($e in @('helitakeoff', 'helilanding')) { $events += "renderer_3d onride $heli $e screenshot p95-air-heli-$e", "renderer_3d onride $heli $e renderer_3d after 90 screenshot p95-air-heli-$e-later" }
    $events += "renderer_3d onride any holding screenshot p95-air-holding", "renderer_3d onride any holding renderer_3d after 120 screenshot p95-air-holding-later"
    $steps = @(
        # Ride with planes and helicopters through take-off, climbing, holding and landing.
        ((@("renderer_3d view $plane cab", "renderer_3d view $plane_chase chase", "renderer_3d view $heli cab", "renderer_3d view $heli_chase chase", "renderer_3d chaselog on") + $events) -join "`n"),
        # Into a hangar.
        "renderer_3d views`nrenderer_3d onride $plane snapback renderer_3d after 2 screenshot p95-air-hangar-snapback`nrenderer_3d ride $plane depot",
        "renderer_3d views`nrenderer_3d after 2 quit"
    )
}
if ($DryRun) { $steps = @("renderer_3d views`nrenderer_3d after 2 quit") }
$start | Set-Content -Encoding ascii "$run/scripts/game_start.scr"
for ($i=0; $i -lt $steps.Count; $i++) {
    $text = $steps[$i]
    if ($i+1 -lt $steps.Count) { $text += "`nschedule on-next-calendar-month scripts/step$($i+1).scr" }
    $text | Set-Content -Encoding ascii "$run/scripts/step$i.scr"
}
$arguments = '-c "{0}" -x -X -QQ -I OpenGFX -v win32-opengl -b 32bpp-optimized -s null -m null -d driver=1,script=3' -f "$run/openttd.cfg"
$arguments += if ($railway) { ' -g "{0}"' -f "$fixture/phase4/infrastructure.sav" } else { ' -g -G 20261016' }
$process = Start-Process $exe -ArgumentList $arguments -WorkingDirectory $build -WindowStyle Hidden -PassThru -RedirectStandardOutput "$run/stdout.log" -RedirectStandardError "$run/stderr.log"
$handle = $process.Handle
try {
    $deadline = (Get-Date).AddSeconds(1200)
    while (!$process.WaitForExit(1000)) { if ((Get-Date) -gt $deadline) { throw "Timed out: $run" } }
    if ($process.ExitCode -ne 0) { throw "Exit $($process.ExitCode): $run" }
} finally { if (!$process.HasExited) { $process.Kill(); $process.WaitForExit() } }
if ($DryRun) { Select-String -Path "$run/stderr.log","$run/stdout.log" -Pattern 'PHASE95 (TRUCK|AIRCRAFT|AIRPORT|FIXTURE)|PHASE4 (edges|RELOADED)|Fixture failed|made an error' | Select-Object -First 40; return }
python "$PSScriptRoot/verify-phase9-exits.py" $run $Save
if ($LASTEXITCODE -ne 0) { throw 'Phase 9.5 verification failed' }
