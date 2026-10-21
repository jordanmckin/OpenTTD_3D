"""Validate paused visibility comparisons and independent ground-picking fingerprints."""
import json
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image

for path in sys.argv[1:]:
    run = Path(path)
    log = (run / 'stderr.log').read_text(errors='replace')
    restart = (run / 'restart-stderr.log').read_text(errors='replace')
    assert re.search(r'PHASE95D tag=persisted-off .*enabled=false', restart), 'Disabled preference did not survive restart'
    assert re.search(r'PHASE95D tag=menu-on .*enabled=true', restart), 'Keyboard menu toggle failed'
    assert re.search(r'renderer_3d_auto_visibility\s*=\s*true', (run / 'openttd.cfg').read_text()), 'Menu preference did not save'
    assert not re.search(r'3D proof failed|OpenGL error|Assertion failed|Your script made an error|Fixture failed|shader.*error', log, re.I), run
    groups = {}
    for match in re.finditer(r'PHASE95D tag=(\S+)-(off|on|restored) view=(\S+) enabled=(\w+) kind=(\d+) target=(\S+) picks=(\d+) locks=(\d+) manual=(\d+) invisible=(\d+)', log):
        name, mode, view, enabled, kind, target, picks, locks, manual, invisible = match.groups()
        groups.setdefault(name, {}).setdefault(mode, {})[view] = dict(enabled=enabled, kind=int(kind), target=target, picks=picks, locks=locks, manual=manual, invisible=invisible)
    assert groups, run
    meta = json.loads((run / 'environment.json').read_text(encoding='utf-8-sig'))
    if meta['verify_gpu']:
        refs = re.findall(r'(?:gpu|instance|kept)-reference valid=(\w+) differing=(\d+) pixels=(\d+)', log)
        assert refs and all(valid == 'true' and int(different) / max(int(pixels), 1) < 0.005 for valid, different, pixels in refs), ('GPU reference mismatch', run)
    rows = []
    for name, modes in groups.items():
        assert set(modes) == {'off', 'on', 'restored'}, (name, modes)
        assert modes['off'].keys() == modes['on'].keys() == modes['restored'].keys(), name
        for view in modes['off']:
            before, active, after = [modes[m][view] for m in ('off', 'on', 'restored')]
            assert before == after, (name, view, before, after)
            assert before['enabled'] == 'false' and active['enabled'] == 'true', name
            for key in ('picks', 'locks', 'manual', 'invisible'):
                assert before[key] == active[key], (name, view, key)
        images = {mode: np.asarray(Image.open(next((run / 'screenshot').glob(f'{name}-{mode}.*'))).convert('RGB'), dtype=np.int16) for mode in modes}
        # UI cursor animation and the status-bar clock are outside the viewport acceptance crop.
        images = {mode: pixels[60:-40] for mode, pixels in images.items()}
        restored = np.max(np.abs(images['off'] - images['restored']), axis=2) > 2
        changed = np.max(np.abs(images['off'] - images['on']), axis=2) > 2
        assert restored.mean() < 0.0002, (name, 'restoration', float(restored.mean()))
        assert changed.mean() < 0.20, (name, 'unbounded change', float(changed.mean()))
        kinds = sorted(set(item['kind'] for item in modes['on'].values()))
        if kinds == [0]:
            assert changed.mean() < 0.0002, (name, 'no focus must leave normal presentation intact')
        if 1 in kinds or 2 in kinds:
            assert changed.sum() > 0, (name, 'focused tile or vehicle must have a visible outline')
        rows.append(dict(view=name, viewports=len(modes['on']), focus_kinds=kinds, changed_pixels=int(changed.sum()), restored_pixels=int(restored.sum())))
    assert sum(row['changed_pixels'] for row in rows) > 0, 'Effect never drew'
    by_name = {row['view']: row for row in rows}
    if 'town-locked' in by_name:
        locked = by_name['town-locked']['changed_pixels']
        unlocked = by_name['town-unlocked']['changed_pixels']
        assert locked < unlocked, 'Manual solid lock did not suppress obstruction fading'
        assert by_name['town-hidden']['changed_pixels'] <= locked + 4, 'Manually hidden houses reappeared'
        assert by_name['town-transparent']['changed_pixels'] < unlocked, 'Manual transparency was lost'
    (run / 'check-results.json').write_text(json.dumps(rows, indent=2) + '\n')
    print(f'{run.name}: {len(rows)} comparison groups; picking and manual state unchanged; restoration passes')
    for row in rows:
        print(f"  {row['view']}: kinds={row['focus_kinds']} changed={row['changed_pixels']} restored={row['restored_pixels']}")
