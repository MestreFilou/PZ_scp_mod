#!/usr/bin/env python3
"""
Builds the SCP site tileset `scp_facility_02` (walls, door frames, doors,
floors, signs, pocket dimension) and repacks the mod's texture pack.

Every tile is drawn procedurally: simple 3D boxes projected to Project
Zomboid's isometric view, with procedural textures mapped on each face.

Outputs:
  art/scp_facility_02_tilesheet.png                (sheet, 8 columns, for editing)
  Contents/mods/SCPFoundation/42/media/texturepacks/scp_facility.pack
      (scp_facility_01 from art/scp_facility_01_tilesheet.png + scp_facility_02)
  Contents/mods/SCPFoundation/42/media/scp_facility.tiles
  art/scp_facility_02_preview.png                  (small room mock-up)

Usage: python3 tools/make_facility_tiles.py   (from the repository root)
Needs numpy and Pillow.
"""

import math
import os
import struct
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEDIA = os.path.join(ROOT, "Contents/mods/SCPFoundation/42/media")
ART = os.path.join(ROOT, "art")

TW, TH = 128, 256           # tile size (Build 42 2x tiles)
SS = 4                      # supersampling
WALL_T = 0.07               # wall thickness (tile units)
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

rng = np.random.default_rng(914)


# ----------------------------------------------------------------------
# Projection and face drawing
# ----------------------------------------------------------------------

def proj(x, y, z):
    """World (x east, y south, z up; 1 = one tile / one wall height) -> screen."""
    return ((64 + (x - y) * 64) * SS, (192 + (x + y) * 32 - z * 192) * SS)


def canvas():
    return Image.new("RGBA", (TW * SS, TH * SS), (0, 0, 0, 0))


def face(img, tex, p0, pu, pv, shade=1.0):
    """Maps texture `tex` on the parallelogram p0 (tex top-left),
    pu (tex top-right), pv (tex bottom-left), given as world points."""
    if shade != 1.0:
        a = np.asarray(tex).astype(np.float32)
        a[..., :3] *= shade
        tex = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGBA")
    s0, su, sv = (np.array(proj(*p)) for p in (p0, pu, pv))
    tw, th = tex.size
    m = np.array([[(su - s0)[0] / tw, (sv - s0)[0] / th],
                  [(su - s0)[1] / tw, (sv - s0)[1] / th]])
    inv = np.linalg.inv(m)
    off = -inv @ s0
    data = (inv[0, 0], inv[0, 1], off[0], inv[1, 0], inv[1, 1], off[1])
    warped = tex.transform(img.size, Image.AFFINE, data, resample=Image.BILINEAR, fillcolor=(0, 0, 0, 0))
    img.alpha_composite(warped)


def finish(img):
    return img.resize((TW, TH), Image.LANCZOS)


# ----------------------------------------------------------------------
# Texture helpers (numpy RGBA, v = 0 at the top)
# ----------------------------------------------------------------------

def hexrgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], np.float32)


