"""Original procedural miniature assets. SPDX-License-Identifier: GPL-2.0-only.

No dependencies. Run from any directory; --check verifies checked-in exports.
"""
import argparse
import hashlib
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / 'OpenTTD-15.3/OpenTTD-15.3'
OUT = ROOT / 'assets/3d'
MODELS = {}
BRICK = (.69, .35, .23)
CREAM = (.86, .77, .57)
ROOF = (.26, .33, .37)
GLASS = (.30, .65, .73)
STEEL = (.30, .40, .43)
COAL = (.12, .14, .16)
GREEN = (.22, .47, .25)


class Mesh:
    def __init__(self, name):
        self.faces = []
        MODELS[name] = self

    def tri(self, a, b, c, colour):
        self.faces.append([a, b, c, colour])

    def quad(self, a, b, c, d, colour):
        self.tri(a, b, c, colour)
        self.tri(a, c, d, colour)

    def box(self, lo, hi, colour):
        x,y,z = lo
        X,Y,Z = hi
        a,b,c,d = (x,y,z),(X,y,z),(X,Y,z),(x,Y,z)
        e,f,g,h = (x,y,Z),(X,y,Z),(X,Y,Z),(x,Y,Z)
        for q in [(a,b,f,e),(b,c,g,f),(c,d,h,g),(d,a,e,h),(e,f,g,h)]:
            self.quad(*q, colour)

    def roof(self, x, y, X, Y, z, height, colour=ROOF):
        a,b,c,d = (x,y,z),(X,y,z),(X,Y,z),(x,Y,z)
        e,f = ((x+X)/2,y,z+height),((x+X)/2,Y,z+height)
        self.quad(a,e,f,d,colour)
        self.quad(e,b,c,f,colour)
        self.tri(a,b,e,CREAM)
        self.tri(d,f,c,CREAM)

    def windows(self, z, top, x=3, X=13, y=3, Y=13):
        for h in range(z, top, 4):
            for p in range(x+1, X-1, 3):
                self.box((p,y-.06,h),(p+1.5,y,h+2),GLASS)
                self.box((p,Y,h),(p+1.5,Y+.06,h+2),GLASS)
            for p in range(y+1, Y-1, 3):
                self.box((x-.06,p,h),(x,p+1.5,h+2),GLASS)
                self.box((X,p,h),(X+.06,p+1.5,h+2),GLASS)

    def cone(self, x,y,z,r,h,colour, sides=8):
        for i in range(sides):
            a,b = i*math.tau/sides,(i+1)*math.tau/sides
            self.tri((x+r*math.cos(a),y+r*math.sin(a),z),
                     (x+r*math.cos(b),y+r*math.sin(b),z),(x,y,z+h),colour)


