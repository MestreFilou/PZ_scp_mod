"""Preview renders (Cycles, CPU) of a mesh given as numpy arrays in .x space (y up)."""
import bpy, math, os
import numpy as np
from mathutils import Vector


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.samples = 24
    sc.cycles.use_denoising = False
    sc.cycles.device = 'CPU'
    sc.render.film_transparent = False
    sc.view_settings.view_transform = 'Standard'
    w = bpy.data.worlds.new('w'); sc.world = w
    w.use_nodes = True
    w.node_tree.nodes['Background'].inputs[0].default_value = (0.32, 0.34, 0.38, 1)
    w.node_tree.nodes['Background'].inputs[1].default_value = 0.9
    return sc


def to_bl(v):
    v = np.asarray(v)
    return np.stack([-v[:, 0], v[:, 2], v[:, 1]], 1)


def add_mesh(name, verts, faces, uvs, tex_path, flip=False, smooth=True, normals=None):
    me = bpy.data.meshes.new(name)
    f = [list(reversed(x)) for x in faces] if flip else faces
    me.from_pydata(to_bl(verts).tolist(), [], f)
    uvl = me.uv_layers.new(name='uv')
    for poly in me.polygons:
        for li in poly.loop_indices:
            vi = me.loops[li].vertex_index
            uvl.data[li].uv = (uvs[vi][0], 1 - uvs[vi][1])
        poly.use_smooth = smooth
    if normals is not None:
        me.normals_split_custom_set_from_vertices(to_bl(normals).tolist())
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes['Principled BSDF']
    bsdf.inputs['Roughness'].default_value = 0.9
    bsdf.inputs['Specular IOR Level'].default_value = 0.1
    if tex_path:
        img = bpy.data.images.load(tex_path)
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = img
        t.interpolation = 'Closest'
        nt.links.new(t.outputs['Color'], bsdf.inputs['Base Color'])
    me.materials.append(mat)
    return ob


def setup_lights():
    for n, (rx, rz, e) in {'key': (50, 35, 3.0), 'fill': (60, -120, 1.2), 'rim': (70, 160, 1.5)}.items():
        l = bpy.data.lights.new(n, 'SUN'); l.energy = e; l.angle = 0.3
        o = bpy.data.objects.new(n, l); bpy.context.scene.collection.objects.link(o)
        o.rotation_euler = (math.radians(rx), 0, math.radians(rz))
    bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0, 0))
    g = bpy.context.object
    m = bpy.data.materials.new('g'); m.use_nodes = True
    m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.25, 0.26, 0.28, 1)
    m.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 1
    g.data.materials.append(m)


def render_views(out, views, center=(0, 0, 0.5), height=1.25, res=(520, 720)):
    """views: list of (name, azimuth_deg, elevation_deg). az 0 = front (camera on -Y side)."""
    sc = bpy.context.scene
    cam = bpy.data.cameras.new('c'); cam.type = 'ORTHO'; cam.ortho_scale = height
    co = bpy.data.objects.new('c', cam); sc.collection.objects.link(co); sc.camera = co
    sc.render.resolution_x, sc.render.resolution_y = res
    paths = []
    for name, az, el in views:
        a, e = math.radians(az), math.radians(el)
        d = Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))
        co.location = Vector(center) + d * 6
        co.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
        p = f'{out}_{name}.png'
        sc.render.filepath = p
        bpy.ops.render.render(write_still=True)
        paths.append(p)
    return paths


def sheet(paths, out, label=None):
    from PIL import Image, ImageDraw
    ims = [Image.open(p).convert('RGB') for p in paths]
    W = sum(i.width for i in ims); H = max(i.height for i in ims)
    s = Image.new('RGB', (W, H))
    x = 0
    for i in ims:
        s.paste(i, (x, 0)); x += i.width
    if label:
        ImageDraw.Draw(s).text((8, 6), label, fill=(255, 255, 255))
    s.save(out)
    for p in paths:
        os.remove(p)


VIEWS = [('front', 0, 5), ('iso', 40, 30), ('side', 90, 5), ('back', 180, 5)]
