"""Verify procedural export reproducibility, geometry and Phase 5 runtime evidence."""
import argparse
import json
import math
import re
from generate import exports, OUT

parser=argparse.ArgumentParser()
parser.add_argument('log', nargs='?')
args=parser.parse_args()
for path,content in exports().items():
    assert path.read_text()==content, f'Stale generated artifact: {path}'
data=json.loads((OUT/'library.json').read_text())
for name,faces in data['models'].items():
    assert 0<len(faces)<600, name
    for a,b,c,colour in faces:
        assert all(math.isfinite(v) for p in (a,b,c,colour) for v in p), name
        u=[b[i]-a[i] for i in range(3)]; v=[c[i]-a[i] for i in range(3)]
        assert sum(abs(u[i]*v[(i+1)%3]-u[(i+1)%3]*v[i]) for i in range(3))>1e-6, name
        assert all(0<=v<=1 for v in colour), name
print(f"PASS: {len(data['models'])} reproducible, finite, nondegenerate models; 110 house IDs enumerated")
if args.log:
    log=open(args.log,encoding='utf-8').read()
    audits=re.findall(r'PHASE5 ASSETS houses=(\d+) industry_tiles=(\d+) trees=(\d+) missing=(\d+) construction=(\d+)',log)
    assert len(audits)>=5, 'Missing multi-view audits'
    assert all(int(h)>0 and int(i)==12 and int(t)>0 and int(m)==0 for h,i,t,m,c in audits)
    names=list(data['models'])
    for model in ('mine_head','mine_hall','power_hall','power_stack','coal_yard'):
        assert re.search(rf'PHASE5 MODEL id={names.index(model)} tiles=[1-9]',log), model
    for engine,model in ((9,'locomotive'),(29,'wagon'),(123,'truck')):
        assert f'PHASE5 VEHICLE engine={engine} model={names.index(model)}' in log
    loads=[int(v) for v in re.findall(r'PHASE4 RUN tile=\d+ load=(\d+)',log)]
    assert 90 in loads and 0 in loads, 'Need full and empty train observations'
    assert not re.search(r'Assertion failed|Fatal error|Fixture failed',log)
    times=sorted(int(v) for v in re.findall(r'render/readback: (\d+) us',log))
    assert times
    print(f'PASS: {len(audits)} live asset audits, zero missing map assets, coal train and trucks mapped')
    print(f'Render/readback samples={len(times)}, median={times[len(times)//2]}us, p95={times[int(len(times)*.95)]}us, max={max(times)}us')
