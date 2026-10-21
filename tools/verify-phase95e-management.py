"""Verify rotated picking, original UI callbacks and authoritative results; no native-input claim."""
import json
import re
import sys
from pathlib import Path
from PIL import Image

run = Path(sys.argv[1])
log = (run / 'stdout.log').read_text(errors='replace') + (run / 'stderr.log').read_text(errors='replace')
assert not re.search(r'Assertion failed|3D proof failed|3D proof OpenGL error|command not found|ERROR:', log, re.I), 'runtime error'
records = {}
for line in log.splitlines():
    m = re.search(r'PHASE95E (GROUND|MANAGEMENT|VEHICLE|DRAG|RESULT|ZOOM) (.*)', line)
    if m:
        records.setdefault(m[1], []).append(dict(re.findall(r'(\w+)=([^ ]+)', m[2])))
assert records.get('GROUND'), 'no picking diagnostics'
for row in records['GROUND'] + records['MANAGEMENT']:
    assert row['failures'] == '0', row
for row in records.get('VEHICLE', []) + records.get('DRAG', []) + records.get('RESULT', []) + records.get('ZOOM', []):
    assert row['ok'] == 'true', row
for yaw in (0, 45, 90, 135, 180, 225, 270, 315):
    rows = [r for r in records['GROUND'] if r['tag'] == f'angle{yaw}']
    assert rows and sum(int(r['checks']) for r in rows) >= 20, yaw
for yaw in (45, 90, 135, 180, 225, 270):
    rows = [r for r in records['GROUND'] if r['tag'] == f'preview{yaw}']
    assert rows and all(float(r['yaw']) == yaw and r['tool'] != '0' for r in rows), ('camera or tool lost', rows)
    assert any(r['tag'] == f'build{yaw}' for r in records['RESULT']), yaw
    assert any(r['tag'] == f'remove{yaw}' for r in records['RESULT']), yaw
assert {int(r['actual']) for r in records['RESULT'] if r['tag'].startswith('build')} >= {1,2,4,8,16,32}, 'missing rail orientations'
assert any(r['mode']=='diagonal' and r['diagonal']=='true' for r in records['DRAG']), 'diagonal selection not exercised'
assert len(records.get('ZOOM', [])) == 2, 'missing cursor zoom'
for tag,yaw in (('orbit-tool',315),('home-tool',0),('restored-tool',315)):
    rows=[r for r in records['GROUND'] if r['tag']==tag]
    assert rows and all(float(r['yaw'])==yaw and r['tool']!='0' for r in rows), ('orbit cancelled tool', rows)
assert any(r['mode']=='preview' and r['tooltip']=='true' for r in records['DRAG']), 'measurement tooltip missing'
assert any(r['tag'] == 'cancelled' and r['tool'] == '0' for r in records['GROUND']), 'cancel failed'
assert sum(int(r['clicks']) for r in records['MANAGEMENT']) > 0, 'no actual vehicle-window actions'
for tag, camera in (('cab', '1'), ('chase', '2')):
    rows = [r for r in records['GROUND'] if r['tag'] == tag and r['camera'] == camera]
    assert len(rows) >= 2 and all(r['checks'] == '9' for r in rows), ('perspective targets', tag)
assert len([r for r in records['GROUND'] if r['tag'] == 'secondary']) >= 4, 'missing viewports'
assert any(r['tag'] == 'edge' and int(r['checks']) > 0 for r in records['GROUND'])
labels = re.findall(r'PHASE95B CLICK .*ok=(\w+)', log)
assert labels and all(x == 'true' for x in labels), 'label actions'
assert not re.search(r'PHASE95B VIEW .*failures=[1-9]', log), 'label failures'
expected = [f'angle{yaw}' for yaw in (0, 45, 90, 135, 180, 225, 270, 315)] + [f'{stage}{yaw}' for stage in ('preview', 'build') for yaw in (45, 90, 135, 180, 225, 270)] + ['secondary', 'cab', 'chase', 'resized', 'edge', 'returned', 'classic2d', 'orbit-tool', 'home-tool', 'area', 'diagonal']
pictures = {p.stem: p for p in (run / 'screenshot').glob('*')}
assert all(n in pictures for n in expected), ('missing captures', sorted(set(expected) - pictures.keys()))
for name in expected:
    im = Image.open(pictures[name])
    assert im.width >= 800 and im.height >= 600, (name, im.size)
# The preview must actually draw, and clearing it after construction must remove its gold tint.
# Ignore toolbar/status pixels; use the same saved scene and angle for each pair.
def gold_pixels(name):
    im = Image.open(pictures[name]).convert('RGB')
    return sum(r > 180 and 140 < g < 245 and b < 100 and r > g for r,g,b in im.crop((0, 120, im.width, im.height-50)).getdata())
for yaw in (45,90,135,180,225,270):
    assert gold_pixels(f'preview{yaw}') > gold_pixels(f'build{yaw}') + 40, ('preview raster missing',yaw)
assert gold_pixels('area') > 100, 'area raster missing'
assert gold_pixels('diagonal') > 100, 'diagonal raster missing'
gpu = re.findall(r'PHASE7 gpu-reference valid=(\w+) differing=(\d+) pixels=(\d+)', log)
if json.loads((run / 'environment.json').read_text(encoding='utf-8-sig'))['verify_gpu']:
    assert gpu and all(valid == 'true' and int(different) / int(pixels) <= .0005 for valid,different,pixels in gpu), ('GPU reference', gpu)
result = dict(passed=True, ground_checks=sum(int(r['checks']) for r in records['GROUND']), ground_failures=0,
              slope_checks=sum(int(r['slopes']) for r in records['GROUND']), foundation_checks=sum(int(r['foundations']) for r in records['GROUND']),
              bridge_checks=sum(int(r['bridges']) for r in records['GROUND']), vehicle_clicks=sum(int(r['clicks']) for r in records['MANAGEMENT']),
              label_clicks=len(labels), drag_callbacks=len(records['DRAG']), command_results=len(records['RESULT']), captures=len(expected), gpu_references=len(gpu), records=records)
(run / 'check-results.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({k: v for k,v in result.items() if k != 'records'}, indent=2))
