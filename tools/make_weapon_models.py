"""Low-poly models of the Foundation's own weapons, drawn here (no source art).

    python3 tools/make_weapon_models.py          # models + textures + icons
    python3 tools/make_weapon_models.py preview  # also renders previews

Each weapon is built from boxes and cylinders. Every part takes its colour
from a swatch of a small texture atlas (one atlas per weapon). Output:
  media/models_X/static/weapons/<name>.x      (text DirectX, like scp_nvg.x)
  media/textures/weapons/<name>.png            (atlas)
  media/textures/Item_<name>.png               (32x32 inventory icon)

Axes in the files are the game's own (checked on its weapon models): the
long side runs along +Y, the top is +Z, the hand grip is at the origin
(the bottom of the handle for long melee weapons).
"""

import math
import os
import random
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEDIA = os.path.join(ROOT, "Contents/mods/SCPFoundation/42/media")
OUT_MESH = os.path.join(MEDIA, "models_X/static/weapons")
OUT_TEX = os.path.join(MEDIA, "textures/weapons")
OUT_ICON = os.path.join(MEDIA, "textures")
PREVIEW = os.path.join(ROOT, "tools/out")

ATLAS = 128      # texture size
CELL = 32        # swatch size (4x4 swatches)

# Built in "design space": x = right, y = along the weapon (forward / up the
# shaft), z = top of the weapon. to_file() turns it into the game's axes.
AXIS_LONG = "y"


class Mesh:
    def __init__(self):
        self.faces = []          # (verts[3|4], swatch, uvs)

    def quad(self, vs, sw, uv=None, centre=None):
        """Add a face; with centre, turn it to face away from that point."""
        if centre is not None:
            mid = np.mean(vs, axis=0)
            if np.dot(normal(vs), mid - np.array(centre, dtype=float)) < 0:
                vs = vs[::-1]
                if uv:
                    uv = uv[::-1]
        self.faces.append((vs, sw, uv))

    def box(self, c, size, sw, rot=None):
        cx, cy, cz = c
        sx, sy, sz = (s / 2 for s in size)
        p = [np.array([cx + dx * sx, cy + dy * sy, cz + dz * sz])
             for dx in (-1, 1) for dy in (-1, 1) for dz in (-1, 1)]
        if rot is not None:
            p = [rot(v) for v in p]
        i = lambda dx, dy, dz: p[(dx > 0) * 4 + (dy > 0) * 2 + (dz > 0)]
        quads = [
            [i(-1, -1, 1), i(1, -1, 1), i(1, 1, 1), i(-1, 1, 1)],      # top
            [i(-1, 1, -1), i(1, 1, -1), i(1, -1, -1), i(-1, -1, -1)],  # bottom
            [i(1, -1, -1), i(1, 1, -1), i(1, 1, 1), i(1, -1, 1)],      # right
            [i(-1, -1, 1), i(-1, 1, 1), i(-1, 1, -1), i(-1, -1, -1)],  # left
            [i(-1, 1, -1), i(-1, 1, 1), i(1, 1, 1), i(1, 1, -1)],      # front
            [i(1, -1, -1), i(1, -1, 1), i(-1, -1, 1), i(-1, -1, -1)],  # back
        ]
        ctr = np.mean(p, axis=0)
        for q in quads:
            self.quad(q, sw, centre=ctr)

    def cyl(self, c, r, length, sw, axis="y", n=8, r2=None, cap=True, sw_cap=None):
        """Cylinder (or cone when r2 is given) centred on c along axis."""
        r2 = r if r2 is None else r2
        ax = "xyz".index(axis)
        a, b = [k for k in range(3) if k != ax]
        def pt(t, ang, rad):
            v = np.array(c, dtype=float)
            v[ax] += t * length / 2
            v[a] += math.cos(ang) * rad
            v[b] += math.sin(ang) * rad
            return v
        for k in range(n):
            a0, a1 = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
            q = [pt(-1, a0, r), pt(-1, a1, r), pt(1, a1, r2), pt(1, a0, r2)]
            u0, u1 = k / n, (k + 1) / n
            self.quad(q, sw, [(u0, 1), (u1, 1), (u1, 0), (u0, 0)], centre=c)
        if cap:
            for t, rad in ((-1, r), (1, r2)):
                ring = [pt(t, 2 * math.pi * k / n, rad) for k in range(n)]
                ctr = pt(t, 0, 0)
                for k in range(n):
                    self.quad([ctr, ring[k], ring[(k + 1) % n]], sw_cap or sw, centre=c)


