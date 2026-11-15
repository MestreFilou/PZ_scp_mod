"""Toolkit used to build the SCP creature models.

Shapes are signed distance fields (numpy), meshed with marching cubes, decimated in
Blender, unwrapped with xatlas; the texture is painted per texel from the 3D position
on the detailed surface (so the low-poly mesh keeps the fine detail as paint).
Space is the game's .x space: x = character's left, y = up, z = backwards (front is -z).
"""
import numpy as np
from skimage import measure
from scipy import ndimage
import xatlas

# ---------------------------------------------------------------- sdf primitives

def V(x, y, fwd=0.0):
    """Point from (left, up, forward)."""
    return np.array([x, y, -fwd], float)


def sphere(p, c, r):
    return np.linalg.norm(p - c, axis=1) - r


def ellipsoid(p, c, r):
    r = np.asarray(r, float)
    q = (p - c) / r
    k0 = np.linalg.norm(q, axis=1)
    k1 = np.linalg.norm(q / r, axis=1)
    return np.where(k1 > 1e-9, k0 * (k0 - 1.0) / np.maximum(k1, 1e-9), -r.min())


def cone(p, a, b, ra, rb):
    """Capsule from a to b whose radius goes from ra to rb."""
    ab = b - a
    t = np.clip(((p - a) @ ab) / (ab @ ab), 0, 1)
    c = a + t[:, None] * ab
    return np.linalg.norm(p - c, axis=1) - (ra + (rb - ra) * t)


def chain(p, pts, radii, k=0.0):
    d = None
    for i in range(len(pts) - 1):
        c = cone(p, pts[i], pts[i + 1], radii[i], radii[i + 1])
        d = c if d is None else (smin(d, c, k) if k else np.minimum(d, c))
    return d


def box(p, c, h, r=0.0):
    q = np.abs(p - c) - (np.asarray(h) - r)
    return np.linalg.norm(np.maximum(q, 0), axis=1) + np.minimum(q.max(1), 0) - r


def rot(p, c, axis, deg):
    """Rotate query points around c (inverse transform of the shape)."""
    a = np.radians(-deg)
    q = p - c
    i, j = [(1, 2), (2, 0), (0, 1)]['xyz'.index(axis)]
    o = q.copy()
    o[:, i] = q[:, i] * np.cos(a) - q[:, j] * np.sin(a)
    o[:, j] = q[:, i] * np.sin(a) + q[:, j] * np.cos(a)
    return o + c


def smin(a, b, k):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1)
    return b + (a - b) * h - k * h * (1 - h)


def smax(a, b, k):
    return -smin(-a, -b, k)


def mirror(p):
    q = p.copy(); q[:, 0] = np.abs(q[:, 0]); return q

# ---------------------------------------------------------------- noise

def _hash(i):
    i = (i ^ 61) ^ (i >> 16); i = i + (i << 3); i = i ^ (i >> 4)
    i = i * 0x27d4eb2d; i = i ^ (i >> 15)
    return (i & 0xffffff) / float(0xffffff)


def vnoise(p, scale, seed=0):
    q = p * scale
    i = np.floor(q).astype(np.int64); f = q - i
    f = f * f * (3 - 2 * f)
    out = 0
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                h = _hash(((i[:, 0] + dx) * 73856093) ^ ((i[:, 1] + dy) * 19349663) ^ ((i[:, 2] + dz) * 83492791) ^ (seed * 2654435761 & 0xffffffff))
                w = (f[:, 0] if dx else 1 - f[:, 0]) * (f[:, 1] if dy else 1 - f[:, 1]) * (f[:, 2] if dz else 1 - f[:, 2])
                out = out + h * w
    return out


def fbm(p, scale, octaves=4, seed=0, gain=0.5):
    a, s, o, n = 1.0, scale, 0.0, 0.0
    for k in range(octaves):
        o = o + a * vnoise(p, s, seed + k); n += a; a *= gain; s *= 2.03
    return o / n


def worley(p, scale, seed=0):
    """Returns (f1, f2) distances to the nearest cell points."""
    q = p * scale
    i = np.floor(q).astype(np.int64)
    d1 = np.full(len(p), 9.0); d2 = np.full(len(p), 9.0)
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for dz in (-1, 0, 1):
                c = i + np.array([dx, dy, dz])
                k = (c[:, 0] * 73856093) ^ (c[:, 1] * 19349663) ^ (c[:, 2] * 83492791) ^ (seed * 2654435761 & 0xffffffff)
                pt = c + np.stack([_hash(k), _hash(k + 1013), _hash(k + 7919)], 1)
                d = np.linalg.norm(q - pt, axis=1)
                d2 = np.where(d < d1, d1, np.minimum(d2, d)); d1 = np.minimum(d1, d)
    return d1, d2

# ---------------------------------------------------------------- meshing

def mesh_sdf(f, lo, hi, voxel=0.005):
    lo = np.asarray(lo, float); hi = np.asarray(hi, float)
    n = np.ceil((hi - lo) / voxel).astype(int) + 1
    xs = [lo[i] + voxel * np.arange(n[i]) for i in range(3)]
    vol = np.empty(n, np.float32)
    yz = np.stack(np.meshgrid(xs[1], xs[2], indexing='ij'), -1).reshape(-1, 2)
    for i, x in enumerate(xs[0]):
        p = np.c_[np.full(len(yz), x), yz]
        d = f(p, False)
        near = np.abs(d) < 0.03          # fine detail only matters close to the surface
        if near.any():
            d[near] = f(p[near])
        vol[i] = d.reshape(n[1], n[2])
    v, fc, _, _ = measure.marching_cubes(vol, 0.0, spacing=(voxel,) * 3)
    v = v + lo
    # orient outward (gradient points outward)
    a, b, c = v[fc[:, 0]], v[fc[:, 1]], v[fc[:, 2]]
    nrm = np.cross(b - a, c - a)
    ctr = (a + b + c) / 3
    g = grad(f, ctr[:2000])
    if (np.einsum('ij,ij->i', nrm[:2000], g) < 0).mean() > 0.5:
        fc = fc[:, ::-1]
    return v, fc