def noise(w, h, scale, amp, seed=None):
    g = np.random.default_rng(seed) if seed is not None else rng
    small = g.random((max(2, h // scale), max(2, w // scale))).astype(np.float32)
    im = Image.fromarray((small * 255).astype(np.uint8), "L").resize((w, h), Image.BICUBIC)
    return (np.asarray(im).astype(np.float32) / 255 - 0.5) * 2 * amp


def base(w, h, color, grain=10, blotch=14, seed=None):
    c = hexrgb(color)
    a = np.zeros((h, w, 4), np.float32)
    n = noise(w, h, 2, grain, seed) + noise(w, h, 24, blotch, seed)
    a[..., :3] = c + n[..., None]
    a[..., 3] = 255
    return a


def rect(a, u0, v0, u1, v1, color, alpha=1.0):
    h, w = a.shape[:2]
    x0, x1 = int(u0 * w), int(u1 * w)
    y0, y1 = int(v0 * h), int(v1 * h)
    c = hexrgb(color) if isinstance(color, str) else np.array(color, np.float32)
    a[y0:y1, x0:x1, :3] = a[y0:y1, x0:x1, :3] * (1 - alpha) + c * alpha
    a[y0:y1, x0:x1, 3] = 255


def shade_rect(a, u0, v0, u1, v1, k):
    h, w = a.shape[:2]
    a[int(v0 * h):int(v1 * h), int(u0 * w):int(u1 * w), :3] *= k


def hline(a, v, thick, color, alpha=1.0):
    rect(a, 0, v - thick / 2, 1, v + thick / 2, color, alpha)


def vline(a, u, thick, color, alpha=1.0):
    rect(a, u - thick / 2, 0, u + thick / 2, 1, color, alpha)


def hazard(a, u0, v0, u1, v1, c1="#e8b81c", c2="#1b1b1b", period=28, angle=1):
    h, w = a.shape[:2]
    x0, x1 = int(u0 * w), int(u1 * w)
    y0, y1 = int(v0 * h), int(v1 * h)
    yy, xx = np.mgrid[y0:y1, x0:x1]
    band = ((xx + angle * yy) // (period // 2)) % 2
    col = np.where(band[..., None] == 0, hexrgb(c1), hexrgb(c2))
    col = col + noise(x1 - x0, y1 - y0, 2, 8)[..., None]
    a[y0:y1, x0:x1, :3] = col
    a[y0:y1, x0:x1, 3] = 255


def grime(a, strength=40, from_bottom=0.25):
    h, w = a.shape[:2]
    v = np.linspace(0, 1, h)[:, None]
    g = np.clip((v - (1 - from_bottom)) / from_bottom, 0, 1) * strength
    a[..., :3] -= (g * (0.6 + 0.4 * (noise(w, h, 6, 1) + 1) / 2))[..., None]


def drips(a, count, color, length=0.35, seed=None):
    g = np.random.default_rng(seed)
    h, w = a.shape[:2]
    c = hexrgb(color)
    for _ in range(count):
        x = int(g.random() * w)
        L = int(h * length * (0.3 + g.random()))
        wd = 2 + int(g.random() * 5)
        for y in range(L):
            k = 1 - y / L
            x0 = max(0, x - wd // 2)
            a[y, x0:x0 + wd, :3] = a[y, x0:x0 + wd, :3] * (1 - 0.8 * k) + c * 0.8 * k


def bolts(a, points, r=4, color="#2b2e31"):
    h, w = a.shape[:2]
    for (u, v) in points:
        cx, cy = int(u * w), int(v * h)
        yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
        m = xx * xx + yy * yy <= r * r
        ys, xs = slice(max(0, cy - r), cy + r + 1), slice(max(0, cx - r), cx + r + 1)
        sub = a[ys, xs]
        mm = m[: sub.shape[0], : sub.shape[1]]
        sub[mm, :3] = hexrgb(color)
        sub[mm, 3] = 255


def to_img(a):
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGBA")


def text_tex(w, h, bg, fg, lines, border=None, font_px=None):
    img = Image.new("RGBA", (w, h), bg)
    d = ImageDraw.Draw(img)
    if border:
        d.rectangle([2, 2, w - 3, h - 3], outline=border, width=max(3, h // 16))
    n = len(lines)
    size = font_px or int(h * 0.62 / n)
    font = ImageFont.truetype(FONT_BOLD, size)
    total = n * size * 1.1
    y = (h - total) / 2
    for line in lines:
        tw = d.textlength(line, font=font)
        if tw > w * 0.9:
            f2 = ImageFont.truetype(FONT_BOLD, int(size * w * 0.9 / tw))
            tw = d.textlength(line, font=f2)
            d.text(((w - tw) / 2, y + (size - f2.size) / 2), line, fill=fg, font=f2)
        else:
            d.text(((w - tw) / 2, y), line, fill=fg, font=font)
        y += size * 1.1
    return img


# ----------------------------------------------------------------------
# Material textures
# ----------------------------------------------------------------------

WALL_W, WALL_H = 256, 512


def wall_ez():
    a = base(WALL_W, WALL_H, "#b8bcc0", 6, 8, 1)
    rect(a, 0, 0.62, 1, 1, "#7b8288")            # dark lower panel
    a[int(0.62 * WALL_H):, :, :3] += noise(WALL_W, WALL_H - int(0.62 * WALL_H), 2, 6)[..., None]
    hline(a, 0.62, 0.014, "#3a6ea5")             # blue stripe
    hline(a, 0.645, 0.006, "#e2e5e8")
    rect(a, 0, 0.965, 1, 1, "#3d4246")          # baseboard
    for v in (0.2, 0.41):
        hline(a, v, 0.004, "#9da2a6")            # panel seams
    vline(a, 0.0, 0.01, "#8f949a")
    vline(a, 1.0, 0.01, "#8f949a")
    grime(a, 18, 0.2)
    return to_img(a)


def wall_lcz():
    a = base(WALL_W, WALL_H, "#d9d6cd", 7, 10, 2)
    # concrete blocks, staggered
    rows = 7
    for r in range(1, rows):
        hline(a, r / rows * 0.9, 0.005, "#b3afa6")
    for r in range(rows):
        off = 0.5 if r % 2 else 0.0
        for u in (off, off + 0.5):
            u = u % 1.0
            rect(a, u - 0.002, r / rows * 0.9, u + 0.002, (r + 1) / rows * 0.9, "#b3afa6")
    hazard(a, 0, 0.9, 1, 0.965, period=30)        # yellow/black floor strip
    hline(a, 0.9, 0.006, "#6a6a64")
    rect(a, 0, 0.965, 1, 1, "#4a4a46")
    hline(a, 0.55, 0.01, "#c79a2a", 0.8)          # thin amber line
    grime(a, 22, 0.18)
    return to_img(a)


def wall_hcz():
    a = base(WALL_W, WALL_H, "#5c6062", 12, 22, 3)
    # big poured concrete slabs with formwork holes
    hline(a, 0.33, 0.006, "#45484a")
    hline(a, 0.66, 0.006, "#45484a")
    for u in (0.25, 0.75):
        for v in (0.165, 0.495, 0.82):
            bolts(a, [(u, v)], 5, "#3a3d3f")
    # rusty steel ribs
    for u in (0.02, 0.98):
        rect(a, u - 0.03, 0, u + 0.03, 1, "#4d4a46")
        shade_rect(a, u - 0.03, 0, u - 0.01, 1, 1.25)
    rect(a, 0, 0.44, 1, 0.47, "#a3392a")          # red warning band
    rect(a, 0, 0.965, 1, 1, "#2f3133")
    a[..., :3] += (noise(WALL_W, WALL_H, 10, 10)[..., None]) * np.array([1.0, 0.7, 0.4])
    grime(a, 35, 0.3)
    drips(a, 6, "#3a352c", 0.25, 33)
    return to_img(a)


def wall_pocket():
    a = base(WALL_W, WALL_H, "#22261c", 10, 26, 4)
    g = noise(WALL_W, WALL_H, 18, 1, 41)
    blot = np.clip((g - 0.25) * 3, 0, 1)
    a[..., :3] = a[..., :3] * (1 - blot[..., None]) + hexrgb("#4a3a22") * blot[..., None]
    drips(a, 14, "#050505", 0.6, 42)
    gloss = np.clip((noise(WALL_W, WALL_H, 4, 1, 43) - 0.7) * 4, 0, 1)
    a[..., :3] += gloss[..., None] * 35
    grime(a, 40, 0.4)
    return to_img(a)


def cap_tex(color):
    return to_img(base(64, 64, color, 4, 4))


FLOOR = 256


def floor_ez():
    a = base(FLOOR, FLOOR, "#9a9fa3", 5, 6, 11)
    n = 4
    for i in range(n):
        for j in range(n):
            shade_rect(a, i / n, j / n, (i + 1) / n, (j + 1) / n, 0.95 + 0.1 * rng.random())
    for i in range(n + 1):
        hline(a, i / n, 0.012, "#6f7377")
        vline(a, i / n, 0.012, "#6f7377")
    return to_img(a)


def floor_lcz():
    a = base(FLOOR, FLOOR, "#bdbab2", 6, 10, 12)
    for i in (0, 0.5, 1):
        hline(a, i, 0.008, "#9c998f")
        vline(a, i, 0.008, "#9c998f")
    return to_img(a)


def floor_hcz():
    a = base(FLOOR, FLOOR, "#5f6367", 6, 10, 13)
    # diamond plate
    yy, xx = np.mgrid[0:FLOOR, 0:FLOOR]
    p = 32
    lx, ly = (xx % p) - p / 2, (yy % p) - p / 2
    ridge = (np.abs(lx + ly) < 3) & (np.abs(lx - ly) < 11)
    ridge2 = (np.abs(lx - ly) < 3) & (np.abs(lx + ly) < 11)
    a[ridge, :3] += 28
    a[ridge2, :3] -= 0
    a[(np.roll(ridge, 2, axis=0)) & ~ridge, :3] -= 22
    for i in (0, 1):
        hline(a, i, 0.012, "#3e4144")
        vline(a, i, 0.012, "#3e4144")
    return to_img(a)


def floor_grate():
    a = base(FLOOR, FLOOR, "#3d4145", 5, 6, 14)
    yy, xx = np.mgrid[0:FLOOR, 0:FLOOR]
    holes = ((xx % 16) > 3) & ((yy % 16) > 3)
    a[holes, :3] = hexrgb("#0e0f10")
    rect(a, 0, 0, 1, 0.04, "#575c61")
    rect(a, 0, 0.96, 1, 1, "#575c61")
    rect(a, 0, 0, 0.04, 1, "#575c61")
    rect(a, 0.96, 0, 1, 1, "#575c61")
    return to_img(a)


def floor_elevator():
    a = base(FLOOR, FLOOR, "#3a3d40", 5, 6, 15)
    hazard(a, 0.06, 0.06, 0.94, 0.94, period=48)
    rect(a, 0.2, 0.2, 0.8, 0.8, "#4b5054")
    yy, xx = np.mgrid[0:FLOOR, 0:FLOOR]
    stripes = ((xx // 8) % 2 == 0)
    sub = (slice(int(0.2 * FLOOR), int(0.8 * FLOOR)), slice(int(0.2 * FLOOR), int(0.8 * FLOOR)))
    a[sub][stripes[sub], :3] -= 10
    return to_img(a)


def floor_hazard_line():
    a = base(FLOOR, FLOOR, "#7e8286", 5, 8, 16)
    hazard(a, 0, 0.4, 1, 0.6, period=40)
    return to_img(a)


def floor_pocket(seed):
    a = base(FLOOR, FLOOR, "#1a1c14", 12, 20, seed)
    g = noise(FLOOR, FLOOR, 20, 1, seed + 1)
    blot = np.clip((g - 0.1) * 2.5, 0, 1)
    a[..., :3] = a[..., :3] * (1 - blot[..., None]) + hexrgb("#3d311f") * blot[..., None]
    gl = np.clip((noise(FLOOR, FLOOR, 6, 1, seed + 2) - 0.55) * 4, 0, 1)
    a[..., :3] += gl[..., None] * 28
    return to_img(a)


def floor_pocket_exit():
    img = floor_pocket(70)
    a = np.asarray(img).astype(np.float32)
    yy, xx = np.mgrid[0:FLOOR, 0:FLOOR]
    d = np.sqrt((xx - FLOOR / 2) ** 2 + (yy - FLOOR / 2) ** 2) / (FLOOR / 2)
    ring = np.exp(-((d - 0.55) ** 2) / 0.01) + 0.5 * np.exp(-(d ** 2) / 0.08)
    a[..., :3] += ring[..., None] * np.array([120, 150, 110])
    return to_img(a)


DOOR_W, DOOR_H = 256, 336


def door_standard():
    a = base(DOOR_W, DOOR_H, "#8f959a", 4, 6, 21)
    a[..., :3] += noise(DOOR_W, DOOR_H, 1, 6)[..., None]          # brushed
    vline(a, 0.5, 0.012, "#4a4f53")                                 # two leaves
    for u0 in (0.12, 0.62):
        rect(a, u0, 0.14, u0 + 0.26, 0.4, "#2b3640")              # windows
        rect(a, u0 + 0.02, 0.16, u0 + 0.08, 0.38, "#5f7484", 0.5)
    hazard(a, 0, 0.88, 1, 0.97, period=26)
    rect(a, 0, 0.97, 1, 1, "#33373a")
    rect(a, 0, 0, 1, 0.025, "#5c6166")
    return to_img(a)


def door_containment():
    a = base(DOOR_W, DOOR_H, "#4b5157", 6, 10, 22)
    vline(a, 0.5, 0.016, "#202326")
    hazard(a, 0, 0.42, 1, 0.58, period=40)
    for u in (0.08, 0.42, 0.58, 0.92):
        bolts(a, [(u, 0.08), (u, 0.3), (u, 0.7), (u, 0.92)], 5, "#2a2e32")
    rect(a, 0.2, 0.15, 0.3, 0.2, "#c22a1f")                         # red lamp
    rect(a, 0.7, 0.15, 0.8, 0.2, "#c22a1f")
    grime(a, 25, 0.2)
    return to_img(a)


def frame_trim(a, a0, b0, top, reader=True):
    """Steel frame around the door opening [a0, b0] x [top, 1] in texture coords,
    then cuts the opening (alpha 0)."""
    t = 0.045
    rect(a, a0 - t, top - t * 0.9, b0 + t, 1, "#62686d")
    hazard(a, a0 - t, top - t * 0.9, b0 + t, top, period=22)
    shade_rect(a, a0 - t, top, a0, 1, 0.85)
    shade_rect(a, b0, top, b0 + t, 1, 1.12)
    if reader:
        rect(a, b0 + 0.07, 0.43, b0 + 0.12, 0.53, "#22262a")      # keycard reader
        rect(a, b0 + 0.08, 0.445, b0 + 0.11, 0.46, "#38d15a")
        rect(a, b0 + 0.08, 0.48, b0 + 0.11, 0.515, "#0c0d0e")
    h, w = a.shape[:2]
    a[int(top * h):, int(a0 * w):int(b0 * w), 3] = 0


# ----------------------------------------------------------------------
# Tile builders
# ----------------------------------------------------------------------

DOOR_A, DOOR_B, DOOR_TOP = 0.14, 0.86, 0.78   # opening along the wall; door height


def west_wall(img, tex, cap):
    face(img, cap, (0, 0, 1), (0, 1, 1), (WALL_T, 0, 1))
    # u runs south -> north so the texture reads left to right on screen
    face(img, tex, (WALL_T, 1, 1), (WALL_T, 0, 1), (WALL_T, 1, 0), 0.86)


def north_wall(img, tex, cap):
    face(img, cap, (0, 0, 1), (1, 0, 1), (0, WALL_T, 1))
    face(img, tex, (0, WALL_T, 1), (1, WALL_T, 1), (0, WALL_T, 0), 1.0)


def tile_wall(tex, side):
    img = canvas()
    cap = cap_tex("#2c2f31")
    if side in ("W", "NW"):
        west_wall(img, tex, cap)
    if side in ("N", "NW"):
        north_wall(img, tex, cap)
    return finish(img)


def tile_frame(tex, side):
    a = np.asarray(tex).astype(np.float32).copy()
    frame_trim(a, DOOR_A, DOOR_B, 1 - DOOR_TOP)
    ftex = to_img(a)
    img = canvas()
    cap = cap_tex("#2c2f31")
    jamb = to_img(base(32, 128, "#55595e", 4, 4))
    if side == "W":
        west_wall(img, ftex, cap)
        # jamb seen through the opening (south face of the north segment)
        face(img, jamb, (0, DOOR_A, DOOR_TOP), (WALL_T, DOOR_A, DOOR_TOP), (0, DOOR_A, 0), 0.7)
    else:
        north_wall(img, ftex, cap)
        face(img, jamb, (DOOR_A, 0, DOOR_TOP), (DOOR_A, WALL_T, DOOR_TOP), (DOOR_A, 0, 0), 0.6)
    return finish(img)


def tile_door(tex, side, opened):
    img = canvas()
    edge = to_img(base(16, 128, "#3a3e42", 3, 3))
    d = 0.055          # door plane, inside the wall thickness
    if not opened:
        if side == "W":
            face(img, edge, (d - 0.03, DOOR_A, DOOR_TOP), (d, DOOR_A, DOOR_TOP), (d - 0.03, DOOR_A, 0), 0.8)
            face(img, tex, (d, DOOR_B, DOOR_TOP), (d, DOOR_A, DOOR_TOP), (d, DOOR_B, 0), 0.88)
        else:
            face(img, edge, (DOOR_A, d - 0.03, DOOR_TOP), (DOOR_A, d, DOOR_TOP), (DOOR_A, d - 0.03, 0), 0.75)
            face(img, tex, (DOOR_A, d, DOOR_TOP), (DOOR_B, d, DOOR_TOP), (DOOR_A, d, 0), 1.0)
    else:
        # sliding door: retracted into the wall, only its edge shows
        sliver = tex.crop((int(DOOR_W * 0.92), 0, DOOR_W, DOOR_H))
        if side == "W":
            face(img, sliver, (d, DOOR_B - 0.05, DOOR_TOP), (d, DOOR_B, DOOR_TOP), (d, DOOR_B - 0.05, 0), 0.8)
        else:
            face(img, sliver, (DOOR_B - 0.05, d, DOOR_TOP), (DOOR_B, d, DOOR_TOP), (DOOR_B - 0.05, d, 0), 0.9)
    return finish(img)


def tile_floor(tex):
    img = canvas()
    face(img, tex, (0, 0, 0), (1, 0, 0), (0, 1, 0))
    return finish(img)


def tile_sign(tex, side, z0=0.5, z1=0.68, a0=0.18, b0=0.82):
    img = canvas()
    off = WALL_T + 0.006
    edge = to_img(base(8, 64, "#202224", 2, 2))
    if side == "W":
        face(img, edge, (WALL_T, a0, z1), (off, a0, z1), (WALL_T, a0, z0), 0.6)
        face(img, tex, (off, b0, z1), (off, a0, z1), (off, b0, z0), 0.92)
    else:
        face(img, edge, (a0, WALL_T, z1), (a0, off, z1), (a0, WALL_T, z0), 0.6)
        face(img, tex, (a0, off, z1), (b0, off, z1), (a0, off, z0), 1.0)
    return finish(img)


def logo_tex(w=256, h=96):
    img = Image.new("RGBA", (w, h), (226, 228, 230, 255))
    d = ImageDraw.Draw(img)
    d.rectangle([2, 2, w - 3, h - 3], outline=(40, 40, 40, 255), width=4)
    cx, cy, r = 52, h // 2, 32
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(25, 25, 25, 255), width=7)
    d.ellipse([cx - 11, cy - 11, cx + 11, cy + 11], outline=(25, 25, 25, 255), width=5)
    for k in range(3):
        ang = math.radians(-90 + k * 120)
        ox, oy = cx + math.cos(ang) * (r + 3), cy + math.sin(ang) * (r + 3)
        ix, iy = cx + math.cos(ang) * 15, cy + math.sin(ang) * 15
        d.line([(ox, oy), (ix, iy)], fill=(25, 25, 25, 255), width=7)
        px, py = -math.sin(ang) * 9, math.cos(ang) * 9
        d.polygon([(ix + math.cos(ang) * -2, iy + math.sin(ang) * -2),
                   (ix + math.cos(ang) * 10 + px, iy + math.sin(ang) * 10 + py),
                   (ix + math.cos(ang) * 10 - px, iy + math.sin(ang) * 10 - py)], fill=(25, 25, 25, 255))
    font = ImageFont.truetype(FONT_BOLD, 34)
    d.text((100, 12), "SCP", fill=(25, 25, 25, 255), font=font)
    f2 = ImageFont.truetype(FONT_BOLD, 13)
    d.text((100, 54), "SECURE. CONTAIN.", fill=(25, 25, 25, 255), font=f2)
    d.text((100, 70), "PROTECT.", fill=(25, 25, 25, 255), font=f2)
    return img


def danger_tex(w=256, h=96):
    img = Image.new("RGBA", (w, h), (232, 186, 28, 255))
    d = ImageDraw.Draw(img)
    d.rectangle([3, 3, w - 4, h - 4], outline=(20, 20, 20, 255), width=6)
    d.polygon([(20, 76), (52, 18), (84, 76)], outline=(20, 20, 20, 255), fill=(232, 186, 28, 255), width=6)
    f = ImageFont.truetype(FONT_BOLD, 26)
    d.text((46, 34), "!", fill=(20, 20, 20, 255), font=f)
    f2 = ImageFont.truetype(FONT_BOLD, 30)
    d.text((96, 16), "DANGER", fill=(20, 20, 20, 255), font=f2)
    f3 = ImageFont.truetype(FONT_BOLD, 12)
    d.text((98, 56), "KETER-CLASS ANOMALY", fill=(20, 20, 20, 255), font=f3)
    return img


# ----------------------------------------------------------------------
# Tileset definition
# ----------------------------------------------------------------------

def P(**kw):
    return [(k, v) for k, v in kw.items()]


def wall_props(kind, name, idx, mat="Cinderblock"):
    if kind == "W":
        return [("WallW", ""), ("wall", ""), ("MaterialType", mat)]
    if kind == "N":
        return [("WallN", ""), ("wall", ""), ("MaterialType", mat)]
    if kind == "NW":
        return [("WallNW", ""), ("wall", ""), ("MaterialType", mat),
                ("CornerNorthWall", f"{name}_{idx - 1}"), ("CornerWestWall", f"{name}_{idx - 2}")]
    if kind == "FW":
        return [("DoorWallW", ""), ("wall", ""), ("MaterialType", mat)]
    if kind == "FN":
        return [("DoorWallN", ""), ("wall", ""), ("MaterialType", mat)]


def door_props(side, closed, label):
    p = [("CustomName", label), ("GroupName", "SCP"), ("Material", "MetalPlates"), ("Material2", "Door"),
         ("MaterialType", "Metal"), ("attached" + side, "")]
    if closed:
        p.append(("door" + side, ""))
    return p


def floor_props(label):
    return [("CustomName", label), ("GroupName", "SCP"), ("solidfloor", ""), ("diamondFloor", ""),
            ("attachedFloor", ""), ("Material", "Concrete")]


def sign_props(side, label):
    return [("CustomName", label), ("GroupName", "SCP"), ("attached" + side, "")]


SHEET = "scp_facility_02"
COLS = 8


def build_tiles():
    tiles = {}

    def put(i, img, props):
        tiles[i] = (img, props)

    zones = [("EZ", wall_ez(), 0), ("LCZ", wall_lcz(), 8), ("HCZ", wall_hcz(), 16)]
    for zone, tex, i0 in zones:
        put(i0 + 0, tile_wall(tex, "W"), wall_props("W", SHEET, i0 + 0))
        put(i0 + 1, tile_wall(tex, "N"), wall_props("N", SHEET, i0 + 1))
        put(i0 + 2, tile_wall(tex, "NW"), wall_props("NW", SHEET, i0 + 2))
        put(i0 + 3, tile_frame(tex, "W"), wall_props("FW", SHEET, i0 + 3))
        put(i0 + 4, tile_frame(tex, "N"), wall_props("FN", SHEET, i0 + 4))
    put(5, tile_floor(floor_ez()), floor_props("Entrance Zone Floor"))
    put(6, tile_floor(floor_hazard_line()), floor_props("Hazard Line Floor"))
    put(13, tile_floor(floor_lcz()), floor_props("Light Containment Floor"))
    put(14, tile_floor(floor_grate()), floor_props("Containment Grating"))
    put(15, tile_floor(floor_elevator()), floor_props("Elevator Platform"))
    put(21, tile_floor(floor_hcz()), floor_props("Heavy Containment Floor"))

    for base_i, tex, label in ((24, door_standard(), "Foundation Door"), (28, door_containment(), "Containment Door")):
        put(base_i + 0, tile_door(tex, "W", False), door_props("W", True, label))
        put(base_i + 1, tile_door(tex, "N", False), door_props("N", True, label))
        put(base_i + 2, tile_door(tex, "W", True), door_props("W", False, label))
        put(base_i + 3, tile_door(tex, "N", True), door_props("N", False, label))

    pw = wall_pocket()
    put(32, tile_wall(pw, "W"), wall_props("W", SHEET, 32, "Stone"))
    put(33, tile_wall(pw, "N"), wall_props("N", SHEET, 33, "Stone"))
    put(34, tile_wall(pw, "NW"), wall_props("NW", SHEET, 34, "Stone"))
    put(35, tile_floor(floor_pocket(60)), floor_props("Corroded Floor"))
    put(36, tile_floor(floor_pocket(65)), floor_props("Corroded Floor"))
    put(37, tile_floor(floor_pocket_exit()), floor_props("Corroded Floor"))

    signs = [
        ("EZ", text_tex(256, 96, (36, 86, 150, 255), (240, 244, 248, 255), ["ENTRANCE", "ZONE"], (230, 236, 240, 255))),
        ("LCZ", text_tex(256, 96, (232, 186, 28, 255), (20, 20, 20, 255), ["LIGHT", "CONTAINMENT"], (20, 20, 20, 255))),
        ("HCZ", text_tex(256, 96, (165, 40, 32, 255), (245, 240, 235, 255), ["HEAVY", "CONTAINMENT"], (245, 240, 235, 255))),
        ("Logo", logo_tex()),
        ("Danger", danger_tex()),
    ]
    for k, (label, tex) in enumerate(signs):
        put(40 + k, tile_sign(tex, "W"), sign_props("W", "Sign " + label))
        put(48 + k, tile_sign(tex, "N"), sign_props("N", "Sign " + label))
    return tiles


# ----------------------------------------------------------------------
# Output: sheet, pack, tile definitions
# ----------------------------------------------------------------------

def make_sheet(tiles, rows):
    sheet = Image.new("RGBA", (COLS * TW, rows * TH), (0, 0, 0, 0))
    for i, (img, _) in tiles.items():
        sheet.alpha_composite(img, ((i % COLS) * TW, (i // COLS) * TH))
    return sheet


def sheet_entries(sheet_img, name, cols, rows):
    out = []
    for i in range(cols * rows):
        c, r = i % cols, i // cols
        t = sheet_img.crop((c * TW, r * TH, c * TW + TW, r * TH + TH))
        bb = t.getbbox()
        if bb:
            out.append((f"{name}_{i}", t.crop(bb), bb[0], bb[1]))
    return out


def write_pack(path, entries, page_name="scp_facility"):
    # shelf packing on one page
    W = 2048
    x = y = shelf = 0
    placed = []
    for name, img, ox, oy in sorted(entries, key=lambda e: -e[1].size[1]):
        w, h = img.size
        if x + w > W:
            x, y, shelf = 0, y + shelf + 1, 0
        placed.append((name, img, x, y, ox, oy))
        x += w + 1
        shelf = max(shelf, h)
    H = 1
    while H < y + shelf + 1:
        H *= 2
    page = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for name, img, px, py, ox, oy in placed:
        page.paste(img, (px, py))
    import io
    buf = io.BytesIO()
    page.save(buf, "PNG", optimize=True)
    png = buf.getvalue()

    def s(v):
        b = v.encode()
        return struct.pack("<i", len(b)) + b

    out = b"PZPK" + struct.pack("<ii", 1, 1) + s(page_name)
    out += struct.pack("<ii", len(placed), 1)
    for name, img, px, py, ox, oy in placed:
        w, h = img.size
        out += s(name) + struct.pack("<8i", px, py, w, h, ox, oy, TW, TH)
    out += struct.pack("<i", len(png)) + png
    with open(path, "wb") as f:
        f.write(out)
    return page


def read_tiles_def(path):
    """Reads the existing .tiles file (tdef v1) -> list of sheets."""
    b = open(path, "rb").read()
    p = 0

    def i32():
        nonlocal p
        v = struct.unpack_from("<i", b, p)[0]
        p += 4
        return v

    def line():
        nonlocal p
        e = b.index(b"\n", p)
        v = b[p:e].decode()
        p = e + 1
        return v

    assert b[:4] == b"tdef"
    p = 4
    i32()
    n = i32()
    sheets = []
    for _ in range(n):
        name, img = line(), line()
        w, h, num, count = i32(), i32(), i32(), i32()
        props = []
        for _ in range(count):
            k = i32()
            props.append([(line(), line()) for _ in range(k)])
        sheets.append({"name": name, "image": img, "w": w, "h": h, "num": num, "props": props})
    return sheets


def write_tiles_def(path, sheets):
    out = b"tdef" + struct.pack("<ii", 1, len(sheets))
    for sh in sheets:
        out += (sh["name"] + "\n" + sh["image"] + "\n").encode()
        out += struct.pack("<iiii", sh["w"], sh["h"], sh["num"], sh["w"] * sh["h"])
        for i in range(sh["w"] * sh["h"]):
            props = sh["props"][i] if i < len(sh["props"]) else []
            out += struct.pack("<i", len(props))
            for k, v in props:
                out += (k + "\n" + v + "\n").encode()
    out += b"\x00" * 28
    with open(path, "wb") as f:
        f.write(out)


def preview(tiles):
    """A small room: floor, walls with a door, a sign, rendered at 1x."""
    W, H = 900, 640
    img = Image.new("RGBA", (W, H), (24, 24, 26, 255))

    def at(i, tx, ty):
        t = tiles[i][0]
        sx = W // 2 - 64 + (tx - ty) * 64
        sy = 80 + (tx + ty) * 32
        img.alpha_composite(t, (sx, sy))

    n = 5
    for ty in range(n):
        for tx in range(n):
            at(13 if (tx + ty) % 3 else 14, tx, ty)
    for ty in range(n):
        at(8 if ty != 2 else 11, 0, ty)
    for tx in range(1, n):
        at(9 if tx != 3 else 12, tx, 0)
    at(10, 0, 0)
    at(28, 0, 2)
    at(25, 3, 0)
    at(49, 1, 0)
    at(44, 0, 4)
    return img


def main():
    tiles = build_tiles()
    rows = 7
    sheet = make_sheet(tiles, rows)
    os.makedirs(ART, exist_ok=True)
    sheet.save(os.path.join(ART, SHEET + "_tilesheet.png"))
    preview(tiles).save(os.path.join(ART, SHEET + "_preview.png"))

    old_sheet = Image.open(os.path.join(ART, "scp_facility_01_tilesheet.png")).convert("RGBA")
    entries = sheet_entries(old_sheet, "scp_facility_01", 8, 2) + sheet_entries(sheet, SHEET, COLS, rows)
    write_pack(os.path.join(MEDIA, "texturepacks", "scp_facility.pack"), entries)

    tdef_path = os.path.join(MEDIA, "scp_facility.tiles")
    sheets = [s for s in read_tiles_def(tdef_path) if s["name"] != SHEET]
    props = [tiles[i][1] if i in tiles else [] for i in range(COLS * rows)]
    sheets.append({"name": SHEET, "image": SHEET + ".png", "w": COLS, "h": rows, "num": 2, "props": props})
    write_tiles_def(tdef_path, sheets)
    print("tiles:", len(tiles), "pack entries:", len(entries))


if __name__ == "__main__":
    sys.exit(main())
