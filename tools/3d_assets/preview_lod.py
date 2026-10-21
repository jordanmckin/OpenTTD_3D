"""Render the exact embedded full/LOD triangles for visual approval (Pillow + NumPy).

Usage: python tools/3d_assets/preview_lod.py [output directory]
Full detail and reduced meshes share camera, lighting and company colours.
The enlarged game-size pair uses nearest-neighbour pixels; the close-up pair
deliberately reveals simplification that is only used at distant zooms in game.
"""
import html
import json
import math
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2] / 'OpenTTD-15.3' / 'OpenTTD-15.3'


def models(path):
	arrays = re.findall(r'inline constexpr Face (\w+)\[\] = \{\n(.*?)\n\};', path.read_text(), re.S)
	return [(name, np.array([[float(v) for v in re.findall(r'(-?\d+\.\d*)f', row)]
		for row in body.splitlines()], dtype=float).reshape(-1, 4, 3)) for name, body in arrays]


def render(faces, scale, yaw, centre, size=(180, 110)):
	w, h = size
	image = np.full((h, w, 3), (231, 235, 228), dtype=np.uint8)
	depth = np.full((h, w), -np.inf)
	c, s = math.cos(yaw), math.sin(yaw)
	p = faces[:, :3].copy()
	x, y = p[:, :, 0].copy(), p[:, :, 1].copy()
	p[:, :, 0], p[:, :, 1] = x*c-y*s, x*s+y*c
	projected = np.stack((2*(p[:, :, 1]-p[:, :, 0]), p[:, :, 0]+p[:, :, 1]-p[:, :, 2],
		p[:, :, 0]+p[:, :, 1]+2*p[:, :, 2]), axis=2)
	projected[:, :, 0] = (projected[:, :, 0]-centre[0])*scale+w/2
	projected[:, :, 1] = (projected[:, :, 1]-centre[1])*scale+h/2
	n = np.cross(p[:, 1]-p[:, 0], p[:, 2]-p[:, 0])
	n[n[:, 2] < 0] *= -1
	light = .62+.38*np.maximum(0, n @ np.array([-.4, -.5, .768]) / np.maximum(1e-20, np.linalg.norm(n, axis=1)))
	colours = faces[:, 3].copy()
	colours[colours[:, 0] == -1] = (.95, .38, .12)
	colours[colours[:, 0] == -2] = (.15, .4, .85)
	glow = colours[:, 0] > 1.5
	colours *= light[:, None]
	colours[glow] = faces[glow, 3]-2
	colours = np.clip(colours*255, 0, 255).astype(np.uint8)
	for triangle, colour in zip(projected, colours):
		x0, y0 = np.maximum(0, np.floor(triangle[:, :2].min(axis=0))).astype(int)
		x1, y1 = np.minimum((w-1, h-1), np.ceil(triangle[:, :2].max(axis=0))).astype(int)
		if x1 < x0 or y1 < y0:
			continue
		a, b, c = triangle
		d = (b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
		if abs(d) < 1e-10:
			continue
		yy, xx = np.mgrid[y0:y1+1, x0:x1+1]
		wa = ((b[1]-c[1])*(xx+.5-c[0])+(c[0]-b[0])*(yy+.5-c[1]))/d
		wb = ((c[1]-a[1])*(xx+.5-c[0])+(a[0]-c[0])*(yy+.5-c[1]))/d
		wc = 1-wa-wb
		z = wa*a[2]+wb*b[2]+wc*c[2]
		patch = depth[y0:y1+1, x0:x1+1]
		keep = (wa >= 0) & (wb >= 0) & (wc >= 0) & (z > patch)
		patch[keep] = z[keep]
		image[y0:y1+1, x0:x1+1][keep] = colour
	return Image.fromarray(image)


def main():
	out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'docs/3d/evidence/phase7/p10/review'
	out.mkdir(parents=True, exist_ok=True)
	full = models(ROOT / 'src/video/asset3d_art.h')
	lods = models(ROOT / 'src/video/asset3d_lod.h')
	report = json.loads((ROOT / 'assets/3d/lod-report.json').read_text())
	rows = []
	for i, entry in enumerate(report):
		_, original = full[entry['model']]
		name, reduced = lods[i]
		assert len(original) == entry['full'] and len(reduced) == entry['reduced']
		radius = np.linalg.norm(original[:, :3, :2], axis=2).max()
		height = np.ptp(original[:, :3, 2])
		scale = .5
		while entry['error']*math.sqrt(8)*scale > .5 or math.hypot(2*radius, height)*math.sqrt(8)*scale > 64:
			scale /= 2
		strip = Image.new('RGB', (720, 250), 'white')
		draw = ImageDraw.Draw(strip)
		for angle in range(2):
			yaw = angle*math.pi/2
			p = original[:, :3].reshape(-1, 3)
			x, y = p[:, 0]*math.cos(yaw)-p[:, 1]*math.sin(yaw), p[:, 0]*math.sin(yaw)+p[:, 1]*math.cos(yaw)
			q = np.stack((2*(y-x), x+y-p[:, 2]), axis=1)
			centre = (q.min(axis=0)+q.max(axis=0))/2
			close = min(6, 160/max(1, np.ptp(q[:, 0])), 90/max(1, np.ptp(q[:, 1])))
			for col, faces in enumerate((original, reduced)):
				strip.paste(render(faces, close, yaw, centre), (col*180, angle*125+15))
				tiny = render(faces, scale, yaw, centre, (44, 26)).resize((176, 104), Image.Resampling.NEAREST)
				strip.paste(tiny, (360+col*180, angle*125+15))
		for x, label in enumerate(('Full, close-up', 'LOD, close-up', 'Full, game pixels x4', 'LOD, game pixels x4')):
			draw.text((x*180+5, 2), label, fill='black')
		file = f'{i:03d}-{name}.png'
		strip.save(out / file)
		rows.append(f'<article data-key="{html.escape(entry["key"])}"><h2>{html.escape(entry["key"])} / model {entry["model"]} / LOD {entry["level"]}</h2>'
			f'<p>{entry["full"]:,} → {entry["reduced"]:,} triangles ({100*(1-entry["reduced"]/entry["full"]):.1f}% fewer). '
			f'Game pair: scale {scale:g}; projected vertex movement ≤ {entry["error"]*math.sqrt(8)*scale:.3f} px. Two camera directions.</p>'
			f'<img loading="lazy" width="720" height="250" src="{file}" alt="Full and reduced meshes from two directions"></article>')
	page = '<!doctype html><html lang="en"><meta charset="utf-8"><title>Phase 7 LOD review</title><style>body{font:16px system-ui;margin:32px auto;max-width:1480px;background:#f1f3f5;color:#18252d}h1{font-size:28px}h2{font-size:17px}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(720px,1fr));gap:16px}article{background:white;padding:10px;border-radius:8px}p{line-height:1.5}img{max-width:100%;height:auto}input{padding:10px;width:320px;margin:16px 0}</style>'
	page += '<h1>Phase 7 priority 10 — distant model review</h1><p>Full detail remains the default. These are the exact generated game meshes, rendered offline with the classic camera projection, company colours and directional lighting. Close-ups reveal the simplification; the game-size pair shows the permitted distant scale, enlarged 4× without smoothing. Static buildings and terrain have no LOD change. Rendering and silhouette approval are separate from the runtime reference tests.</p><input placeholder="Filter: road, train, aircraft, effect…" aria-label="Filter models" oninput="document.querySelectorAll(\'article\').forEach(a=>a.hidden=!a.dataset.key.includes(this.value.toLowerCase()))"><main>'
	page += '\n'.join(rows) + '</main></html>'
	(out / 'index.html').write_text(page, encoding='utf-8')
	print(f'{len(rows)} model comparisons: {out / "index.html"}')


if __name__ == '__main__':
	main()