def normal(vs):
    n = np.cross(vs[1] - vs[0], vs[2] - vs[0])
    l = np.linalg.norm(n)
    return n / l if l > 1e-12 else np.array([0, 0, 1.0])


def swatch_uv(sw, u, v):
    col, row = sw % 4, sw // 4
    m = 2 / ATLAS     # keep off the swatch edges
    s = CELL / ATLAS
    return (col * s + m + u * (s - 2 * m), row * s + m + v * (s - 2 * m))


def face_uvs(vs, uv):
    if uv:
        return uv
    if len(vs) == 3:
        return [(0.5, 0.5), (1, 1), (0, 1)]
    return [(0, 1), (1, 1), (1, 0), (0, 0)]


def to_file(v):
    """Design space -> file space (see AXIS_LONG)."""
    x, y, z = v
    if AXIS_LONG == "y":
        return (x, y, z)
    if AXIS_LONG == "z":
        return (x, -z, y)
    return (y, -x, z)     # "x"


# The game's handgun model (M9) is upside down compared with its rifles:
# top towards -Z. Ours follow it, turned half a turn around the long axis.
UPSIDE_DOWN = {"SCP_SecPistol"}


def write_x(mesh, name, tex):
    verts, norms, uvs, faces, nfaces, mats = [], [], [], [], [], []
    flip = name in UPSIDE_DOWN
    for vs, sw, uv in mesh.faces:
        if flip:
            vs = [np.array([-v[0], v[1], -v[2]]) for v in vs]
        n = normal(vs)
        base = len(verts)
        for p, (u, w) in zip(vs, face_uvs(vs, uv)):
            verts.append(to_file(p))
            uvs.append(swatch_uv(sw, u, w))
        norms.append(to_file(n))
        idx = list(range(base, base + len(vs)))
        # same order as the mod's other .x models: counter-clockwise around the normal
        faces.append(idx)
        nfaces.append([len(norms) - 1] * len(vs))
        mats.append(0)

    f = lambda a: ";".join(f"{c:.6f}" for c in a) + ";"
    L = []
    L.append("xof 0303txt 0032\n")
    L.append("""template Frame {
 <3d82ab46-62da-11cf-ab39-0020af71e433>
 [...]
}
template Matrix4x4 {
 <f6f23f45-7686-11cf-8f52-0040333594a3>
 array FLOAT matrix[16];
}
template FrameTransformMatrix {
 <f6f23f41-7686-11cf-8f52-0040333594a3>
 Matrix4x4 frameMatrix;
}
template Vector {
 <3d82ab5e-62da-11cf-ab39-0020af71e433>
 FLOAT x;
 FLOAT y;
 FLOAT z;
}
template MeshFace {
 <3d82ab5f-62da-11cf-ab39-0020af71e433>
 DWORD nFaceVertexIndices;
 array DWORD faceVertexIndices[nFaceVertexIndices];
}
template Mesh {
 <3d82ab44-62da-11cf-ab39-0020af71e433>
 DWORD nVertices;
 array Vector vertices[nVertices];
 DWORD nFaces;
 array MeshFace faces[nFaces];
 [...]
}
template MeshNormals {
 <f6f23f43-7686-11cf-8f52-0040333594a3>
 DWORD nNormals;
 array Vector normals[nNormals];
 DWORD nFaceNormals;
 array MeshFace faceNormals[nFaceNormals];
}
template Coords2d {
 <f6f23f44-7686-11cf-8f52-0040333594a3>
 FLOAT u;
 FLOAT v;
}
template MeshTextureCoords {
 <f6f23f40-7686-11cf-8f52-0040333594a3>
 DWORD nTextureCoords;
 array Coords2d textureCoords[nTextureCoords];
}
template ColorRGBA {
 <35ff44e0-6c7c-11cf-8f52-0040333594a3>
 FLOAT red;
 FLOAT green;
 FLOAT blue;
 FLOAT alpha;
}
template ColorRGB {
 <d3e16e81-7835-11cf-8f52-0040333594a3>
 FLOAT red;
 FLOAT green;
 FLOAT blue;
}
template Material {
 <3d82ab4d-62da-11cf-ab39-0020af71e433>
 ColorRGBA faceColor;
 FLOAT power;
 ColorRGB specularColor;
 ColorRGB emissiveColor;
 [...]
}
template TextureFilename {
 <a42790e1-7810-11cf-8f52-0040333594a3>
 STRING filename;
}
template MeshMaterialList {
 <f6f23f42-7686-11cf-8f52-0040333594a3>
 DWORD nMaterials;
 DWORD nFaceIndexes;
 array DWORD faceIndexes[nFaceIndexes];
 [Material <3d82ab4d-62da-11cf-ab39-0020af71e433>]
}
""")
    L.append(f"""Material Mat0 {{
 1.000000;1.000000;1.000000;1.000000;;
 0.000000;
 0.000000;0.000000;0.000000;;
 0.000000;0.000000;0.000000;;
 TextureFilename {{
  "{tex}.png";
 }}
}}
""")
    ident = "1.000000,0.000000,0.000000,0.000000,0.000000,1.000000,0.000000,0.000000,0.000000,0.000000,1.000000,0.000000,0.000000,0.000000,0.000000,1.000000;;"
    L.append(f"Frame Dummy {{\n FrameTransformMatrix {{\n  {ident}\n }}\n\n Frame {name} {{\n  FrameTransformMatrix {{\n   {ident}\n  }}\n\n  Mesh {name} {{\n")
    L.append(f"   {len(verts)};\n")
    L.append(",\n".join("   " + f(v) for v in verts) + ";\n")
    L.append(f"   {len(faces)};\n")
    L.append(",\n".join(f"   {len(fc)};" + ",".join(map(str, fc)) + ";" for fc in faces) + ";\n")
    L.append(f"\n   MeshNormals {{\n    {len(norms)};\n")
    L.append(",\n".join("    " + f(v) for v in norms) + ";\n")
    L.append(f"    {len(nfaces)};\n")
    L.append(",\n".join(f"    {len(fc)};" + ",".join(map(str, fc)) + ";" for fc in nfaces) + ";\n   }\n")
    L.append(f"\n   MeshMaterialList {{\n    1;\n    {len(mats)};\n")
    L.append(",\n".join(f"    {m}" for m in mats) + ";\n    { Mat0 }\n   }\n")
    L.append(f"\n   MeshTextureCoords c1 {{\n    {len(uvs)};\n")
    L.append(",\n".join(f"    {u:.6f};{w:.6f};" for u, w in uvs) + ";\n   }\n")
    L.append("  }\n }\n}\n")
    os.makedirs(OUT_MESH, exist_ok=True)
    with open(os.path.join(OUT_MESH, name + ".x"), "w", newline="\n") as fh:
        fh.write("".join(L))
    return len(verts), len(faces)