def library():
    m=Mesh('missing'); m.box((3,3,0),(13,13,6),(.8,.15,.65)); m.roof(2,2,14,14,6,3)
    for i in range(3):
        m=Mesh('house'+str(i)); h=7+i*2
        m.box((1,1,0),(15,15,.5),(.65,.64,.53))
        m.box((3,3,.5),(13,13,h),[CREAM,BRICK,(.76,.73,.61)][i])
        m.windows(2,h-1); m.roof(2,2,14,14,h,4, [ROOF,BRICK,ROOF][i])
        m.box((10,8,h),(11.5,9.5,h+5),BRICK)
        m.box((7,2.9,.5),(9,3,3.5),ROOF)
    m=Mesh('office'); m.box((2,2,0),(14,14,1),CREAM)
    m.box((3,3,1),(13,13,19),CREAM); m.windows(3,18)
    m.box((2.5,2.5,19),(13.5,13.5,20),ROOF)
    m=Mesh('church'); m.box((3,3,0),(13,13,10),CREAM); m.roof(2,2,14,14,10,5)
    m.box((5,2,0),(9,6,18),CREAM); m.cone(7,4,18,3.4,7,ROOF,4)
    m=Mesh('park'); m.box((1,7,0),(15,9,.3),CREAM)
    m.box((3,3,0),(4,4,5),BRICK); m.cone(3.5,3.5,4,3,8,GREEN)
    m.box((10,11,0),(14,12,2),BRICK)
    m=Mesh('monument'); m.box((5,5,0),(11,11,2),CREAM); m.box((7,7,2),(9,9,10),STEEL)
    m=Mesh('theater'); m.box((2,2,0),(14,14,11),BRICK); m.roof(1,1,15,15,11,2)
    m.box((3,1,4),(13,3,5),CREAM); m.box((5,1.9,0),(11,2,4),GLASS)
    for q in range(4):
        m=Mesh('stadium'+str(q)); m.box((0,0,0),(16,16,.3),(.27,.52,.29))
        # Base 2x2 house tile order: (0,0), (0,1), (1,0), (1,1).
        sx,sy=q//2,q%2
        for step in range(3):
            x=step if sx==0 else 15-step
            y=step if sy==0 else 15-step
            m.box((x,0,.3),(x+1,16,4-step),CREAM)
            m.box((0,y,.3),(16,y+1,4-step),CREAM)
        x=5 if sx==0 else 10
        m.box((x,4,.31),(x+.15,12,.36),CREAM)
    m=Mesh('construction'); m.box((2,2,0),(14,14,1),CREAM)
    for x in (3,12):
        for y in (3,12): m.box((x,y,1),(x+1,y+1,6),BRICK)
    m.box((2,6,1),(6,10,3),BRICK)
    for name in ('factory','mine_hall','power_hall'):
        m=Mesh(name); m.box((0,0,0),(16,16,.4),(.55,.53,.46))
        m.box((1,2,.4),(15,14,10),BRICK); m.roof(0,1,16,15,10,4)
        m.windows(3,9,1,15,2,14)
        if name=='factory': m.box((11,10,10),(13,12,23),BRICK)
    m=Mesh('mine_head'); m.box((0,0,0),(16,16,.5),(.55,.53,.46))
    for x in (4,11):
        for y in (4,11): m.box((x,y,.5),(x+1,y+1,20),STEEL)
    m.box((3,3,17),(13,13,18),CREAM); m.roof(2,2,14,14,20,3)
    for z in (5,10,15): m.box((4,4,z),(12,5,z+.7),STEEL)
    m.box((7,7,0),(9,9,20),COAL)
    m=Mesh('coal_yard'); m.box((0,0,0),(16,16,.4),(.52,.50,.43))
    m.cone(6,7,.4,5,5,COAL); m.cone(11,10,.4,4,4,COAL)
    m=Mesh('power_stack'); m.box((0,0,0),(16,16,.4),(.55,.53,.46))
    m.box((4,4,.4),(12,12,5),BRICK)
    m.box((6,6,5),(10,10,27),BRICK); m.box((5.5,5.5,26),(10.5,10.5,28),CREAM)
    m.box((6,6,28),(10,10,28.2),COAL)
    m=Mesh('tree'); m.box((-.6,-.6,0),(.6,.6,5),BRICK)
    m.cone(0,0,3,3.5,7,GREEN); m.cone(0,0,6,2.7,6,(.30,.55,.27))
    m=Mesh('tree_dead'); m.box((-.5,-.5,0),(.5,.5,7),BRICK)
    m.box((-.4,-2,4),(.4,2,4.7),BRICK)
    m=Mesh('platform')
    for y in (0,12):
        m.box((0,y,0),(16,y+4,2),CREAM)
        m.box((0,y+(.0 if y else 3.5),2),(16,y+(0.5 if y else 4),2.1),(.94,.87,.62))
        for x in (3,12): m.box((x,y+1,2),(x+.4,y+1.4,7),STEEL)
        m.roof(1,y,15,y+4,7,1.3,ROOF)
    for name in ('locomotive','wagon','truck'):
        m=Mesh(name); m.box((-3.6,-1.8,.7),(3.6,1.8,1.4),COAL)
        for x in (-2.5,2):
            for y in (-2,1.5): m.box((x-.5,y,.3),(x+.5,y+.5,1.8),COAL)
        if name=='locomotive':
            m.box((-3.4,-1.7,1.4),(-.8,1.7,5.5),(.18,.39,.48))
            m.box((-3.6,-1.9,5.5),(-.6,1.9,5.9),ROOF)
            m.box((-3,-1.76,3.7),(-1.2,1.76,4.8),GLASS)
            m.box((-.8,-1.4,1.4),(3.3,1.4,4),(.18,.39,.48))
            m.box((2,-.6,4),(2.9,.6,5.6),COAL)
        elif name=='wagon':
            m.box((-3.5,-1.8,1.4),(3.5,1.8,2),BRICK)
            for y in (-1.8,1.5): m.box((-3.5,y,2),(3.5,y+.3,4),BRICK)
            for x in (-3.5,3.2): m.box((x,-1.8,2),(x+.3,1.8,4),BRICK)
        else:
            m.box((-3.5,-1.6,1.4),(1,1.6,4.4),CREAM)
            m.box((1,-1.6,1.4),(3.5,1.6,3.7),(.18,.51,.57))
            m.box((2.4,-1.65,2.7),(3.2,1.65,3.5),GLASS)


