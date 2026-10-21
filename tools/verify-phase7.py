"""Summarize actual draw passes (CPU wall times) and, where logged, presented frame times.

PHASE7 present lines time each completed draw tick end to end; interval_us is the time
between presented frames, so 1e6/mean interval is the measured frame rate of the run.
"""
import sys
import json
import csv
import re
from pathlib import Path
from statistics import mean

root = Path(__file__).resolve().parents[1]
tag = sys.argv[1] if len(sys.argv) > 1 else "phase7"
rows = []
samples = []
for folder in sorted((root / '.runtime').glob(f'{tag}-*-*-*')):
    log = (folder / 'stderr.log').read_text(errors='replace')
    assert not re.search(r'3D proof failed|3D proof OpenGL error|Assertion failed|Your script made an error|Fixture failed', log), folder
    if folder.name.endswith('-stress'):
        assert 'PHASE7 STRESS_READY clones=200' in log, folder
        log = log.split('PHASE7 STRESS_READY clones=200', 1)[1]
    if '-fleet' in folder.name:
        assert 'PHASE7 FLEET_RELOADED' in log, folder
        log = log.split('PHASE7 FLEET_RELOADED', 1)[1]
    assert not re.search(r'dirty-reference missed_chunks=[1-9]', log), folder
    presents = [dict((k, int(v)) for k, v in re.findall(r'(\w+)=(\d+)', line))
                for line in log.splitlines() if 'PHASE7 present' in line][20:]
    frames = []
    streams = {}
    for line in log.splitlines():
        if 'PHASE7 streams' in line:
            streams = dict((k, int(v)) for k, v in re.findall(r'(\w+)=(\d+)', line))
        elif 'PHASE7 frame' in line:
            frames.append(dict(streams, **dict((k, int(v)) for k, v in re.findall(r'(\w+)=(\d+)', line))))
    first_frame = frames[0] if frames else {}
    frames = frames[5:]  # exclude initialization; retain slow large-map samples
    assert len(frames) >= 15, (folder, len(frames))
    # Offscreen deferral is only observable when part of the map is outside every view.
    whole_map_visible = re.search(r'-\d+x\d+$', folder.name) and folder.name.split('-')[1] == '6'
    if '-optimized' in folder.name and any('pending_chunks' in f for f in frames) and not whole_map_visible:
        assert max(f['pending_chunks'] for f in frames) > 0, folder
    if '-optimized' in folder.name and folder.name.endswith('-pan'):
        keys = re.findall(r'PHASE7 view width=\d+ height=\d+ left=(-?\d+) top=(-?\d+) zoom=(\d+)', log)
        transitions = [key for i, key in enumerate(keys) if i == 0 or key != keys[i-1]]
        assert len(set(keys)) >= 16 and len(transitions) >= 18, (folder,len(set(keys)),len(transitions))
        assert sum(f.get('evictions', 0) for f in frames) > 0, 'Pan must exercise actual eviction'
        assert sum(f.get('cold_chunks', 0) for f in frames) > 0, 'Pan must regenerate cold geometry'
    if any('tiles_rebuilt' in f for f in frames):
        assert all('tiles_rebuilt' in f and 'tiles_reused' in f for f in frames), folder
        assert sum(f['tiles_rebuilt'] for f in frames) > 0, folder
        if '-chunked' in folder.name:
            assert sum(f['tiles_reused'] for f in frames) == 0, folder
        elif '-optimized' in folder.name or '-tilecached' in folder.name or '-eager' in folder.name:
            assert sum(f['tiles_reused'] for f in frames) > 0, folder
    if any('tiles_scan_candidates' in f for f in frames):
        assert all(f['tiles_scanned'] <= f['tiles_scan_candidates'] for f in frames), folder
        scanned = sum(f['tiles_scanned'] for f in frames)
        candidates = sum(f['tiles_scan_candidates'] for f in frames)
        if '-tilecached' in folder.name:
            assert scanned == candidates and candidates > 0, folder
        elif '-optimized' in folder.name or '-eager' in folder.name:
            assert 0 < scanned < candidates, folder
    if any('vehicle_instances' in f for f in frames):
        assert all(f['vehicle_draws'] <= f['vehicle_instances'] for f in frames), folder
        assert all(0 <= f['instance_upload_bytes'] <= 64 * (f['vehicle_instances'] + f.get('static_instances', 0)) for f in frames), folder
        if ' instanced=true' in log:
            assert all(f['instance_upload_bytes'] >= 64 * f['vehicle_instances'] for f in frames), folder
            if '-streamed' in folder.name:
                assert all(f['instance_upload_bytes'] == 64 * (f['vehicle_instances'] + f.get('static_instances', 0)) for f in frames), folder
        assert all(f.get('static_draws', 0) <= f.get('static_instances', 0) for f in frames), folder
        if '-uninstanced' in folder.name:
            assert all(f['vehicle_draws'] == f['vehicle_instances'] and f.get('static_draws', 0) == f.get('static_instances', 0) and f['instance_upload_bytes'] == 0 for f in frames), folder
    if any('static_instances' in f for f in frames):
        if '-baked' in folder.name:
            assert ' static_shared=false' in log and 'optimized=true' in log, folder
            assert all(f['static_instances'] == 0 and f['static_draws'] == 0 for f in frames), folder
        elif '-optimized' in folder.name:
            assert ' static_shared=true' in log, folder
            assert sum(f['static_instances'] for f in frames) > 0, folder
    if any('stream_retained_bytes' in f for f in frames):
        assert all(f['stream_retained_bytes'] <= 32 * 1024**2 and f['stream_entries'] <= 16 for f in frames), folder
        if '-streamed' in folder.name:
            assert all(f['stream_retained_bytes'] == 0 for f in frames), folder
            assert 'streams_enabled=false' in log, folder
        elif '-optimized' in folder.name:
            assert sum(f['stream_hits'] + f['stream_patches'] for f in frames) > 0, folder
    if any('model_triangles' in f for f in frames):
        assert all(f['model_triangles'] <= f['full_model_triangles'] for f in frames), folder
        if '-lod-' in folder.name or folder.name.endswith('-lod'):
            assert sum(f['lod_instances'] for f in frames) > 0, 'LOD case must exercise reduced models'
        else:
            assert all(f['lod_instances'] == 0 and f['model_triangles'] == f['full_model_triangles'] for f in frames), folder
    samples.extend(dict(case=folder.name, **f) for f in frames)
    values = sorted(f['draw_us'] for f in frames)
    cold = [f for f in frames if f.get('cold_chunks', 0) > 0]
    row = dict(case=folder.name, samples=len(frames),
               first_draw_ms=round(first_frame.get('draw_us', 0)/1000, 3),
               mean_draw_ms=round(mean(values)/1000, 3),
               p95_draw_ms=round(values[int((len(values)-1)*.95)]/1000, 3),
               mean_scan_ms=round(mean(f['scan_us'] for f in frames)/1000, 3),
               mean_render_ms=round(mean(f['render_us'] for f in frames)/1000, 3),
               mean_read_ms=round(mean(f['read_us'] for f in frames)/1000, 3),
               mean_gpu_ms=round(mean(f.get('gpu_ns', 0) for f in frames)/1e6, 3),
               mean_projection_ms=round(mean(f.get('projection_us', 0) for f in frames)/1000, 3),
               mean_upload_ms=round(mean(f.get('upload_us', 0) for f in frames)/1000, 3),
               mean_static_upload_kib=round(mean(f.get('static_upload_bytes', 0) for f in frames)/1024, 3),
               mean_tiles_scanned=round(mean(f.get('tiles_scanned', 0) for f in frames), 1),
               mean_tiles_scan_candidates=round(mean(f.get('tiles_scan_candidates', 0) for f in frames), 1),
               mean_tiles_rebuilt=round(mean(f.get('tiles_rebuilt', 0) for f in frames), 1),
               mean_tiles_reused=round(mean(f.get('tiles_reused', 0) for f in frames), 1),
               mean_mesh_ms=round(mean(f.get('mesh_us', 0) for f in frames)/1000, 3),
               mean_chunks_rebuilt=round(mean(f.get('chunks_rebuilt', 0) for f in frames), 1),
               pending_chunks=max(f.get('pending_chunks', 0) for f in frames),
               resident_chunks=max(f.get('resident_chunks', 0) for f in frames),
               cpu_mesh_mib=round(max(f.get('cpu_mesh_bytes', 0) for f in frames)/2**20, 3),
               combined_mesh_mib=round(max(f.get('cpu_mesh_bytes', 0)+f.get('retained_bytes', 0) for f in frames)/2**20, 3),
               evictions=sum(f.get('evictions', 0) for f in frames),
               cold_frames=len(cold),
               cold_frame_max_ms=round(max((f['draw_us'] for f in cold), default=0)/1000, 3),
               cold_frame_mean_ms=round(mean(f['draw_us'] for f in cold)/1000, 3) if cold else 0,
               mean_prepare_ms=round(mean(f.get('prepare_us', 0) for f in frames)/1000, 3),
               mean_upload_kib=round(mean(f.get('upload_bytes', 0) for f in frames)/1024, 3),
               retained_mib=round(max(f.get('retained_bytes', 0) for f in frames)/2**20, 3),
               mean_draw_calls=round(mean(f['draws'] for f in frames), 2),
               mean_renders=round(mean(f['renders'] for f in frames), 2),
               mean_static_draws=round(mean(f.get('static_draws', 0) for f in frames), 2),
               mean_static_instances=round(mean(f.get('static_instances', 0) for f in frames), 2),
               static_sharing_active=' static_shared=true' in log,
               mean_vehicle_draws=round(mean(f.get('vehicle_draws', 0) for f in frames), 2),
               mean_vehicle_instances=round(mean(f.get('vehicle_instances', 0) for f in frames), 2),
               mean_instance_upload_kib=round(mean(f.get('instance_upload_bytes', 0) for f in frames)/1024, 3),
               mean_static_group_ms=round(mean(f.get('static_group_us', 0) for f in frames)/1000, 3),
               mean_instance_stream_ms=round(mean(f.get('instance_stream_us', 0) for f in frames)/1000, 3),
               stream_hits=sum(f.get('stream_hits', 0) for f in frames),
               stream_patches=sum(f.get('stream_patches', 0) for f in frames),
               stream_builds=sum(f.get('stream_builds', 0) for f in frames),
               stream_evictions=sum(f.get('stream_evictions', 0) for f in frames),
               stream_retained_mib=round(max(f.get('stream_retained_bytes', 0) for f in frames)/2**20, 3),
               mean_model_triangles=round(mean(f.get('model_triangles', 0) for f in frames), 1),
               mean_full_model_triangles=round(mean(f.get('full_model_triangles', 0) for f in frames), 1),
               model_library_mib=round(max(f.get('model_library_bytes', 0) for f in frames)/2**20, 3),
               mean_lod_instances=round(mean(f.get('lod_instances', 0) for f in frames), 2),
               instancing_active=' instanced=true' in log,
               mean_layer_refreshes=round(mean(f.get('layer_refreshes', 0) for f in frames), 2),
               mean_scoped_boxes=round(mean(f.get('scoped_boxes', 0) for f in frames), 1),
               mean_scoped_drops=round(mean(f.get('scoped_drops', 0) for f in frames), 2),
               mean_scoped_kept=round(mean(f.get('scoped_kept', 0) for f in frames), 2),
               working_set_mib=round(int((folder/'working-set-bytes.txt').read_text())/2**20, 1))
    if presents:
        intervals = sorted(f['interval_us'] for f in presents if f['interval_us'] > 0)
        works = sorted(f['work_us'] for f in presents)
        row.update(presented_frames=len(presents),
                   fps=round(1e6/mean(intervals), 2),
                   mean_frame_ms=round(mean(intervals)/1000, 3),
                   p50_frame_ms=round(intervals[len(intervals)//2]/1000, 3),
                   p95_frame_ms=round(intervals[int((len(intervals)-1)*.95)]/1000, 3),
                   p99_frame_ms=round(intervals[int((len(intervals)-1)*.99)]/1000, 3),
                   mean_work_ms=round(mean(works)/1000, 3),
                   over_10ms_work=round(sum(1 for w in works if w > 10000)/len(works), 3),
                   mean_paint_ms=round(mean(f['paint_us'] for f in presents)/1000, 3),
                   frames_with_3d_draw=round(sum(1 for f in presents if f['draws'] > 0)/len(presents), 3),
                   frames_with_3d_render=round(sum(1 for f in presents if f.get('renders', 0) > 0)/len(presents), 3),
                   game_ms_per_frame=round(mean(f['game_us'] for f in presents)/1000, 3),
                   game_ticks_per_s=round(sum(f['game_ticks'] for f in presents)/(sum(intervals)/1e6), 2))
    rows.append(row)
assert rows, f'No benchmark cases found for {tag}'
print(json.dumps(rows, indent=2))
(root / f'.runtime/{tag}-results.json').write_text(json.dumps(rows, indent=2)+'\n')
with (root / f'.runtime/{tag}-samples.csv').open('w', newline='') as stream:
    writer = csv.DictWriter(stream, fieldnames=sorted({key for sample in samples for key in sample}))
    writer.writeheader()
    writer.writerows(samples)
