"""Measure lossless indexing of the embedded full-detail model vertices.

This reads the compiled face tables, retaining colour and unnormalised face normals
in each vertex key, just as the model shader consumes them. It estimates storage,
not frame time. No assets or generated headers are changed.
"""
import argparse
import json
import math
import re
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / 'OpenTTD-15.3' / 'OpenTTD-15.3'


def f32(value):
    return struct.unpack('f', struct.pack('f', value))[0]


def audit():
    rows = []
    for header in ('asset3d_art.h', 'asset3d_generated.h'):
        source = (ROOT / 'src/video' / header).read_text()
        for name, body in re.findall(r'inline constexpr Face (\w+)\[\] = \{(.*?)\n\};', source, re.S):
            unique = set()
            vertices = 0
            for line in body.splitlines():
                if not line.strip():
                    continue
                values = [f32(float(n)) for n in re.findall(r'(-?\d+(?:\.\d*)?(?:[eE][+-]?\d+)?)f', line)]
                assert len(values) == 12, (name, line)
                points = [values[i:i+3] for i in (0, 3, 6)]
                a = [f32(points[1][i] - points[0][i]) for i in range(3)]
                b = [f32(points[2][i] - points[0][i]) for i in range(3)]
                normal = tuple(f32(f32(a[j]*b[k]) - f32(a[k]*b[j])) for j, k in ((1, 2), (2, 0), (0, 1)))
                if math.sqrt(sum(n*n for n in normal)) < .0001:
                    continue
                vertices += 3
                for point in points:
                    unique.add(tuple(point) + tuple(values[9:]) + normal)
            rows.append(dict(header=header, model=name, vertices=vertices, unique_vertices=len(unique)))
    assert rows
    vertices = sum(r['vertices'] for r in rows)
    unique = sum(r['unique_vertices'] for r in rows)
    return dict(models=len(rows), vertices=vertices, unique_vertices=unique,
                original_44_byte_vertices=vertices*44,
                compact_36_byte_vertices=vertices*36,
                indexed_36_byte_vertices_with_uint32_indices=unique*36+vertices*4,
                indexed_saving_over_compact_bytes=vertices*32-unique*36,
                note='Lossless vertex keys include position, material colour and the exact unnormalised local face normal. Indexing is an estimate, not implemented or timed.',
                per_model=rows)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = audit()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: value for key, value in result.items() if key != 'per_model'}, indent=2))
