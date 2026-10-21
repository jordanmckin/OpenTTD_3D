"""Phase 9.5c: check and summarise the off / contact / sun captures of tools/phase95c-shadows.ps1.

Each view's three images come from one paused run, so they differ only by shadows. Checks: every capture exists,
the run logged no OpenGL or shadow failures, shadows only darken (no pixel gets noticeably lighter), contact
shadows stay subtle and sun shadows add to them. Writes a comparison sheet per view and a JSON summary.
"""
import json
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image

runs = [Path(p) for p in sys.argv[1:-1]]
out = Path(sys.argv[-1])
out.mkdir(parents=True, exist_ok=True)
summary = []
for run in runs:
    log = (run / 'stderr.log').read_text(errors='replace')
    assert not re.search(r'3D proof OpenGL error|3D proof failed|shadows? (program )?unavailable|Assertion failed', log), run
    stats = re.findall(r'PHASE95C mode=(\d) failed=(\w+) sun_passes=(\d+)', log)
    assert stats and all(failed == 'false' for _, failed, _ in stats), run
    shots = run / 'screenshot'
    for off in sorted(shots.glob('*-off.*')):
        name = off.stem[:-len('-off')]
        images = {m: np.asarray(Image.open(next(shots.glob(f'{name}-{m}.*'))).convert('RGB'), dtype=np.int16) for m in ('off', 'contact', 'sun')}
        row = {'run': run.name, 'view': name}
        luma = {m: (v * [299, 587, 114]).sum(axis=2) / 1000 for m, v in images.items()}
        for mode in ('contact', 'sun'):
            dark = luma['off'] - luma[mode]
            row[f'{mode}_changed'] = round(float((np.abs(dark) > 3).mean()), 4)
            row[f'{mode}_mean_darkening'] = round(float(dark.mean()), 3)
            row[f'{mode}_max_darkening'] = round(float(dark.max()), 1)
            row[f'{mode}_lighter'] = round(float((dark < -3).mean()), 5)
        # Shadows only remove light; contact stays subtle; sun includes contact.
        assert row['contact_lighter'] < 0.001 and row['sun_lighter'] < 0.001, row
        assert row['contact_mean_darkening'] < 3.0, row
        assert row['sun_mean_darkening'] >= row['contact_mean_darkening'] - 0.05, row
        summary.append(row)
        h, w = images['off'].shape[:2]
        cw, ch = min(w, 900), min(h, 520)
        box = (w // 2 - cw // 2, h // 2 - ch // 2, w // 2 + cw // 2, h // 2 + ch // 2)
        parts = [Image.fromarray(images[m].astype(np.uint8)).crop(box) for m in ('off', 'contact', 'sun')]
        sheet = Image.new('RGB', (cw, ch * 3 + 8), 'white')
        for k, part in enumerate(parts):
            sheet.paste(part, (0, k * (ch + 4)))
        sheet.save(out / f'{name}.png', optimize=True)
(out / 'visual-results.json').write_text(json.dumps(summary, indent=2) + '\n')
print(f'{len(summary)} views passed')
for row in summary:
    print(f"  {row['view']}: contact {row['contact_changed']:.1%} px, mean -{row['contact_mean_darkening']:.2f}; "
          f"sun {row['sun_changed']:.1%} px, mean -{row['sun_mean_darkening']:.2f}")
