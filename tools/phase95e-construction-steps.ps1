# Additional application-callback coverage. Every run starts from the same isolated save.
# No OS input is injected; native right-click and monitor DPI remain manual checks.
'setting gui.station_dragdrop true'
'setting gui.persistent_buildingtools true'
'renderer_3d labeloptions 0 127'
'scrollto instant 42 42'
'zoomto 1'
foreach ($yaw in @(0,45,90,135,180,225,270,315)) {
    "renderer_3d camera $yaw 100"
    "renderer_3d managestate base$yaw 42 42"
    foreach ($road in @('roadx','roady')) {
        $coords = if ($road -eq 'roadx') { '40 41 44 41' } else { '42 40 42 44' }
        $target = if ($road -eq 'roadx') { '42 41' } else { '42 42' }
        "renderer_3d managetool $road preview $coords"
        "renderer_3d managestate $road-preview$yaw $target"
        "renderer_3d managecheck $road-preview$yaw"
        "screenshot $road-preview$yaw"
        "renderer_3d managetool $road escape $coords"
        "renderer_3d managestate $road-escape$yaw $target"
        "renderer_3d managetool $road build $coords"
        "renderer_3d managestate $road-built$yaw $target"
        "screenshot $road-built$yaw"
        "renderer_3d managetool $road remove $coords"
        "renderer_3d managestate $road-removed$yaw $target"
    }
    foreach ($depot in @('raildepot','roaddepot')) {
        "renderer_3d managetool $depot build 42 42 42 42"
        "renderer_3d managestate $depot-built$yaw 42 42"
        "screenshot $depot-built$yaw"
        # An incompatible depot must fail without replacing the existing one.
        $other = if ($depot -eq 'raildepot') { 'roaddepot' } else { 'raildepot' }
        "renderer_3d managetool $other build 42 42 42 42"
        "renderer_3d managestate $depot-invalid$yaw 42 42"
        'renderer_3d managetool demolish build 42 42 42 42'
        "renderer_3d managestate $depot-removed$yaw 42 42"
    }
    'renderer_3d managetool station build 40 41 44 41'
    "renderer_3d managestate station-built$yaw 42 41"
    "screenshot station-built$yaw"
    'renderer_3d managetool demolish build 40 41 44 41'
    "renderer_3d managestate station-removed$yaw 42 41"
    'renderer_3d managedrag build 40 41 44 41'
    'renderer_3d previewclear'
    'renderer_3d managetool signal build 42 41 42 41'
    "renderer_3d managestate signal-built$yaw 42 41"
    "screenshot signal-built$yaw"
    'renderer_3d managetool signal remove 42 41 42 41'
    "renderer_3d managestate signal-removed$yaw 42 41"
    'renderer_3d managetool demolish build 40 41 44 41'
    'renderer_3d managetool bridge build 40 41 44 41'
    "renderer_3d managestate bridge-built$yaw 40 41"
    "renderer_3d managestate bridge-other$yaw 44 41"
    "screenshot bridge-built$yaw"
    'renderer_3d managetool demolish build 40 41 40 41'
    "renderer_3d managestate bridge-removed$yaw 40 41"
    # A flat tile has no tunnel slope: the command should leave it unchanged.
    'renderer_3d managetool tunnel build 42 42 42 42'
    "renderer_3d managestate tunnel-invalid$yaw 42 42"
    # An unused row through the fixture's existing hill has real entrance slopes.
    'scrollto instant 34 36'
    'renderer_3d managetool tunnel build 32 36 32 36'
    "renderer_3d managestate tunnel-built$yaw 32 36"
    "renderer_3d managestate tunnel-other$yaw 37 36"
    "screenshot tunnel-built$yaw"
    'renderer_3d managetool demolish build 32 36 32 36'
    "renderer_3d managestate tunnel-removed$yaw 32 36"
    'scrollto instant 42 42'
    'renderer_3d managetool raise build 42 42 42 42'
    "renderer_3d managestate raised$yaw 42 42"
    "renderer_3d managecheck raised$yaw"
    "screenshot raised$yaw"
    'renderer_3d managetool lower build 42 42 42 42'
    "renderer_3d managestate lowered$yaw 42 42"
    'renderer_3d managetool raise build 42 42 42 42'
    'renderer_3d managetool level build 40 40 44 44'
    "renderer_3d managestate levelled$yaw 42 42"
    'renderer_3d previewclear'
    'renderer_3d managezoom 42 42'
}
# Explicit road preview/reset cancellation, separately from the Escape key handler.
'renderer_3d managetool roadx cancel 40 41 44 41'
'renderer_3d managestate road-cancel 42 41'
'renderer_3d previewclear'