def grad(f, p, e=0.0015):
    g = np.empty_like(p)
    for i in range(3):
        d = np.zeros(3); d[i] = e
        g[:, i] = f(p + d) - f(p - d)
    n = np.linalg.norm(g, axis=1, keepdims=True)
    return g / np.maximum(n, 1e-12)


def decimate(v, fc, target_tris, symmetric=True):
    import bpy
    me = bpy.data.meshes.new('tmp')
    me.from_pydata(v.tolist(), [], fc.tolist())
    ob = bpy.data.objects.new('tmp', me)
    bpy.context.scene.collection.objects.link(ob)
    m = ob.modifiers.new('d', 'DECIMATE')
    m.ratio = min(1.0, target_tris / len(fc))
    m.use_symmetry = symmetric; m.symmetry_axis = 'X'
    m.use_collapse_triangulate = True
    dg = bpy.context.evaluated_depsgraph_get()
    em = ob.evaluated_get(dg).to_mesh()
    nv = np.array([x.co[:] for x in em.vertices])
    nf = np.array([p.vertices[:] for p in em.polygons if len(p.vertices) == 3])
    bpy.data.objects.remove(ob); bpy.data.meshes.remove(me)
    return nv, nf


def unwrap(v, fc, res=512, padding=4):
    atlas = xatlas.Atlas()
    atlas.add_mesh(v.astype(np.float32), fc.astype(np.uint32))
    co = xatlas.ChartOptions(); co.max_iterations = 2; co.max_cost = 6.0; co.normal_seam_weight = 2.0
    po = xatlas.PackOptions(); po.resolution = res; po.padding = padding; po.bruteForce = True; po.create_image = False
    atlas.generate(chart_options=co, pack_options=po)
    vmap, idx, uv = atlas[0]
    return vmap, idx.astype(int), uv


def vertex_normals(v, fc, vmap=None):
    """Smooth normals; with vmap (split verts -> original) normals stay continuous over UV seams."""
    base = v
    f = fc if vmap is None else vmap[fc]
    n = np.zeros((int(f.max()) + 1, 3))
    a, b, c = base[f[:, 0]], base[f[:, 1]], base[f[:, 2]]
    fn = np.cross(b - a, c - a)
    for k in range(3):
        np.add.at(n, f[:, k], fn)
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
    return n if vmap is None else n[vmap]

# ---------------------------------------------------------------- texture bake

def bake(v, fc, uv, f, color_fn, res=512, project=True, ss=2):
    """Paint the texture: color_fn(P, N, ao) -> rgb in 0..1. v/fc/uv are the split (atlas) mesh."""
    R = res * ss
    pos = np.zeros((R, R, 3)); mask = np.zeros((R, R), bool)
    px = uv * R
    for t in fc:
        a, b, c = px[t]
        x0, y0 = np.floor(np.minimum(np.minimum(a, b), c) - 1).astype(int)
        x1, y1 = np.ceil(np.maximum(np.maximum(a, b), c) + 1).astype(int)
        x0, y0 = max(x0, 0), max(y0, 0); x1, y1 = min(x1, R - 1), min(y1, R - 1)
        if x1 < x0 or y1 < y0:
            continue
        gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        den = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(den) < 1e-12:
            continue
        w0 = ((b[1] - c[1]) * (gx - c[0]) + (c[0] - b[0]) * (gy - c[1])) / den
        w1 = ((c[1] - a[1]) * (gx - c[0]) + (a[0] - c[0]) * (gy - c[1])) / den
        w2 = 1 - w0 - w1
        e = -0.6 / max(np.sqrt(abs(den)), 1e-6)
        ins = (w0 >= e) & (w1 >= e) & (w2 >= e)
        if not ins.any():
            continue
        P = w0[..., None] * v[t[0]] + w1[..., None] * v[t[1]] + w2[..., None] * v[t[2]]
        sub_m = mask[y0:y1 + 1, x0:x1 + 1]
        strict = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
        wr = ins & (strict | ~sub_m)
        pos[y0:y1 + 1, x0:x1 + 1][wr] = P[wr]
        sub_m |= ins
    P = pos[mask]
    if project:
        for _ in range(3):
            P = P - f(P)[:, None] * grad(f, P)
    N = grad(f, P)
    ao = np.zeros(len(P))
    for d in (0.008, 0.02, 0.05):
        ao += np.clip(f(P + N * d) / d, 0, 1)
    ao /= 3
    col = np.zeros((R, R, 3))
    col[mask] = np.clip(color_fn(P, N, ao), 0, 1)
    # fill empty texels with the nearest painted one, then downsample
    idx = ndimage.distance_transform_edt(~mask, return_distances=False, return_indices=True)
    col = col[idx[0], idx[1]]
    col = col.reshape(res, ss, res, ss, 3).mean((1, 3))
    return (col * 255 + 0.5).astype(np.uint8)


def mix(a, b, t):
    t = np.clip(t, 0, 1)
    if np.ndim(t) == 1:
        t = t[:, None]
    return np.asarray(a) * (1 - t) + np.asarray(b) * t


def sstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def rgb(h):
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)]) / 255.0
