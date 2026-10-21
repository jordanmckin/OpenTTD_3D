"""Verify map state after real GUI construction callbacks; no native-input claim."""
import json
import re
import sys
from pathlib import Path
from PIL import Image

run = Path(sys.argv[1])
log = '\n'.join((run / name).read_text(errors='replace') for name in ('stdout.log', 'stderr.log'))
assert not re.search(r'Assertion failed|3D proof failed|3D proof OpenGL error|command not found|ERROR:', log, re.I), 'runtime error'
records = {}
for kind, fields in re.findall(r'PHASE95E (STATE|TOOL|GROUND|ZOOM|DRAG) (.*)', log):
    records.setdefault(kind, []).append(dict(re.findall(r'(\w+)=([^ ]+)', fields)))
assert records.get('STATE') and records.get('TOOL'), 'missing diagnostics'
scheduled = (run / 'scripts/game_start.scr').read_text()
expected_tools = re.findall(r'renderer_3d managetool (\w+) (\w+)', scheduled)
assert [(r['tool'], r['mode']) for r in records['TOOL']] == expected_tools, 'tool callback sequence missing or duplicated'
for row in records['TOOL'] + records.get('ZOOM', []) + records.get('DRAG', []):
    assert row['ok'] == 'true', row
for row in records.get('GROUND', []):
    assert row['failures'] == '0' and int(row['checks']) > 0, row
for yaw in (0,45,90,135,180,225,270,315):
    for tag in (f'roadx-preview{yaw}', f'roady-preview{yaw}', f'raised{yaw}'):
        rows = [r for r in records.get('GROUND', []) if r['tag'] == tag]
        assert rows and all(float(r['yaw']) == yaw and r['tool'] != '0' for r in rows), ('camera or tool lost', tag, rows)
for row in records['TOOL']:
    if row['mode'] in ('escape', 'cancel'):
        assert row['active'] == '0', row
states = {r['tag']: r for r in records['STATE']}
assert len(states) == len(records['STATE']), 'duplicate state tags'
def state(tag, **expected):
    assert tag in states, ('missing state', tag)
    row = states[tag]
    for key, value in expected.items():
        assert row[key] == str(value).lower(), (tag, key, value, row)
    return row
def empty(tag):
    return state(tag, type=0, rail=0, road=0, raildepot=False, roaddepot=False,
                 station=False, signal=False, bridge=False, tunnel=False)
def unbuilt(tag):
    row = state(tag, rail=0, road=0, raildepot=False, roaddepot=False,
                station=False, signal=False, bridge=False, tunnel=False)
    assert row['type'] in ('0', '4'), ('expected clear land or fixture trees', row)
    return row
captures = []
for yaw in (0,45,90,135,180,225,270,315):
    base = unbuilt(f'base{yaw}')
    for road, bits in (('roadx', 10), ('roady', 5)):
        preview = unbuilt(f'{road}-preview{yaw}')
        state(f'{road}-escape{yaw}', active=0)
        cancelled = unbuilt(f'{road}-escape{yaw}')
        assert {k:v for k,v in preview.items() if k not in ('tag','active')} == {k:v for k,v in cancelled.items() if k not in ('tag','active')}, ('Escape changed tile', preview, cancelled)
        state(f'{road}-built{yaw}', road=bits)
        empty(f'{road}-removed{yaw}')
        captures += [f'{road}-preview{yaw}', f'{road}-built{yaw}']
    for depot in ('raildepot', 'roaddepot'):
        built = state(f'{depot}-built{yaw}', **{depot: True})
        rejected = state(f'{depot}-invalid{yaw}')
        assert {k:v for k,v in built.items() if k not in ('tag','active')} == {k:v for k,v in rejected.items() if k not in ('tag','active')}, ('invalid placement changed tile', built, rejected)
        empty(f'{depot}-removed{yaw}')
        captures += [f'{depot}-built{yaw}']
    state(f'station-built{yaw}', station=True)
    empty(f'station-removed{yaw}')
    state(f'signal-built{yaw}', signal=True, rail=1)
    state(f'signal-removed{yaw}', signal=False, rail=1)
    state(f'bridge-built{yaw}', bridge=True, other='44,41')
    state(f'bridge-other{yaw}', bridge=True, other='40,41')
    empty(f'bridge-removed{yaw}')
    empty(f'tunnel-invalid{yaw}')
    state(f'tunnel-built{yaw}', tunnel=True, other='37,36')
    state(f'tunnel-other{yaw}', tunnel=True, other='32,36')
    state(f'tunnel-removed{yaw}', tunnel=False)
    state(f'raised{yaw}', height=int(base['height']) + 1)
    state(f'lowered{yaw}', height=base['height'])
    state(f'levelled{yaw}', height=base['height'])
    captures += [f'station-built{yaw}', f'signal-built{yaw}', f'bridge-built{yaw}', f'tunnel-built{yaw}', f'raised{yaw}']
empty('road-cancel')
state('road-cancel', active=0)
assert len(records.get('ZOOM', [])) == 16, 'cursor zoom at each yaw'
for name in captures:
    paths = list((run / 'screenshot').glob(name + '.*'))
    assert len(paths) == 1, ('missing capture', name)
    with Image.open(paths[0]) as im:
        assert im.width >= 800 and im.height >= 600, (name, im.size)
gpu = re.findall(r'PHASE7 gpu-reference valid=(\w+) differing=(\d+) pixels=(\d+)', log)
if json.loads((run / 'environment.json').read_text(encoding='utf-8-sig'))['verify_gpu']:
    assert gpu and all(valid == 'true' and int(different) / int(pixels) <= .0005 for valid,different,pixels in gpu), ('GPU reference', gpu)
result = dict(passed=True, states=len(states), tool_callbacks=len(records['TOOL']),
              ground_checks=sum(int(r['checks']) for r in records.get('GROUND', [])),
              ground_failures=0, cursor_zoom_checks=len(records['ZOOM']), captures=len(captures),
              gpu_references=len(gpu), native_input=False, records=records)
(run / 'check-results.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({k:v for k,v in result.items() if k != 'records'}, indent=2))