# ----------------------------------------------------------------------
# Texture atlas
# ----------------------------------------------------------------------

def noise_fill(d, x0, y0, rgb, amount=10, seed=0):
    rnd = random.Random(seed)
    for y in range(y0, y0 + CELL):
        for x in range(x0, x0 + CELL):
            k = rnd.randint(-amount, amount)
            d.point((x, y), tuple(max(0, min(255, c + k)) for c in rgb) + (255,))


def make_atlas(swatches, name):
    """swatches: list of (kind, rgb[, rgb2]) in swatch order (max 16)."""
    img = Image.new("RGBA", (ATLAS, ATLAS), (0, 0, 0, 255))
    for k, sw in enumerate(swatches):
        kind, rgb = sw[0], sw[1]
        # each swatch is drawn on its own tile so nothing spills on the next one
        tile = Image.new("RGBA", (CELL, CELL), (0, 0, 0, 255))
        d = ImageDraw.Draw(tile)
        x0 = y0 = 0
        noise_fill(d, x0, y0, rgb, 6 if kind != "glow" else 2, seed=k)
        if kind == "hazard":
            for i in range(-CELL, CELL, 8):
                d.polygon([(x0 + i, y0 + CELL), (x0 + i + 4, y0 + CELL), (x0 + i + 4 + CELL, y0), (x0 + i + CELL, y0)],
                          fill=sw[2] + (255,))
        elif kind == "grip":
            for y in range(y0, y0 + CELL, 4):
                d.line([(x0, y), (x0 + CELL, y + 2)], fill=sw[2] + (255,), width=1)
        elif kind == "glow":
            for y in range(y0, y0 + CELL):
                t = abs((y - y0) / CELL - 0.5) * 2
                c = tuple(int(a + (b - a) * t) for a, b in zip((235, 250, 255), rgb))
                d.line([(x0, y), (x0 + CELL - 1, y)], fill=c + (255,))
        elif kind == "metal":
            for y in range(y0, y0 + CELL, 3):
                d.line([(x0, y), (x0 + CELL - 1, y)], fill=tuple(min(255, c + 12) for c in rgb) + (255,))
        elif kind == "panel":
            d.rectangle([x0 + 3, y0 + 3, x0 + CELL - 4, y0 + CELL - 4], outline=sw[2] + (255,))
        elif kind == "logo":
            cx, cy = x0 + CELL // 2, y0 + CELL // 2
            d.ellipse([cx - 11, cy - 11, cx + 11, cy + 11], outline=sw[2] + (255,), width=2)
            d.ellipse([cx - 4, cy - 4, cx + 4, cy + 4], outline=sw[2] + (255,), width=2)
            for a in (90, 210, 330):
                ra = math.radians(a)
                d.line([(cx + math.cos(ra) * 5, cy - math.sin(ra) * 5), (cx + math.cos(ra) * 14, cy - math.sin(ra) * 14)],
                       fill=sw[2] + (255,), width=3)
        img.paste(tile, ((k % 4) * CELL, (k // 4) * CELL))
    os.makedirs(OUT_TEX, exist_ok=True)
    img.save(os.path.join(OUT_TEX, name + ".png"))
    return img


# ----------------------------------------------------------------------
# The weapons (sizes in metres, design space)
# ----------------------------------------------------------------------

def shock_maul():
    """SCP_ShockMaul: two-handed electric maul of the containment teams."""
    m = Mesh()
    S = dict(shaft=0, grip=1, steel=2, hazard=3, coil=4, dark=5, logo=6, cap=7)
    # shaft: from the pommel (y=-0.30) to the head (y=0.78); hands at 0 and +0.28
    m.cyl((0, 0.24, 0), 0.018, 1.08, S["shaft"], n=8)
    m.cyl((0, -0.06, 0), 0.023, 0.42, S["grip"], n=8)                 # rubber grip
    m.cyl((0, -0.31, 0), 0.032, 0.05, S["steel"], n=8)                # pommel
    m.box((0, -0.27, 0), (0.04, 0.03, 0.04), S["dark"])
    m.cyl((0, 0.18, 0), 0.026, 0.06, S["steel"], n=8)                 # guard ring
    # battery pack on the shaft
    m.box((0, 0.42, -0.028), (0.045, 0.16, 0.03), S["dark"])
    m.box((0, 0.42, -0.046), (0.035, 0.12, 0.008), S["coil"])         # charge strip
    # head: heavy block with hazard bands and a logo plate
    m.box((0, 0.86, 0), (0.30, 0.17, 0.13), S["steel"])
    for dx in (-0.09, 0.09):
        m.box((dx, 0.86, 0), (0.035, 0.175, 0.135), S["hazard"])
    m.box((0, 0.86, 0.066), (0.10, 0.10, 0.004), S["logo"])
    m.box((0, 0.86, -0.066), (0.10, 0.10, 0.004), S["logo"])
    m.box((0, 0.765, 0), (0.13, 0.03, 0.09), S["dark"])                 # collar
    for dz in (-0.03, 0.03):                                            # cables from the battery
        m.box((0.0, 0.66, dz), (0.012, 0.18, 0.012), S["dark"])
    # striking faces: a coil emitter at each end of the head
    for side in (-1, 1):
        m.cyl((side * 0.175, 0.86, 0), 0.065, 0.05, S["dark"], axis="x", n=12)
        m.cyl((side * 0.21, 0.86, 0), 0.055, 0.03, S["coil"], axis="x", n=12, sw_cap=S["coil"])
        for dz in (-0.035, 0.035):                                      # electrode prongs
            m.cyl((side * 0.24, 0.86, dz), 0.008, 0.05, S["cap"], axis="x", n=6)
    # top spike
    m.cyl((0, 0.97, 0), 0.025, 0.06, S["dark"], n=8, r2=0.012)
    m.cyl((0, 1.01, 0), 0.008, 0.03, S["coil"], n=6)
    sw = [("plain", (54, 56, 60)), ("grip", (28, 28, 30), (48, 48, 52)), ("metal", (120, 124, 130)),
          ("hazard", (225, 180, 30), (25, 25, 25)), ("glow", (60, 150, 255)), ("panel", (40, 42, 46), (80, 84, 90)),
          ("logo", (200, 200, 200), (30, 30, 30)), ("metal", (190, 190, 195))]
    # the game holds long weapons by the bottom of the handle (y = 0)
    m.faces = [([v + np.array([0, 0.30, 0]) for v in vs], swi, uv) for vs, swi, uv in m.faces]
    return "SCP_ShockMaul", m, sw


def tilt(deg, pivot):
    """Rotation around the x axis (tilts a part forward/back) about pivot."""
    c, sn = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    px, py, pz = pivot
    def f(v):
        y, z = v[1] - py, v[2] - pz
        return np.array([v[0], py + y * c - z * sn, pz + y * sn + z * c])
    return f


def assault_rifle():
    """SCP_Epsilon: the task forces' carbine (origin at the pistol grip)."""
    m = Mesh()
    S = dict(body=0, dark=1, steel=2, grip=3, glow=4, logo=5, tan=6)
    m.box((0, 0.06, 0.035), (0.046, 0.30, 0.07), S["body"])            # upper receiver
    m.box((0, 0.03, 0.000), (0.040, 0.16, 0.03), S["dark"])            # lower receiver
    m.box((0, 0.27, 0.035), (0.052, 0.14, 0.058), S["tan"])            # handguard
    for k in range(3):                                                  # handguard vents
        m.box((0.027, 0.23 + k * 0.035, 0.035), (0.002, 0.018, 0.02), S["dark"])
    m.cyl((0, 0.40, 0.045), 0.010, 0.14, S["steel"], n=8)              # barrel
    m.cyl((0, 0.48, 0.045), 0.016, 0.04, S["dark"], n=8)               # muzzle brake
    m.box((0, 0.36, 0.075), (0.008, 0.012, 0.03), S["dark"])           # front sight
    m.box((0, -0.10, 0.04), (0.03, 0.06, 0.035), S["dark"])            # buffer tube
    m.box((0, -0.17, 0.025), (0.042, 0.10, 0.075), S["dark"], rot=tilt(-8, (0, -0.12, 0.04)))   # stock
    m.box((0, -0.225, 0.02), (0.046, 0.015, 0.09), S["grip"])          # butt pad
    m.box((0, -0.005, -0.045), (0.032, 0.035, 0.085), S["grip"], rot=tilt(-18, (0, 0, -0.01)))  # pistol grip
    m.box((0, 0.065, -0.06), (0.026, 0.05, 0.10), S["dark"], rot=tilt(12, (0, 0.065, -0.01)))  # magazine
    m.box((0, 0.035, -0.022), (0.006, 0.045, 0.006), S["dark"])        # trigger guard
    m.box((0, 0.10, 0.074), (0.022, 0.30, 0.01), S["dark"])            # top rail
    m.box((0, 0.06, 0.098), (0.034, 0.075, 0.038), S["dark"])          # red dot sight
    m.box((0, 0.098, 0.098), (0.026, 0.003, 0.026), S["glow"])         # its lens
    m.box((0.0235, 0.08, 0.035), (0.002, 0.05, 0.04), S["logo"])       # Foundation mark
    sw = [("panel", (58, 62, 70), (76, 82, 92)), ("plain", (30, 31, 34)), ("metal", (95, 98, 104)),
          ("grip", (26, 26, 28), (44, 44, 48)), ("glow", (230, 60, 60)), ("logo", (58, 62, 70), (225, 225, 225)),
          ("plain", (120, 108, 82))]
    return "SCP_Epsilon", m, sw


def pistol():
    """SCP_SecPistol: the guards' service pistol (origin at the grip)."""
    m = Mesh()
    S = dict(slide=0, frame=1, steel=2, grip=3, logo=4, glow=5)
    m.box((0, 0.06, 0.032), (0.026, 0.17, 0.03), S["slide"])
    for k in range(4):                                                  # slide serrations
        m.box((0.0135, 0.0 + k * 0.008, 0.034), (0.002, 0.003, 0.02), S["frame"])
    m.box((0, 0.055, 0.008), (0.024, 0.15, 0.02), S["frame"])
    m.cyl((0, 0.15, 0.03), 0.006, 0.012, S["steel"], n=6)
    m.box((0, 0.13, 0.05), (0.004, 0.008, 0.008), S["glow"])           # front sight dot
    m.box((0, -0.01, 0.05), (0.014, 0.008, 0.008), S["glow"])          # rear sight
    m.box((0, -0.005, -0.04), (0.026, 0.038, 0.085), S["grip"], rot=tilt(-15, (0, 0, 0.0)))
    m.box((0, 0.03, -0.012), (0.006, 0.04, 0.006), S["frame"])         # trigger guard
    m.box((0.0135, 0.07, 0.032), (0.001, 0.03, 0.02), S["logo"])
    sw = [("metal", (40, 42, 46)), ("plain", (30, 30, 32)), ("metal", (130, 130, 135)),
          ("grip", (34, 30, 28), (52, 46, 42)), ("logo", (40, 42, 46), (215, 215, 215)), ("glow", (120, 255, 140))]
    return "SCP_SecPistol", m, sw


def shotgun():
    """SCP_RiotShotgun: pump shotgun of the riot teams (origin at the grip)."""
    m = Mesh()
    S = dict(body=0, dark=1, steel=2, grip=3, hazard=4, logo=5)
    m.box((0, 0.04, 0.03), (0.044, 0.20, 0.065), S["body"])            # receiver
    m.cyl((0, 0.33, 0.048), 0.012, 0.40, S["steel"], n=8)              # barrel
    m.cyl((0, 0.30, 0.020), 0.011, 0.32, S["dark"], n=8)               # magazine tube
    m.box((0, 0.27, 0.025), (0.046, 0.12, 0.048), S["grip"])           # pump
    for k in range(4):
        m.box((0, 0.225 + k * 0.03, 0.025), (0.048, 0.006, 0.05), S["dark"])
    m.box((0, 0.52, 0.048), (0.03, 0.03, 0.03), S["hazard"])           # orange "less lethal" band
    m.box((0, -0.04, -0.04), (0.032, 0.035, 0.075), S["grip"], rot=tilt(-18, (0, -0.02, 0.0)))  # pistol grip
    m.box((0, -0.17, 0.02), (0.04, 0.22, 0.06), S["dark"], rot=tilt(-6, (0, -0.06, 0.03)))     # stock
    m.box((0, -0.285, 0.008), (0.044, 0.015, 0.085), S["grip"])        # recoil pad
    m.box((0, 0.10, 0.068), (0.016, 0.06, 0.012), S["dark"])           # ghost-ring sight base
    m.box((0.023, 0.05, 0.03), (0.002, 0.06, 0.035), S["logo"])
    sw = [("panel", (46, 48, 52), (64, 66, 72)), ("plain", (28, 28, 30)), ("metal", (90, 92, 98)),
          ("grip", (30, 30, 32), (48, 48, 52)), ("hazard", (230, 120, 30), (25, 25, 25)),
          ("logo", (46, 48, 52), (225, 225, 225))]
    return "SCP_RiotShotgun", m, sw


WEAPONS = [shock_maul, assault_rifle, pistol, shotgun]


# ----------------------------------------------------------------------
# Preview render (flat shading, painter's algorithm) and icons
# ----------------------------------------------------------------------

def render(mesh, atlas, size, yaw, pitch, scale=None, bg=(0, 0, 0, 0), light=(-0.35, -0.6, 0.7), fit=0.9):
    """Textured render: painter's algorithm, each face mapped from the atlas."""
    cy, sy = math.cos(yaw), math.sin(yaw)
    cp, sp = math.cos(pitch), math.sin(pitch)
    def view(v):
        x, y, z = v
        x, y = x * cy - y * sy, x * sy + y * cy        # yaw around z
        y, z = y * cp - z * sp, y * sp + z * cp        # pitch around x
        return np.array([x, y, z])
    tex = atlas.convert("RGB")
    polys = []
    L = np.array(light); L = L / np.linalg.norm(L)
    for vs, sw, uv in mesh.faces:
        pv = [view(v) for v in vs]
        n = normal(pv)
        if n[1] > 1e-6:     # facing away (camera looks along +y)
            continue
        tuv = [tuple(c * ATLAS for c in swatch_uv(sw, u, w)) for u, w in face_uvs(vs, uv)]
        shade = 0.5 + 0.65 * max(0.0, float(np.dot(n, L)))
        polys.append((np.mean([p[1] for p in pv]), pv, tuv, shade))
    allp = np.array([p for _, pv, _, _ in polys for p in pv])
    xs, zs = allp[:, 0], allp[:, 2]
    span = max(xs.max() - xs.min(), zs.max() - zs.min())
    k = scale or (size * fit / span)
    ox = size / 2 - (xs.max() + xs.min()) / 2 * k
    oz = size / 2 + (zs.max() + zs.min()) / 2 * k
    S = 3
    img = Image.new("RGBA", (size * S, size * S), bg)
    for _, pv, tuv, shade in sorted(polys, key=lambda t: -t[0]):
        scr = [((ox + p[0] * k) * S, (oz - p[2] * k) * S) for p in pv]
        x0, y0 = int(min(q[0] for q in scr)), int(min(q[1] for q in scr))
        x1, y1 = int(max(q[0] for q in scr)) + 2, int(max(q[1] for q in scr)) + 2
        w, h = x1 - x0, y1 - y0
        # affine screen -> texture from the first three corners
        A = np.array([[q[0] - x0, q[1] - y0, 1] for q in scr[:3]])
        if abs(np.linalg.det(A)) < 1e-6:
            continue
        cu = np.linalg.solve(A, [t[0] for t in tuv[:3]])
        cv = np.linalg.solve(A, [t[1] for t in tuv[:3]])
        patch = tex.transform((w, h), Image.AFFINE, tuple(cu) + tuple(cv), resample=Image.BILINEAR)
        patch = patch.point(lambda c: min(255, int(c * shade)))
        mask = Image.new("L", (w, h), 0)
        ImageDraw.Draw(mask).polygon([(q[0] - x0, q[1] - y0) for q in scr], fill=255)
        img.paste(patch, (x0, y0), mask)
    return img.resize((size, size), Image.LANCZOS)


def icon(mesh, atlas, name):
    img = render(mesh, atlas, 32, math.radians(90), math.radians(-12), fit=0.98)
    # tilt the icon 45 degrees like the game's long weapons
    big = render(mesh, atlas, 128, math.radians(90), math.radians(-12), fit=0.98)
    big = big.rotate(45, resample=Image.BICUBIC, expand=False)
    a = np.array(big)
    ys, xs = np.nonzero(a[:, :, 3] > 10)
    big = big.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
    w, h = big.size
    sq = Image.new("RGBA", (max(w, h) + 4, max(w, h) + 4), (0, 0, 0, 0))
    sq.paste(big, ((sq.width - w) // 2, (sq.height - h) // 2))
    img = sq.resize((32, 32), Image.LANCZOS)
    # dark outline so it reads on the inventory background
    alpha = img.split()[3]
    ring = alpha.filter(ImageFilter.MaxFilter(3))
    out = Image.new("RGBA", img.size, (18, 18, 20, 0))
    out.putalpha(ring.point(lambda v: 255 if v > 40 else 0))
    out.alpha_composite(img)
    out.save(os.path.join(OUT_ICON, f"Item_{name}.png"))


def preview_sheet(items):
    os.makedirs(PREVIEW, exist_ok=True)
    for name, mesh, atlas in items:
        W = 900
        sheet = Image.new("RGBA", (W * 2, W), (34, 36, 40, 255))
        a = render(mesh, atlas, W, math.radians(90), math.radians(75))           # profile
        b = render(mesh, atlas, W, math.radians(55), math.radians(-30))          # 3/4
        sheet.alpha_composite(a, (0, 0)); sheet.alpha_composite(b, (W, 0))
        sheet.convert("RGB").save(os.path.join(PREVIEW, f"preview_{name}.png"))


def main():
    items = []
    for fn in WEAPONS:
        name, mesh, sw = fn()
        atlas = make_atlas(sw, name)
        nv, nf = write_x(mesh, name, name)
        icon(mesh, atlas, name)
        items.append((name, mesh, atlas))
        print(f"{name}: {nv} vertices, {nf} faces")
    if "preview" in sys.argv:
        preview_sheet(items)


if __name__ == "__main__":
    main()