def exports():
    library()
    # Read identities from this checkout, not sprite numbers or guessed ID ranges.
    source=(ROOT/'src/table/town_land.h').read_text()
    entries=re.findall(r'MS\([^;]*?STR_TOWN_BUILDING_NAME_(\w+).*?\), // ([0-9A-F]{2})',source,re.S)
    houses=[]
    for label,number in entries:
        i=int(number,16)
        model='missing'
        if any(s in label for s in ('HOUSE','COTTAGE','BUNGALOW')): model='house'+str(i%3)
        elif any(s in label for s in ('OFFICE','FLAT','HOTEL','SHOP')): model='office'
        elif 'CHURCH' in label: model='church'
        elif 'PARK' in label: model='park'
        elif any(s in label for s in ('STATUE','FOUNTAIN')): model='monument'
        elif 'WAREHOUSE' in label: model='factory'
        elif 'STADIUM' in label: model='stadium'+str((i-20) if i<24 else (i-32))
        elif 'THEATER' in label or 'CINEMA' in label: model='theater'
        houses.append(dict(id=i,label=label,model=model))
    assert len(houses)==110, len(houses)
    assert [h['id'] for h in houses]==list(range(110))
    names=list(MODELS)
    data={'version':1,'seed':20261016,'license':'GPL-2.0-only','houses':houses,
          'industry_tiles':{'0':'mine_head','1':'mine_head','2':'mine_hall','3':'coal_yard','4':'coal_yard','5':'mine_hall','6':'mine_hall','7':'power_hall','8':'power_stack','9':'power_stack','10':'coal_yard'},
          'models':{n:m.faces for n,m in MODELS.items()}}
    header=['// Generated by tools/3d_assets/generate.py; GPL-2.0-only. Do not edit.',
            '#ifndef ASSET3D_GENERATED_H','#define ASSET3D_GENERATED_H','namespace Asset3D {',
            'struct Face { float p[3][3]; float colour[3]; };',
            'struct Model { const Face *faces; size_t count; };',
            'enum ID { '+', '.join(n.upper() for n in names)+' };']
    def f(v): return f'{float(v):.6f}f'
    for name,m in MODELS.items():
        header.append('inline constexpr Face '+name+'[] = {')
        for a,b,c,col in m.faces:
            header.append('{{'+','.join('{'+','.join(map(f,p))+'}' for p in (a,b,c))+'},{'+','.join(map(f,col))+'}},')
        header.append('};')
    header.append('inline constexpr Model models[] = {'+','.join('{'+n+', std::size('+n+')}' for n in names)+'};')
    header.append('inline constexpr ID houses[] = {'+','.join(h['model'].upper() for h in houses)+'};')
    header.append('constexpr ID House(unsigned id) { return id < std::size(houses) ? houses[id] : MISSING; }')
    header.append('constexpr ID Industry(unsigned type, unsigned gfx) { if (type == 0 && gfx <= 6) { constexpr ID ids[] = {MINE_HEAD,MINE_HEAD,MINE_HALL,COAL_YARD,COAL_YARD,MINE_HALL,MINE_HALL}; return ids[gfx]; } if (type == 1 && gfx >= 7 && gfx <= 10) { constexpr ID ids[] = {POWER_HALL,POWER_STACK,POWER_STACK,COAL_YARD}; return ids[gfx-7]; } if (type == 6) return FACTORY; return MISSING; }')
    header+=['}', '#endif','']
    # Offline vector contact sheet uses exactly the exported triangles.
    svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="1400" viewBox="0 0 1200 1400"><rect width="1200" height="1400" fill="#e8e2d3"/>']
    for i,(name,m) in enumerate(MODELS.items()):
        ox=150+(i%4)*300; oy=140+(i//4)*190
        for a,b,c,col in sorted(m.faces,key=lambda t:sum(p[0]+p[1]+p[2]*.1 for p in t[:3])):
            pts=' '.join(f'{ox+(p[1]-p[0])*4:.2f},{oy+(p[0]+p[1])*2-p[2]*4:.2f}' for p in (a,b,c))
            rgb=','.join(str(round(v*255)) for v in col)
            svg.append(f'<polygon points="{pts}" fill="rgb({rgb})" stroke="#000" stroke-opacity=".08" stroke-width=".5"/>')
        svg.append(f'<text x="{ox}" y="{oy+48}" text-anchor="middle" font-family="sans-serif" font-size="16">{name}</text>')
    svg.append('</svg>')
    payload=json.dumps(data,indent=2)+'\n'
    manifest={'license':'GPL-2.0-only','provenance':'Original procedural geometry; no third-party models or textures.',
              'generator':'tools/3d_assets/generate.py','sha256':hashlib.sha256(payload.encode()).hexdigest(),
              'triangle_counts':{n:len(m.faces) for n,m in MODELS.items()}}
    return {OUT/'library.json':payload, OUT/'manifest.json':json.dumps(manifest,indent=2)+'\n',
            OUT/'preview.svg':'\n'.join(svg),ROOT/'src/video/asset3d_generated.h':'\n'.join(header)}


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--check',action='store_true'); args=parser.parse_args()
    for path,content in exports().items():
        if args.check:
            assert path.read_text()==content, f'Stale export: {path}'
        else:
            path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(content.encode('utf-8'))
    print(f'{len(MODELS)} deterministic models: '+('verified' if args.check else 'exported'))

