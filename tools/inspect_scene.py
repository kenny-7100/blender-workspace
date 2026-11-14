"""Read-only scene inspection in a fresh Blender process; does not save the file."""
import json
import argparse
from pathlib import Path
import sys
import bpy
import bmesh

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', type=Path)
parser.add_argument('--require-closed', action='store_true', help='For solid assets; do not use for intentionally open meshes')
args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
objects = []
for obj in bpy.context.scene.objects:
    if obj.type != 'MESH' or obj.get('role') != 'asset':
        continue
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    item = {'name': obj.name, 'vertices': len(bm.verts), 'faces': len(bm.faces),
                    'non_manifold_edges': sum(not e.is_manifold for e in bm.edges),
                    'dimensions_m': list(obj.dimensions)}
    bm.free()
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    evaluated_mesh = evaluated.to_mesh()
    bm = bmesh.new()
    bm.from_mesh(evaluated_mesh)
    item['evaluated_non_manifold_edges'] = sum(not e.is_manifold for e in bm.edges)
    item['evaluated_signed_volume_m3'] = bm.calc_volume(signed=True)
    bm.free()
    evaluated.to_mesh_clear()
    objects.append(item)
missing = [im.filepath for im in bpy.data.images if im.source == 'FILE' and not im.packed_file
           and not __import__('os').path.exists(bpy.path.abspath(im.filepath))]
report = {'file': Path(bpy.data.filepath).name, 'blender': bpy.app.version_string, 'objects': objects,
          'cameras': [o.name for o in bpy.context.scene.objects if o.type == 'CAMERA'],
          'missing_images': missing,
          'require_closed': args.require_closed,
          'limitations': 'Structural report only; open label sheets may be intentional. No visual quality certification.'}
assert not missing, missing
assert objects, 'No objects tagged role=asset'
if args.require_closed:
    assert all(o['evaluated_non_manifold_edges'] == 0 for o in objects), 'Evaluated asset surfaces must be closed'
    assert all(o['evaluated_signed_volume_m3'] > 0 for o in objects), 'Asset volume must be positive'
if args.output:
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2)+'\n')
print('SCENE_INSPECTION_OK '+json.dumps(report))
