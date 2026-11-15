"""Common build steps: mesh -> atlas -> texture -> male and female .x files -> previews."""
import os, json, sys
import numpy as np
from PIL import Image
import xlib, core

HERE = os.path.dirname(os.path.abspath(__file__))
MEDIA = os.path.normpath(os.path.join(HERE, '../../Contents/mods/SCPFoundation/42/media'))
SKEL = json.load(open(os.path.join(HERE, 'skeleton.json')))
BOB = {b: np.array(m) for b, m in SKEL['bob'].items()}     # bone -> offset (inverse bind) matrix
KATE = {b: np.array(m) for b, m in SKEL['kate'].items()}
BONES = list(BOB)
OUT = os.environ.get('SCP_PREVIEW_DIR', '/home/user/work/after')


def joint(b, who=BOB):
    return np.linalg.inv(who[b])[3, :3]


def limit_weights(W, n=4):
    W = W.copy()
    idx = np.argsort(-W, axis=1)[:, n:]
    np.put_along_axis(W, idx, 0, axis=1)
    W[W < 0.01] = 0
    W /= W.sum(1, keepdims=True)
    return W


def skin(v, W, pose, src=BOB):
    """Linear blend skinning. pose: bone -> world matrix (row vectors)."""
    vh = np.c_[v, np.ones(len(v))]
    out = np.zeros((len(v), 4))
    for bi, b in enumerate(BONES):
        if (W[:, bi] > 0).any():
            out += W[:, bi:bi + 1] * (vh @ src[b] @ pose[b])
    return out[:, :3]


def to_kate(v, W):
    return skin(v, W, {b: np.linalg.inv(KATE[b]) for b in BONES})


def make(name, f, lo, hi, tris, color_fn, weight_fn, tex, voxel=0.004, res=512, symmetric=True, static=None):
    """static: name of the bone a rigid model is attached to (its vertices are stored in that bone's space)."""
    import render
    render.reset()
    v0, f0 = core.mesh_sdf(f, lo, hi, voxel)
    v1, f1 = core.decimate(v0, f0, tris, symmetric)
    vmap, fc, uv = core.unwrap(v1, f1, res)
    v = v1[vmap]
    nrm = core.vertex_normals(v1, fc, vmap)
    img = core.bake(v, fc, uv, f, color_fn, res)
    tex_path = os.path.join(MEDIA, 'textures/SCP', tex + '.png')
    Image.fromarray(img).save(tex_path, optimize=True)
    if static:
        path = os.path.join(MEDIA, 'models_X', 'static', 'clothes', name + '.x')
        x = xlib.load(path)
        vl = (np.c_[v, np.ones(len(v))] @ BOB[static])[:, :3]
        nl = nrm @ BOB[static][:3, :3]
        nl /= np.linalg.norm(nl, axis=1, keepdims=True)
        xlib.save(x, path, vl, fc.tolist(), nl, uv, np.zeros((len(v), len(BONES))), BONES, BOB)
        print(name, 'hi-res tris', len(f0), '-> tris', len(fc), 'verts', len(v))
        return dict(v=v, fc=fc, uv=uv, nrm=nrm, W=None, tex=tex_path)
    W = limit_weights(weight_fn(v1))[vmap]
    sub = 'skinned'
    for prefix, conv in (('', None), ('kate_', to_kate)):
        path = os.path.join(MEDIA, 'models_X', sub, 'clothes', prefix + name + '.x')
        x = xlib.load(path)
        vv = v if conv is None else conv(v, W)
        nn = nrm if conv is None else core.vertex_normals(conv(v1, W[np.unique(vmap, return_index=True)[1]]), fc, vmap)
        xlib.save(x, path, vv, fc.tolist(), nn, uv, W, BONES, BOB if conv is None else KATE)
    print(name, 'hi-res tris', len(f0), '-> tris', len(fc), 'verts', len(v))
    return dict(v=v, fc=fc, uv=uv, nrm=nrm, W=W, tex=tex_path)


def preview(name, m, poses=None, height=1.25, center=(0, 0, 0.5), views=None):
    import render
    os.makedirs(OUT, exist_ok=True)
    render.reset(); render.setup_lights()
    for k, mm in enumerate(m if isinstance(m, list) else [m]):
        render.add_mesh(name + str(k), mm['v'], mm['fc'].tolist(), mm['uv'], mm['tex'], normals=mm['nrm'])
    p = render.render_views(os.path.join(OUT, name), views or render.VIEWS, center=center, height=height)
    render.sheet(p, os.path.join(OUT, name + '.png'))


