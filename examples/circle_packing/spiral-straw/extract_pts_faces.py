#!/usr/bin/env python3
"""
Extract points and faces from an STL file (binary or ASCII) and format them
as OpenSCAD arrays (`points` and `faces`).

  ### Features
  
  • Auto-detection: Handles both binary and ASCII STL formats.
  • Vertex Deduplication: Deduplicates shared vertices using configurable      
  coordinate precision (-d / --decimals, default 6).
  • Clean Formatting: Formats floats without trailing zeros or -0.
  • Command-Line Interface:
      • Run with defaults:
        ./extract_pts_faces.py
      (Reads spiral-straw.stl and outputs spiral-straw.txt)
      • Or specify custom files:
        ./extract_pts_faces.py -i input_model.stl -o output.scad -d 6 

"""

import argparse
import os
import struct
import sys


def parse_binary_stl(f):
    """Parse binary STL format."""
    f.seek(80)  # skip 80-byte header
    num_triangles_data = f.read(4)
    if len(num_triangles_data) < 4:
        raise ValueError("Invalid STL: file too short to read triangle count")
    num_triangles = struct.unpack('<I', num_triangles_data)[0]

    triangles = []
    for _ in range(num_triangles):
        data = f.read(50)
        if len(data) < 50:
            break
        floats = struct.unpack('<12fH', data)
        # floats[0:3] = normal vector
        v1 = floats[3:6]
        v2 = floats[6:9]
        v3 = floats[9:12]
        triangles.append((v1, v2, v3))

    return triangles


def parse_ascii_stl(f):
    """Parse ASCII STL format."""
    f.seek(0)
    triangles = []
    current_tri = []

    for line in f:
        line_str = line.decode('utf-8', errors='ignore').strip()
        if line_str.startswith('vertex'):
            parts = line_str.split()
            current_tri.append(tuple(float(x) for x in parts[1:4]))
            if len(current_tri) == 3:
                triangles.append(tuple(current_tri))
                current_tri = []

    return triangles


def parse_stl(filepath):
    """Detect format and parse STL file."""
    with open(filepath, 'rb') as f:
        header = f.read(80)
        f.seek(0, os.SEEK_END)
        file_size = f.tell()

        if file_size >= 84:
            f.seek(80)
            expected_count = struct.unpack('<I', f.read(4))[0]
            if file_size == 84 + expected_count * 50:
                f.seek(0)
                return parse_binary_stl(f)

        if header.strip().startswith(b'solid'):
            f.seek(0)
            return parse_ascii_stl(f)

        f.seek(0)
        return parse_binary_stl(f)


def format_coord(x, decimals=6):
    """Format float cleanly, stripping trailing zeros and avoiding negative zero."""
    r = round(x, decimals)
    if abs(r) < 10 ** (-(decimals + 2)):
        return '0'
    if r == int(r):
        return str(int(r))
    return f'{r:.{decimals}f}'.rstrip('0').rstrip('.')


def extract_points_and_faces(triangles, decimals=6):
    """Deduplicate vertices and construct indexed face list."""
    points = []
    point_map = {}
    faces = []

    for tri in triangles:
        face = []
        for vertex in tri:
            key = tuple(round(coord, decimals) for coord in vertex)
            if key not in point_map:
                point_map[key] = len(points)
                points.append(key)
            face.append(point_map[key])
        faces.append(face)

    return points, faces


def generate_openscad_code(points, faces, decimals=6):
    """Format points and faces as OpenSCAD array declarations."""
    lines = []
    lines.append('points = [')
    for i, p in enumerate(points):
        comma = ',' if i < len(points) - 1 else ''
        coords_str = ', '.join(format_coord(c, decimals) for c in p)
        lines.append(f'    [{coords_str}]{comma}')
    lines.append('];')
    lines.append('')
    lines.append('faces = [')
    for i, f in enumerate(faces):
        comma = ',' if i < len(faces) - 1 else ''
        lines.append(f'    [{f[0]}, {f[1]}, {f[2]}]{comma}')
    lines.append('];')
    lines.append('')
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Extract points and faces from an STL file to OpenSCAD arrays."
    )
    parser.add_argument(
        '-i', '--input',
        default='spiral-straw.stl',
        help="Input STL file (default: spiral-straw.stl)"
    )
    parser.add_argument(
        '-o', '--output',
        default='spiral-straw.txt',
        help="Output text/scad file (default: spiral-straw.txt)"
    )
    parser.add_argument(
        '-d', '--decimals',
        type=int,
        default=6,
        help="Decimal precision for vertex coordinates (default: 6)"
    )

    args = parser.parse_args()

    if not os.path.isfile(args.input):
        print(f"Error: Input file '{args.input}' not found.", file=sys.stderr)
        sys.exit(1)

    triangles = parse_stl(args.input)
    points, faces = extract_points_and_faces(triangles, decimals=args.decimals)
    code = generate_openscad_code(points, faces, decimals=args.decimals)

    if args.output == '-':
        sys.stdout.write(code)
    else:
        with open(args.output, 'w') as f:
            f.write(code)
        print(
            f"Successfully extracted {len(points)} points and {len(faces)} faces "
            f"from '{args.input}' to '{args.output}'."
        )


if __name__ == '__main__':
    main()
