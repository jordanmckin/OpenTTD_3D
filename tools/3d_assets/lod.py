"""Conservative, deterministic vertex clustering for distant library instances.

Keep each connected component's axis extrema and every material. No component is
removed. Reject a reduction if a surviving face reverses its winding. The error
is the largest vertex displacement (including vertices of collapsed triangles),
used by the runtime to cap projected displacement at half a screen pixel.
"""
import math


def normal(face):
	a, b, c = face[:3]
	u, v = [b[i] - a[i] for i in range(3)], [c[i] - a[i] for i in range(3)]
	return (u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0])


def reduce_faces(faces, cell):
	# Weld the exported triangle soup at the same precision as the embedded data.
	faces = [tuple(tuple(round(v, 4) for v in p) for p in f) for f in faces]
	parents = {}
	def root(p):
		parents.setdefault(p, p)
		while parents[p] != p:
			parents[p] = parents[parents[p]]
			p = parents[p]
		return p
	for a, b, c, _ in faces:
		for p in (b, c):
			parents[root(p)] = root(a)
	parts = {}
	for f in faces:
		parts.setdefault(root(f[0]), []).append(f)
	result, error = [], 0.0
	for part in parts.values():
		points = sorted({p for f in part for p in f[:3]})
		lo = [min(p[i] for p in points) for i in range(3)]
		hi = [max(p[i] for p in points) for i in range(3)]
		groups = {}
		for p in points:
			# Extremal coordinates never merge with interior coordinates, keeping bounds.
			extrema = tuple(-1 if p[i] == lo[i] else 1 if p[i] == hi[i] else 0 for i in range(3))
			key = (tuple(math.floor((p[i] - lo[i]) / cell) for i in range(3)), extrema)
			groups.setdefault(key, []).append(p)
		mapping = {}
		for group in groups.values():
			centre = tuple(round(sum(p[i] for p in group) / len(group), 4) for i in range(3))
			mapping.update((p, centre) for p in group)
		reduced, valid = [], True
		for f in part:
			new = tuple(mapping[p] for p in f[:3]) + (f[3],)
			n = normal(new)
			if sum(x*x for x in n) < 1e-8:
				continue
			if sum(a*b for a, b in zip(n, normal(f))) <= 0:
				valid = False
				break
			reduced.append(new)
		new_points = [p for f in reduced for p in f[:3]]
		keeps_bounds = bool(new_points) and all(min(p[i] for p in new_points) == lo[i] and max(p[i] for p in new_points) == hi[i] for i in range(3))
		if not valid or not keeps_bounds or {f[3] for f in reduced} != {f[3] for f in part}:
			reduced = part
		else:
			error = max(error, max(math.dist(p, mapping[p]) for p in points))
		result.extend(reduced)
	return result, error
