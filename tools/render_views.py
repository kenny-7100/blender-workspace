"""Blender script: render selected named cameras from an existing blend file.

./bin/blender --background FILE --python-exit-code 1 --python tools/render_views.py -- --output DIR
"""
import argparse
import json
from pathlib import Path
import sys
import bpy

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--views', default='Hero,Front,Back,Detail')
parser.add_argument('--samples', type=int, default=64)
parser.add_argument('--width', type=int, default=900)
parser.add_argument('--height', type=int, default=1200)
parser.add_argument('--device', choices=['CPU', 'METAL'], default='CPU')
args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
args.output.mkdir(parents=True, exist_ok=True)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = args.samples
scene.cycles.use_denoising = True
scene.render.resolution_x, scene.render.resolution_y = args.width, args.height
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
if args.device == 'METAL':
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'METAL'
    prefs.get_devices()
    devices = [d for d in prefs.devices if d.type == 'METAL']
    if not devices:
        raise RuntimeError('Requested Metal but no Metal device was found')
    for d in prefs.devices:
        d.use = d.type == 'METAL'
    scene.cycles.device = 'GPU'
else:
    scene.cycles.device = 'CPU'
records = []
for name in args.views.split(','):
    camera = bpy.data.objects.get('Camera.'+name)
    if camera is None or camera.type != 'CAMERA':
        raise ValueError(f'Missing camera Camera.{name}')
    scene.camera = camera
    scene.render.filepath = str(args.output.resolve() / f'{name.lower()}.png')
    bpy.ops.render.render(write_still=True)
    records.append({'camera': camera.name, 'file': scene.render.filepath})
report = {'blender': bpy.app.version_string, 'device': args.device, 'samples': args.samples,
          'resolution': [args.width, args.height], 'views': records}
(args.output / 'render-report.json').write_text(json.dumps(report, indent=2)+'\n')
print('RENDER_VIEWS_OK', json.dumps(report))
