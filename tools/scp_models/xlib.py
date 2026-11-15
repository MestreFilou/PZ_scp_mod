"""Minimal reader/writer for the DirectX .x text files used by the mod (PZ B42).

Only the Mesh block is parsed and rewritten; the skeleton frames, templates and
the dummy AnimationSet are kept verbatim so the file stays what the game already loads.
"""
import re
import numpy as np

NUM = re.compile(r'-?\d+\.?\d*(?:[eE][-+]?\d+)?')


class XFile:
    pass


def _block_end(lines, start):
    depth = 0
    for i in range(start, len(lines)):
        depth += lines[i].count('{') - lines[i].count('}')
        if depth == 0:
            return i
    raise ValueError('unbalanced')


def _nums(text):
    return [float(x) for x in NUM.findall(text)]


def load(path):
    x = XFile()
    lines = open(path).read().split('\n')
    ms = next(i for i, l in enumerate(lines) if re.match(r'^\s*Mesh \S+ \{', l))
    me = _block_end(lines, ms)
    x.prefix = lines[:ms]
    x.suffix = lines[me + 1:]
    x.mesh_name = lines[ms].split()[1]
    x.indent = len(lines[ms]) - len(lines[ms].lstrip())
    body = lines[ms + 1:me]
    # split sub blocks
    subs = {}
    weights = []
    i = 0
    head = []
    while i < len(body):
        m = re.match(r'^\s*(\w+)\s*\w*\s*\{', body[i])
        if m:
            e = _block_end(body, i)
            if m.group(1) == 'SkinWeights':
                weights.append(body[i + 1:e])
            else:
                subs[m.group(1)] = body[i + 1:e]
            i = e + 1
        else:
            head.append(body[i]); i += 1
    v = _nums('\n'.join(head))
    nv = int(v[0])
    x.verts = np.array(v[1:1 + nv * 3]).reshape(nv, 3)
    p = 1 + nv * 3
    nf = int(v[p]); p += 1
    faces = []
    for _ in range(nf):
        n = int(v[p]); faces.append([int(a) for a in v[p + 1:p + 1 + n]]); p += 1 + n
    x.faces = faces
    n = _nums('\n'.join(subs['MeshNormals']))
    nn = int(n[0])
    x.normals = np.array(n[1:1 + nn * 3]).reshape(nn, 3)
    t = _nums('\n'.join(subs['MeshTextureCoords']))
    x.uvs = np.array(t[1:1 + int(t[0]) * 2]).reshape(-1, 2)
    x.material_lines = subs['MeshMaterialList']
    x.weights = {}
    x.offsets = {}
    x.bone_order = []
    for w in weights:
        name = re.search(r'"(.+?)"', w[0]).group(1)
        d = _nums('\n'.join(w[1:]))
        k = int(d[0])
        idx = np.array(d[1:1 + k], dtype=int)
        wt = np.array(d[1 + k:1 + 2 * k])
        x.weights[name] = (idx, wt)
        x.offsets[name] = np.array(d[1 + 2 * k:1 + 2 * k + 16]).reshape(4, 4)
        x.bone_order.append(name)
    # frames
    x.frames = {}   # name -> (parent, local 4x4 row-vector matrix)
    stack = []
    i = 0
    L = x.prefix + [''] * (me - ms + 1) + x.suffix
    for i, l in enumerate(L):
        m = re.match(r'^\s*Frame (\S+) \{', l)
        if m:
            j = i + 1
            while 'FrameTransformMatrix' not in L[j]:
                j += 1
            mat = np.array(_nums(L[j + 1])).reshape(4, 4)
            x.frames[m.group(1)] = (stack[-1][0] if stack else None, mat)
            stack.append((m.group(1), 1))
            continue
        if stack:
            d = l.count('{') - l.count('}')
            if d:
                name, depth = stack[-1]
                depth += d
                if depth == 0:
                    stack.pop()
                else:
                    stack[-1] = (name, depth)
        if l.startswith('AnimTicksPerSecond') or l.startswith('AnimationSet'):
            break
    return x


def world(x, name):
    """World matrix (row-vector convention) of a frame."""
    parent, m = x.frames[name]
    return m if parent is None else m @ world(x, parent)


def weight_matrix(x, bones=None):
    bones = bones or x.bone_order
    W = np.zeros((len(x.verts), len(bones)))
    for b, (idx, wt) in x.weights.items():
        W[idx, bones.index(b)] = wt
    return W


def save(x, path, verts, faces, normals, uvs, W, bones, offsets):
    """W: (nv, nb) weights; offsets: dict bone -> 4x4. Max 4 influences per vertex."""
    ind = ' ' * x.indent
    i1 = ind + ' '
    i2 = i1 + ' '
    o = list(x.prefix)
    o.append(f'{ind}Mesh {x.mesh_name} {{')
    o.append(f'{i1}{len(verts)};')
    o += [f'{i1}{v[0]:.6f};{v[1]:.6f};{v[2]:.6f};,' for v in verts]
    o[-1] = o[-1][:-1] + ';'
    o.append(f'{i1}{len(faces)};')
    fl = [f'{i1}{len(f)};' + ','.join(str(a) for a in f) + ';,' for f in faces]
    fl[-1] = fl[-1][:-1] + ';'
    o += fl
    o.append('')
    o.append(f'{i1}MeshNormals {{')
    o.append(f'{i2}{len(normals)};')
    o += [f'{i2}{v[0]:.6f};{v[1]:.6f};{v[2]:.6f};,' for v in normals]
    o[-1] = o[-1][:-1] + ';'
    o.append(f'{i2}{len(faces)};')
    fl = [f'{i2}{len(f)};' + ','.join(str(a) for a in f) + ';,' for f in faces]
    fl[-1] = fl[-1][:-1] + ';'
    o += fl
    o.append(f'{i1}}}')
    o.append('')
    o.append(f'{i1}MeshMaterialList {{')
    o.append(f'{i2}1;')
    o.append(f'{i2}{len(faces)};')
    o += [f'{i2}0,'] * (len(faces) - 1) + [f'{i2}0;']
    # keep the Material sub block of the original
    o += [l for l in x.material_lines if '{' in l]
    o.append(f'{i1}}}')
    o.append('')
    o.append(f'{i1}MeshTextureCoords c1 {{')
    o.append(f'{i2}{len(uvs)};')
    o += [f'{i2}{v[0]:.6f};{v[1]:.6f};,' for v in uvs]
    o[-1] = o[-1][:-1] + ';'
    o.append(f'{i1}}}')
    used = [b for bi, b in enumerate(bones) if (W[:, bi] > 0).any()]
    if used:
        o.append('')
        o.append(f'{i1}XSkinMeshHeader {{')
        o.append(f'{i2}4;'); o.append(f'{i2}4;'); o.append(f'{i2}{len(used)};')
        o.append(f'{i1}}}')
        for b in used:
            col = W[:, bones.index(b)]
            idx = np.nonzero(col > 0)[0]
            o.append('')
            o.append(f'{i1}SkinWeights {{')
            o.append(f'{i2}"{b}";')
            o.append(f'{i2}{len(idx)};')
            o += [f'{i2}{i},' for i in idx[:-1]] + [f'{i2}{idx[-1]};']
            o += [f'{i2}{col[i]:.6f},' for i in idx[:-1]] + [f'{i2}{col[idx[-1]]:.6f};']
            o.append(i2 + ','.join(f'{a:.6f}' for a in offsets[b].flatten()) + ';;')
            o.append(f'{i1}}}')
    o.append(f'{ind}}}')
    o += x.suffix
    open(path, 'w').write('\n'.join(o))
