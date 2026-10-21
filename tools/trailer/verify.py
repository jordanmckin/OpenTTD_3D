"""Check actual traffic evidence and preservation of the supplied city save."""
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
build = ROOT / '.runtime/trailer-build20'
reload = ROOT / '.runtime/trailer-reload'
log = (build / 'stderr.log').read_text()
replay = (reload / 'stderr.log').read_text()
assert 'TRAILER BUILD_DONE vehicles=43' in log
assert 'TRAILER RELOADED vehicles=43' in replay
for text in [log, replay]:
    assert 'TRAILER FAIL' not in text
    assert 'Your script made an error' not in text
assert 'TRAILER BUILD_DONE' not in replay, 'Reload must resume, not rebuild the network.'

pattern = r'TRAILER VEHICLE id=(\d+) name=(.*?) xy=(\d+),(\d+) speed=(\d+) load=(\d+) profit=(-?\d+)'
vehicles = defaultdict(list)
for match in re.finditer(pattern, log + replay):
    vehicle, name, x, y, speed, load, profit = match.groups()
    vehicles[name].append(dict(id=int(vehicle), x=int(x), y=int(y), speed=int(speed), load=int(load), profit=int(profit)))

routes = {}
for label in ['Iron Freight', 'Coal Freight', 'Timber Freight', 'Coal Haulage', 'Timber Haulage', 'Ore Haulage', 'Steel Haulage', 'City Goods', 'Lewisworth Bus', 'Whitdon Bus']:
    samples = [sample for name, values in vehicles.items() if name.startswith(label) for sample in values]
    assert samples, label
    positions = {(s['x'], s['y']) for s in samples}
    assert len(positions) >= 3, f'{label}: insufficient movement'
    assert max(s['speed'] for s in samples) > 0, f'{label}: stationary'
    assert max(s['load'] for s in samples) > 0, f'{label}: never carried cargo'
    routes[label] = dict(positions=len(positions), max_load=max(s['load'] for s in samples), max_profit=max(s['profit'] for s in samples))

for label in ['Iron', 'Coal', 'Timber']:
    for n in range(1, 4):
        samples = vehicles[f'{label} Freight {n}']
        assert max(s['profit'] for s in samples) > 0

supplied = Path(r'C:\Users\8bits\Documents\OpenTTD\save\city_save.sav')
original_hash = hashlib.sha256(supplied.read_bytes()).hexdigest()
assert original_hash == hashlib.sha256((build / 'source.sav').read_bytes()).hexdigest()
assert (build / 'save/trailer-city.sav').stat().st_size > 0
assert (reload / 'save/trailer-city.sav').stat().st_size > 0
statuses = re.findall(r'TRAILER STATUS fleet=(\d+) moving=(\d+) loaded=(\d+) profit=(-?\d+)', log + replay)
assert all(int(row[0]) == 43 for row in statuses)
result = dict(fleet=dict(trains=9, trucks=18, buses=16), source_sha256=original_hash, source_unchanged=True,
              reload_resumed=True, max_simultaneously_moving=max(int(s[1]) for s in statuses),
              max_simultaneously_loaded=max(int(s[2]) for s in statuses), routes=routes)
output = ROOT / 'artifacts/trailer-city/verification.json'
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
