"""Small Blender mesh constructors without context-dependent bpy.ops.

Functions return new, unlinked meshes. Callers own objects, collections, materials,
transforms and modifiers. Dimensions must be positive; sphere/torus subdivision
counts must be integers above the stated minimum. Run with Blender Python.
"""
import math
import bpy


def _positive(*values):
    if any(not math.isfinite(v) or v <= 0 for v in values):
        raise ValueError('Dimensions must be finite and positive')


def _count(value, minimum):
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise ValueError(f'Subdivision count must be an integer >= {minimum}')


def _mesh(name, vertices, faces, smooth=False):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    if smooth:
        for face in mesh.polygons:
            face.use_smooth = True
    return mesh


def box_mesh(name, dimensions):
    dimensions = tuple(dimensions)
    if len(dimensions) != 3:
        raise ValueError('Box dimensions must have three components')
    _positive(*dimensions)
    x, y, z = (v / 2 for v in dimensions)
    vertices = [(-x,-y,-z), (x,-y,-z), (x,y,-z), (-x,y,-z),
                (-x,-y,z), (x,-y,z), (x,y,z), (-x,y,z)]
    faces = [(0,3,2,1), (4,5,6,7), (0,1,5,4), (1,2,6,5), (2,3,7,6), (3,0,4,7)]
    return _mesh(name, vertices, faces)


def uv_sphere_mesh(name, segments=24, rings=12):
    """Unit-radius sphere, with one vertex at each pole."""
    _count(segments, 3)
    _count(rings, 2)
    vertices, faces = [(0, 0, 1)], []
    for i in range(1, rings):
        a = math.pi * i / rings
        for j in range(segments):
            b = math.tau * j / segments
            vertices.append((math.sin(a)*math.cos(b), math.sin(a)*math.sin(b), math.cos(a)))
    bottom = len(vertices)
    vertices.append((0, 0, -1))
    for j in range(segments):
        faces.append((0, 1+j, 1+(j+1)%segments))
    for i in range(rings-2):
        for j in range(segments):
            a = 1+i*segments+j
            b = 1+i*segments+(j+1)%segments
            faces.append((a, a+segments, b+segments, b))
    for j in range(segments):
        faces.append((1+(rings-2)*segments+j, bottom, 1+(rings-2)*segments+(j+1)%segments))
    return _mesh(name, vertices, faces, smooth=True)


def cylinder_mesh(name, radius, depth, segments=32):
    """Closed Z-axis cylinder, with smooth side faces and flat end caps."""
    _positive(radius, depth)
    _count(segments, 3)
    vertices = []
    for z in (-depth/2, depth/2):
        for j in range(segments):
            a = j*math.tau/segments
            vertices.append((radius*math.cos(a), radius*math.sin(a), z))
    faces = [tuple(reversed(range(segments))), tuple(range(segments, 2*segments))]
    for j in range(segments):
        k = (j+1)%segments
        faces.append((j, k, k+segments, j+segments))
    mesh = _mesh(name, vertices, faces)
    for face in list(mesh.polygons)[2:]:
        face.use_smooth = True
    return mesh


def torus_mesh(name, major_radius, minor_radius, segments=40, sides=8):
    """Closed Z-axis ring torus. Self-intersecting spindle tori are rejected."""
    _positive(major_radius, minor_radius)
    if minor_radius >= major_radius:
        raise ValueError('Minor radius must be smaller than major radius')
    _count(segments, 3)
    _count(sides, 3)
    vertices, faces = [], []
    for i in range(segments):
        a = i*math.tau/segments
        for j in range(sides):
            b = j*math.tau/sides
            radius = major_radius+minor_radius*math.cos(b)
            vertices.append((radius*math.cos(a), radius*math.sin(a), minor_radius*math.sin(b)))
    for i in range(segments):
        for j in range(sides):
            faces.append((i*sides+j, ((i+1)%segments)*sides+j,
                          ((i+1)%segments)*sides+(j+1)%sides, i*sides+(j+1)%sides))
    return _mesh(name, vertices, faces, smooth=True)


def rounded_box_mesh(name, dimensions, radius, corner_segments=8):
    """Extruded rounded XY rectangle, with independent Z thickness.

    Use this for thin lids/panels whose corner radius exceeds their thickness.
    The faces are flat; only vertical sides are smooth. Radius cannot exceed
    half the smaller planar dimension. Object rotation selects another plane.
    """
    dimensions = tuple(dimensions)
    if len(dimensions) != 3:
        raise ValueError('Rounded box dimensions must have three components')
    _positive(*dimensions, radius)
    _count(corner_segments, 1)
    width, height, depth = dimensions
    if radius > min(width, height)/2:
        raise ValueError('Corner radius exceeds half the smaller planar dimension')
    outline = []
    for cx, cy, start in [
        (width/2-radius, height/2-radius, 0),
        (-width/2+radius, height/2-radius, 90),
        (-width/2+radius, -height/2+radius, 180),
        (width/2-radius, -height/2+radius, 270),
    ]:
        for j in range(corner_segments+1):
            angle = math.radians(start+j*90/corner_segments)
            point = (cx+radius*math.cos(angle), cy+radius*math.sin(angle))
            # At the maximum radius adjacent arcs can share a tangent point.
            if not outline or math.dist(point, outline[-1]) > 1e-10:
                outline.append(point)
    if math.dist(outline[0], outline[-1]) < 1e-10:
        outline.pop()
    count = len(outline)
    vertices = [(x, y, z) for z in (-depth/2, depth/2) for x, y in outline]
    faces = [tuple(reversed(range(count))), tuple(range(count, 2*count))]
    for j in range(count):
        k = (j+1)%count
        faces.append((j, k, k+count, j+count))
    mesh = _mesh(name, vertices, faces)
    for face in list(mesh.polygons)[2:]:
        face.use_smooth = True
    return mesh