PARENT = {'Bip01_Spine': 'Bip01_Pelvis', 'Bip01_Spine1': 'Bip01_Spine', 'Bip01_Neck': 'Bip01_Spine1', 'Bip01_Head': 'Bip01_Neck',
          'Bip01_DressFront': 'Bip01_Pelvis', 'Bip01_DressBack': 'Bip01_Pelvis',
          'Bip01_DressFront02': 'Bip01_DressFront', 'Bip01_DressBack02': 'Bip01_DressBack'}
for _s in 'LR':
    _p = f'Bip01_{_s}_'
    PARENT.update({_p + 'Clavicle': 'Bip01_Neck', _p + 'UpperArm': _p + 'Clavicle', _p + 'Forearm': _p + 'UpperArm',
                   _p + 'Hand': _p + 'Forearm', _p + 'Finger0': _p + 'Hand', _p + 'Finger1': _p + 'Hand',
                   _p + 'Thigh': 'Bip01_Pelvis', _p + 'Calf': _p + 'Thigh', _p + 'Foot': _p + 'Calf'})


def _rotm(j, axis, deg):
    a = np.radians(deg)
    i, k = [(1, 2), (2, 0), (0, 1)]['xyz'.index(axis)]
    R = np.eye(4)
    R[i, i] = R[k, k] = np.cos(a); R[i, k] = np.sin(a); R[k, i] = -np.sin(a)
    T0 = np.eye(4); T0[3, :3] = -j
    T1 = np.eye(4); T1[3, :3] = j
    return T0 @ R @ T1


def pose_mesh(v, W, rots):
    """rots: bone -> list of (axis, degrees) about the bone's joint, world axes of the bind pose."""
    delta = {}

    def get(b):
        if b not in delta:
            m = np.eye(4)
            for axis, deg in rots.get(b, []):
                m = m @ _rotm(joint(b), axis, deg)
            delta[b] = m @ get(PARENT[b]) if b in PARENT else m
        return delta[b]
    vh = np.c_[v, np.ones(len(v))]
    out = np.zeros((len(v), 4))
    for bi, b in enumerate(BONES):
        if (W[:, bi] > 0).any():
            out += W[:, bi:bi + 1] * (vh @ get(b))
    return out[:, :3]


# arms down from the T-pose, mid-stride, one arm reaching: a quick check that the skinning holds
WALK = {'Bip01_L_UpperArm': [('z', -70), ('x', -55)], 'Bip01_R_UpperArm': [('z', 75)],
        'Bip01_L_Forearm': [('x', -35)], 'Bip01_R_Forearm': [('x', -20)],
        'Bip01_L_Thigh': [('x', -35)], 'Bip01_L_Calf': [('x', 40)], 'Bip01_R_Thigh': [('x', 22)], 'Bip01_R_Calf': [('x', 15)],
        'Bip01_Spine': [('x', -8)], 'Bip01_Spine1': [('x', -8)], 'Bip01_Head': [('y', 25), ('x', 10)]}


def preview_pose(name, m, rots=WALK, height=1.25, center=(0, 0, 0.5), views=None):
    import render
    render.reset(); render.setup_lights()
    for k, mm in enumerate(m if isinstance(m, list) else [m]):
        W = mm['W']
        if isinstance(W, str):          # rigid model attached to one bone
            W = np.zeros((len(mm['v']), len(BONES))); W[:, BONES.index(mm['W'])] = 1
        render.add_mesh(name + str(k), pose_mesh(mm['v'], W, rots), mm['fc'].tolist(), mm['uv'], mm['tex'])
    p = render.render_views(os.path.join(OUT, name + '_pose'), views or [('front', 0, 5), ('iso', 40, 30), ('side', 90, 5), ('back', 215, 25)], center=center, height=height)
    render.sheet(p, os.path.join(OUT, name + '_pose.png'))


def quick(name, f, lo, hi, voxel=0.005, height=1.25, center=(0, 0, 0.5), views=None):
    """Fast clay render of the detailed shape, to iterate on the silhouette."""
    import render
    render.reset(); render.setup_lights()
    v, fc = core.mesh_sdf(f, lo, hi, voxel)
    os.makedirs(OUT, exist_ok=True)
    render.add_mesh(name, v, fc.tolist(), np.zeros((len(v), 2)), None, smooth=True)
    p = render.render_views(os.path.join(OUT, name + '_clay'), views or [('front', 0, 5), ('iso', 40, 30), ('side', 90, 5)], center=center, height=height)
    render.sheet(p, os.path.join(OUT, name + '_clay.png'))
