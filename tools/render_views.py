"""Blender script: render selected named cameras from an existing blend file.

./bin/blender --background FILE --python-exit-code 1 --python tools/render_views.py -- --output DIR
"""
import argparse
import json
from pathlib import Path
import sys
import time
import bpy

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--views', default='Hero')
parser.add_argument('--quality', choices=['preview', 'final'], default='preview')
parser.add_argument('--samples', type=int)
parser.add_argument('--width', type=int)
parser.add_argument('--height', type=int)
parser.add_argument('--device', choices=['CPU', 'METAL'], default='CPU')
args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
defaults = (24, 600, 800) if args.quality == 'preview' else (128, 900, 1200)
for name, default in zip(('samples', 'width', 'height'), defaults):
    if getattr(args, name) is None:
        setattr(args, name, default)
    if getattr(args, name) < 1:
        parser.error(f'{name} must be positive')
names = [name.strip() for name in args.views.split(',')]
if any(not name or '/' in name or '\\' in name for name in names):
    parser.error('views must contain camera suffixes without path separators')
if len({name.lower() for name in names}) != len(names):
    parser.error('views must have distinct output filenames')
view_cameras = []
for name in names:
    camera = bpy.data.objects.get('Camera.'+name)
    if camera is None or camera.type != 'CAMERA':
        parser.error(f'Missing camera Camera.{name}; no views were rendered')
    view_cameras.append((name, camera))
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
report = {'blender': bpy.app.version_string, 'device': args.device, 'quality': args.quality,
          'samples': args.samples, 'resolution': [args.width, args.height],
          'source_file': Path(bpy.data.filepath).name, 'status': 'running', 'views': records}
started = time.perf_counter()


def write_report():
    report['elapsed_seconds'] = round(time.perf_counter()-started, 3)
    temporary = args.output / '.render-report.partial.json'
    temporary.write_text(json.dumps(report, indent=2)+'\n')
    temporary.replace(args.output / 'render-report.json')


write_report()
try:
    for name, camera in view_cameras:
        scene.camera = camera
        target = args.output.resolve() / f'{name.lower()}.png'
        temporary = target.with_name('.'+target.stem+'.partial.png')
        scene.render.filepath = str(temporary)
        view_started = time.perf_counter()
        bpy.ops.render.render(write_still=True)
        temporary.replace(target)
        records.append({'camera': camera.name, 'file': str(target),
                        'elapsed_seconds': round(time.perf_counter()-view_started, 3)})
        write_report()
    report['status'] = 'complete'
except Exception as error:
    report['status'] = 'failed'
    report['error_type'] = type(error).__name__
    write_report()
    raise
write_report()
print('RENDER_VIEWS_OK', json.dumps(report))
