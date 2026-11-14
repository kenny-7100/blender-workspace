"""Run with ../../bin/blender --background --python model.py (absolute paths also work)."""
from pathlib import Path
import json
import bpy
from mathutils import Vector

OUT = Path(__file__).resolve().parent
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

def material(name, color, metallic=0.0, roughness=0.4):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = (*color, 1)
    bsdf.inputs['Metallic'].default_value = metallic
    bsdf.inputs['Roughness'].default_value = roughness
    return mat

teal = material('Ocean teal enamel', (0.025, 0.43, 0.48), 0.35)
navy = material('Dark blue joints', (0.025, 0.055, 0.09), 0.4)
yellow = material('Warm yellow details', (1.0, 0.55, 0.10), 0.2)
white = material('Porcelain white', (0.88, 0.94, 0.95), 0.1)
black = material('Face display glass', (0.012, 0.025, 0.045), 0.3, 0.22)
ground = material('Studio floor', (0.10, 0.14, 0.21), 0.05, 0.65)

def finish(obj, name, mat):
    obj.name = name
    obj.data.materials.append(mat)
    for face in obj.data.polygons:
        face.use_smooth = True
    return obj

def box(name, loc, scale, mat, bevel=0.12):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    obj = bpy.context.object
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    finish(obj, name, mat)
    mod = obj.modifiers.new('Rounded edges', 'BEVEL')
    mod.width = bevel
    mod.segments = 4
    obj.modifiers.new('Weighted normals', 'WEIGHTED_NORMAL')
    return obj

def sphere(name, loc, scale, mat):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, location=loc)
    obj = bpy.context.object
    obj.scale = scale
    return finish(obj, name, mat)

def rod(name, start, end, radius, mat):
    a, b = Vector(start), Vector(end)
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=radius, depth=(b-a).length, location=(a+b)/2)
    obj = bpy.context.object
    obj.rotation_euler = (b-a).to_track_quat('Z', 'Y').to_euler()
    return finish(obj, name, mat)

# A static character assembled from editable, named mesh objects; front faces -Y.
box('Torso', (0, 0, 2.05), (1.25, 0.72, 1.12), teal, 0.18)
box('Chest badge', (0, -0.39, 2.12), (0.62, 0.08, 0.40), white, 0.07)
for x in (-0.16, 0, 0.16):
    sphere('Badge indicator', (x, -0.45, 2.12), (0.045, 0.025, 0.065), yellow)
rod('Neck', (0, 0, 2.57), (0, 0, 2.78), 0.20, navy)
box('Head', (0, -0.015, 3.22), (1.50, 0.86, 1.03), teal, 0.22)
box('Face panel', (0, -0.46, 3.24), (1.17, 0.10, 0.63), black, 0.15)
for x in (-0.30, 0.30):
    sphere('Bright eye', (x, -0.525, 3.32), (0.105, 0.035, 0.14), white)
box('Friendly smile', (0, -0.525, 3.06), (0.29, 0.04, 0.045), yellow, 0.018)
rod('Antenna', (0, 0, 3.70), (0, 0, 4.02), 0.045, navy)
sphere('Antenna tip', (0, 0, 4.07), (0.13,)*3, yellow)
for side in (-1, 1):
    sphere('Ear', (side*0.80, 0, 3.22), (0.15, 0.23, 0.23), yellow)
    sphere('Shoulder', (side*0.76, 0, 2.34), (0.22,)*3, navy)
    elbow = (side*1.03, 0, 1.97)
    hand = (side*1.15, -0.13, 1.51)
    rod('Upper arm', (side*0.78, 0, 2.33), elbow, 0.15, teal)
    sphere('Elbow', elbow, (0.17,)*3, navy)
    rod('Forearm', elbow, hand, 0.18, white)
    sphere('Hand', hand, (0.23, 0.22, 0.25), yellow)
    x = side*0.34
    rod('Thigh', (x, 0, 1.54), (x, 0, 1.05), 0.20, navy)
    sphere('Knee', (x, -0.03, 1.03), (0.23,)*3, yellow)
    rod('Shin', (x, 0, 1.00), (x, 0, 0.52), 0.21, teal)
    box('Boot', (x, -0.15, 0.37), (0.55, 0.85, 0.36), white, 0.12)

rod('Display plinth', (0, 0, 0.04), (0, 0, 0.16), 1.65, navy)
box('Floor', (0, 0, -0.08), (200, 200, 0.12), ground, 0.02)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 48
scene.cycles.use_denoising = True
scene.render.resolution_x = 800
scene.render.resolution_y = 800
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.filepath = str(OUT / 'robot.png')
scene.render.film_transparent = False
scene.world.color = (0.22, 0.22, 0.22)
scene.view_settings.view_transform = 'AgX'
scene.render.fps = 24
scene.unit_settings.system = 'METRIC'
scene.render.use_file_extension = True
scene.render.image_settings.color_mode = 'RGBA'
scene.render.image_settings.color_depth = '8'
bpy.context.preferences.filepaths.temporary_directory = str(OUT.parents[1] / 'tmp')

def aim(obj, target):
    obj.rotation_euler = (Vector(target)-obj.location).to_track_quat('-Z', 'Y').to_euler()

bpy.ops.object.camera_add(location=(6, -10, 5.8))
cam = bpy.context.object
cam.name = 'Portrait camera'
cam.data.type = 'ORTHO'
cam.data.ortho_scale = 5.7
aim(cam, (0, 0, 2.0))
scene.camera = cam
for name, location, power, size, color in [
    ('Key softbox', (1, -5, 7), 850, 5, (0.80, 0.91, 1.0)),
    ('Warm fill', (-4, -2, 4), 600, 4, (1.0, 0.76, 0.50)),
    ('Rim light', (3, 4, 6), 1100, 3, (0.5, 0.8, 1.0)),
]:
    bpy.ops.object.light_add(type='AREA', location=location)
    light = bpy.context.object
    light.name = name
    light.data.energy, light.data.shape, light.data.size = power, 'DISK', size
    light.data.color = color
    aim(light, (0, 0, 2))

# Start the saved project in camera view with the character selected.
bpy.ops.object.select_all(action='DESELECT')
bpy.data.objects['Head'].select_set(True)
bpy.context.view_layer.objects.active = bpy.data.objects['Head']
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type == 'VIEW_3D':
            area.spaces.active.region_3d.view_perspective = 'CAMERA'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'robot.blend'))
bpy.ops.render.render(write_still=True)
report = {
    'blender': bpy.app.version_string,
    'python': __import__('sys').version,
    'objects': len(scene.objects),
    'mesh_objects': sum(o.type == 'MESH' for o in scene.objects),
    'render_engine': scene.render.engine,
    'resolution': [scene.render.resolution_x, scene.render.resolution_y],
    'blend': str(OUT / 'robot.blend'),
    'render': str(OUT / 'robot.png'),
}
(OUT / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
print('DEMO_SUCCESS ' + json.dumps(report))
