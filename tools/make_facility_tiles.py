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
(previews of the site are made by tools/make_site_preview.py)

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
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
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
# Material textures. The surfaces come from SCP - Containment Breach
# (art/cb_textures, CC BY-SA 3.0); stripes, signs and props are drawn here.
# ----------------------------------------------------------------------

WALL_W, WALL_H = 256, 512
CB = os.path.join(ART, "cb_textures")


def cb(name, size, crop=None, bright=1.0, tint=None):
    """A Containment Breach texture as a float RGBA array of `size` (w, h)."""
    im = Image.open(os.path.join(CB, name + ".jpg")).convert("RGB")
    if crop:
        w, h = im.size
        im = im.crop((int(crop[0] * w), int(crop[1] * h), int(crop[2] * w), int(crop[3] * h)))
    im = im.resize(size, Image.LANCZOS)
    a = np.zeros((size[1], size[0], 4), np.float32)
    a[..., :3] = np.asarray(im).astype(np.float32) * bright
    if tint is not None:
        a[..., :3] *= np.array(tint, np.float32)
    a[..., 3] = 255
    return a


def wall_ez():
    a = cb("officewall", (WALL_W, WALL_H))
    grime(a, 14, 0.15)
    return to_img(a)


def wall_lcz():
    a = cb("whitewall", (WALL_W, WALL_H))
    rect(a, 0, 0.955, 1, 1, "#2e2f30")
    grime(a, 16, 0.2)
    return to_img(a)


def wall_hcz():
    a = cb("concretewall", (WALL_W, WALL_H), bright=0.68)      # kept dark, as asked
    rect(a, 0, 0.0, 1, 0.035, "#2a2c2e")
    rect(a, 0, 0.46, 1, 0.485, "#7d2a20", 0.8)         # red warning band
    rect(a, 0, 0.955, 1, 1, "#222425")
    grime(a, 30, 0.3)
    drips(a, 5, "#2a2620", 0.25, 33)
    return to_img(a)


def wall_cell():
    a = cb("metalpanels", (WALL_W, WALL_H), bright=0.9)
    hazard(a, 0, 0.9, 1, 0.955, period=30)
    rect(a, 0, 0.955, 1, 1, "#1f2122")
    rect(a, 0, 0.0, 1, 0.03, "#1f2122")
    grime(a, 20, 0.25)
    return to_img(a)


def wall_bunker():
    a = cb("concretemoss", (WALL_W, WALL_H), bright=1.05)
    rect(a, 0, 0.0, 1, 0.03, "#2a2c2e")
    return to_img(a)


def wall_perimeter():
    a = cb("concretewall", (WALL_W, WALL_H), bright=1.08)
    hazard(a, 0, 0.0, 1, 0.05, period=30)
    vline(a, 0.0, 0.02, "#4a4c4e")
    vline(a, 1.0, 0.02, "#4a4c4e")
    grime(a, 30, 0.3)
    return to_img(a)


def wall_pocket():
    a = cb("rockmoss", (WALL_W, WALL_H), bright=1.5)
    b = cb("pdwall", (WALL_W, WALL_H), bright=0.9)
    k = np.clip((noise(WALL_W, WALL_H, 40, 1, 41) + 0.2), 0, 1)[..., None] * 0.45
    a[..., :3] = a[..., :3] * (1 - k) + b[..., :3] * k
    drips(a, 10, "#050505", 0.6, 42)
    grime(a, 30, 0.4)
    return to_img(a)


def cap_tex(color):
    return to_img(base(64, 64, color, 4, 4))


FLOOR = 256


def floor_ez():        # white tiles (rooms, Entrance Zone)
    return to_img(cb("tilefloor", (FLOOR, FLOOR), crop=(0, 0, 1 / 3, 1 / 3)))


def floor_lcz():       # dark concrete of the Containment Breach hallways
    a = cb("concretefloor", (FLOOR, FLOOR), bright=1.45)
    return to_img(a)


def floor_hcz():       # stained steel plate
    a = cb("dirtymetal", (FLOOR, FLOOR), crop=(0, 0, 0.5, 0.5), bright=0.62)
    for i in (0, 1):
        hline(a, i, 0.012, "#232526")
        vline(a, i, 0.012, "#232526")
    return to_img(a)


def floor_grate():
    a = cb("metal3", (FLOOR, FLOOR), bright=1.25)
    for u0, v0, u1, v1 in ((0, 0, 1, 0.03), (0, 0.97, 1, 1), (0, 0, 0.03, 1), (0.97, 0, 1, 1)):
        rect(a, u0, v0, u1, v1, "#4f5458")
    return to_img(a)


def floor_elevator():
    a = cb("dirtymetal", (FLOOR, FLOOR), bright=0.8)
    hazard(a, 0.05, 0.05, 0.95, 0.95, period=48)
    b = cb("metal3", (FLOOR, FLOOR), bright=1.3)
    s = slice(int(0.18 * FLOOR), int(0.82 * FLOOR))
    a[s, s] = b[s, s]
    return to_img(a)


def floor_hazard_line():
    a = cb("concretefloor", (FLOOR, FLOOR), bright=1.45)
    hazard(a, 0, 0.36, 1, 0.64, period=40)
    return to_img(a)


def floor_asphalt():
    a = cb("concretefloor", (FLOOR, FLOOR), bright=1.0)
    a[..., :3] += noise(FLOOR, FLOOR, 30, 8, 75)[..., None]
    return to_img(a)


def floor_slab():
    a = cb("concretefloor", (FLOOR, FLOOR), bright=2.0)
    for i in (0, 1):
        hline(a, i, 0.01, "#3c3e3f")
        vline(a, i, 0.01, "#3c3e3f")
    return to_img(a)


def floor_roof():
    a = base(FLOOR, FLOOR, "#3a3c3d", 14, 10, 77)
    for i in (0, 1):
        hline(a, i, 0.01, "#2a2b2c")
    return to_img(a)


def floor_pocket(seed):
    g = np.random.default_rng(seed)
    u, v = g.random() * 0.5, g.random() * 0.5
    a = cb("rockmoss", (FLOOR, FLOOR), crop=(u, v, u + 0.5, v + 0.5), bright=1.7)
    return to_img(a)


def floor_pocket_exit():
    a = np.asarray(floor_pocket(70)).astype(np.float32)
    yy, xx = np.mgrid[0:FLOOR, 0:FLOOR]
    d = np.sqrt((xx - FLOOR / 2) ** 2 + (yy - FLOOR / 2) ** 2) / (FLOOR / 2)
    ring = np.exp(-((d - 0.55) ** 2) / 0.01) + 0.5 * np.exp(-(d ** 2) / 0.08)
    a[..., :3] += ring[..., None] * np.array([120, 150, 110])
    return to_img(a)


DOOR_W, DOOR_H = 256, 336


def door_standard():
    a = cb("Door01", (DOOR_W, DOOR_H), crop=(0.40, 0.02, 0.76, 0.86), bright=1.35)
    rect(a, 0, 0.955, 1, 1, "#1c1d1e")
    return to_img(a)


def door_containment():
    a = cb("containment_doors", (DOOR_W, DOOR_H), crop=(0.01, 0.13, 0.58, 0.86), bright=1.15)
    hazard(a, 0, 0.93, 1, 1, period=30)
    return to_img(a)


def gate_tex():
    a = cb("containment_doors", (256, 512), crop=(0.60, 0.06, 0.98, 0.84), bright=1.2)
    rect(a, 0, 0.0, 1, 0.06, "#8f2f24", 0.8)
    hazard(a, 0, 0.84, 1, 0.96, period=44)
    rect(a, 0, 0.96, 1, 1, "#1c1d1e")
    for u in (0.0, 1.0):
        vline(a, u, 0.03, "#26282a")
    bolts(a, [(u, v) for u in (0.08, 0.92) for v in (0.12, 0.3, 0.5, 0.7)], 5, "#1e2022")
    return to_img(a)


def frame_trim(a, a0, b0, top, reader=True):
    """Steel frame around the door opening [a0, b0] x [top, 1] in texture coords,
    then cuts the opening (alpha 0)."""
    t = 0.045
    rect(a, a0 - t, top - t * 0.9, b0 + t, 1, "#3d4144")
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
# More tile builders: corner posts, the main gate, wall fittings, furniture
# ----------------------------------------------------------------------

def tile_pillar(tex):
    """Small post where a north wall and a west wall meet at the far corner."""
    img = canvas()
    t = WALL_T
    strip = tex.crop((0, 0, 24, tex.size[1]))
    face(img, cap_tex("#2c2f31"), (0, 0, 1), (t, 0, 1), (0, t, 1))
    face(img, strip, (0, t, 1), (t, t, 1), (0, t, 0), 1.0)
    face(img, strip, (t, t, 1), (t, 0, 1), (t, t, 0), 0.86)
    return finish(img)


def tile_gate(tex, side, opened):
    """One tile of the big sliding gate (full tile wide, full wall height)."""
    img = canvas()
    d0, d1 = 0.0, 0.1
    rail = to_img(base(64, 16, "#1c1d1e", 3, 3))
    if opened:
        if side == "W":
            face(img, rail, (d0, 0, 0.004), (d1, 0, 0.004), (d0, 1, 0.004))
        else:
            face(img, rail, (0, d0, 0.004), (1, d0, 0.004), (0, d1, 0.004))
        return finish(img)
    cap = cap_tex("#1e2022")
    if side == "W":
        face(img, cap, (d0, 0, 1), (d0, 1, 1), (d1, 0, 1))
        face(img, tex, (d1, 1, 1), (d1, 0, 1), (d1, 1, 0), 0.86)
    else:
        face(img, cap, (0, d0, 1), (1, d0, 1), (0, d1, 1))
        face(img, tex, (0, d1, 1), (1, d1, 1), (0, d1, 0), 1.0)
    return finish(img)


def tile_overlay(tex, side, z0, z1, a0=0.0, b0=1.0, out=0.02):
    """Flat fitting on a wall (pipes, vent)."""
    img = canvas()
    off = WALL_T + out
    if side == "W":
        face(img, tex, (off, b0, z1), (off, a0, z1), (off, b0, z0), 0.9)
    else:
        face(img, tex, (a0, off, z1), (b0, off, z1), (a0, off, z0), 1.0)
    return finish(img)


def box(img, facing, x0, y0, x1, y1, z0, z1, top, front, side):
    """A box standing against the north wall (facing 'n': its front looks south)
    or against the west wall (facing 'w': same box turned, front looks east)."""
    if facing == "n":
        face(img, top, (x0, y0, z1), (x1, y0, z1), (x0, y1, z1), 1.0)
        face(img, front, (x0, y1, z1), (x1, y1, z1), (x0, y1, z0), 1.0)
        face(img, side, (x1, y1, z1), (x1, y0, z1), (x1, y1, z0), 0.8)
    else:
        x0, y0, x1, y1 = y0, x0, y1, x1
        face(img, top, (x0, y1, z1), (x0, y0, z1), (x1, y1, z1), 1.0)
        face(img, side, (x0, y1, z1), (x1, y1, z1), (x0, y1, z0), 1.0)
        face(img, front, (x1, y1, z1), (x1, y0, z1), (x1, y1, z0), 0.86)


def metal_tex(w, h, color, seed):
    a = cb("metal", (w, h), bright=1.0)
    c = hexrgb(color) / 190.0
    a[..., :3] *= c
    a[..., :3] += noise(w, h, 3, 5, seed)[..., None]
    return a


def prop_locker(f):
    img = canvas()
    fr = metal_tex(256, 256, "#7d8a92", 1)
    for u in (0.0, 0.5):
        rect(fr, u + 0.02, 0.03, u + 0.48, 0.97, "#6f7c85")
        for v in (0.1, 0.14, 0.18):
            rect(fr, u + 0.12, v, u + 0.38, v + 0.02, "#2a2e31")
        rect(fr, u + 0.40, 0.5, u + 0.44, 0.56, "#1e2022")
    vline(fr, 0.5, 0.02, "#30353a")
    plain = to_img(metal_tex(64, 128, "#6b767d", 2))
    box(img, f, 0.08, 0.05, 0.92, 0.4, 0, 0.74, plain, to_img(fr), plain)
    return finish(img)


def prop_shelf(f):
    img = canvas()
    fr = base(256, 256, "#15171a", 3, 3, 3)
    g = np.random.default_rng(31)
    for k in range(4):
        v = 0.04 + k * 0.24
        rect(fr, 0, v + 0.2, 1, v + 0.24, "#59616a")
        u = 0.05
        while u < 0.85:
            w = 0.1 + g.random() * 0.14
            col = ["#8a6f4a", "#6b7d5a", "#7a7f86", "#93876b", "#5a6b80"][int(g.random() * 5)]
            h = 0.08 + g.random() * 0.1
            rect(fr, u, v + 0.2 - h, min(0.95, u + w), v + 0.2, col)
            u += w + 0.03
    for u in (0.0, 0.97):
        rect(fr, u, 0, u + 0.03, 1, "#59616a")
    plain = to_img(metal_tex(64, 128, "#59616a", 4))
    box(img, f, 0.06, 0.05, 0.94, 0.38, 0, 0.8, plain, to_img(fr), plain)
    return finish(img)


def prop_desk(f):
    img = canvas()
    top = to_img(metal_tex(128, 96, "#9a9c98", 5))
    fr = metal_tex(256, 96, "#70757a", 6)
    rect(fr, 0.04, 0.1, 0.3, 0.9, "#5d6268")
    rect(fr, 0.34, 0.1, 0.96, 0.9, "#0e0f10")
    plain = to_img(metal_tex(64, 64, "#63686d", 7))
    box(img, f, 0.05, 0.08, 0.95, 0.6, 0, 0.3, top, to_img(fr), plain)
    scr = base(128, 96, "#b9b4a2", 4, 4, 8)
    rect(scr, 0.1, 0.1, 0.9, 0.82, "#0c1f12")
    for v in (0.2, 0.32, 0.44, 0.56):
        rect(scr, 0.16, v, 0.16 + 0.5 * ((v * 7) % 1 + 0.3) / 1.3, v + 0.05, "#3ddc6a")
    beige = to_img(base(64, 64, "#a9a493", 4, 4, 9))
    box(img, f, 0.34, 0.14, 0.66, 0.4, 0.3, 0.52, beige, to_img(scr), beige)
    return finish(img)


def prop_crate(f):
    img = canvas()
    fr = base(256, 256, "#5a6048", 8, 12, 10)
    for u0, v0, u1, v1 in ((0, 0, 1, 0.07), (0, 0.93, 1, 1), (0, 0, 0.07, 1), (0.93, 0, 1, 1)):
        rect(fr, u0, v0, u1, v1, "#3b4030")
    lab = np.asarray(text_tex(160, 60, (0, 0, 0, 0), (225, 225, 210, 255), ["SCP"])).astype(np.float32)
    m = lab[..., 3:4] / 255
    fr[98:158, 48:208, :3] = fr[98:158, 48:208, :3] * (1 - m) + lab[..., :3] * m
    t = to_img(fr)
    box(img, f, 0.14, 0.12, 0.86, 0.84, 0, 0.44, t, t, t)
    return finish(img)


def prop_barrel(f):
    img = Image.new("RGBA", (TW * SS, TH * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx, cy = proj(0.5, 0.5, 0)
    rx, ry, hgt = 0.3 * 64 * SS * 1.41, 0.3 * 32 * SS * 1.41, 0.46 * 192 * SS
    body = (212, 168, 30, 255) if f == "n" else (58, 92, 128, 255)
    dark = tuple(int(c * 0.6) for c in body[:3]) + (255,)
    d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=dark)
    d.rectangle([cx - rx, cy - hgt, cx + rx, cy], fill=body)
    d.rectangle([cx + rx * 0.35, cy - hgt, cx + rx, cy], fill=dark)
    for k in (0.33, 0.66):
        d.arc([cx - rx, cy - hgt * k - ry, cx + rx, cy - hgt * k + ry], 0, 180, fill=(30, 30, 30, 255), width=3 * SS)
    d.ellipse([cx - rx, cy - hgt - ry, cx + rx, cy - hgt + ry], fill=tuple(int(c * 0.8) for c in body[:3]) + (255,),
              outline=(30, 30, 30, 255), width=2 * SS)
    d.ellipse([cx - rx * 0.2, cy - hgt - ry * 0.6, cx + rx * 0.1, cy - hgt - ry * 0.2], fill=(25, 25, 25, 255))
    return finish(img)


def prop_rack(f):
    img = canvas()
    fr = cb("controlpanel", (256, 384), crop=(0.0, 0.0, 0.42, 0.8), bright=1.5)
    g = np.random.default_rng(12)
    for _ in range(26):
        u, v = 0.08 + g.random() * 0.8, 0.05 + g.random() * 0.88
        rect(fr, u, v, u + 0.025, v + 0.012, ["#3ddc6a", "#e0b020", "#d03a2a"][int(g.random() * 3)])
    plain = to_img(metal_tex(64, 128, "#2e3134", 13))
    box(img, f, 0.1, 0.05, 0.9, 0.48, 0, 0.86, plain, to_img(fr), plain)
    return finish(img)


def prop_bed(f):
    img = canvas()
    frame = to_img(metal_tex(64, 32, "#4a4f54", 14))
    box(img, f, 0.06, 0.06, 0.94, 0.52, 0, 0.14, frame, frame, frame)
    mat = base(256, 128, "#b9bdb6", 5, 10, 15)
    rect(mat, 0.0, 0.0, 0.24, 1.0, "#e2e3dd")
    rect(mat, 0.45, 0.0, 1.0, 1.0, "#6f7f74", 0.85)
    side = to_img(base(64, 16, "#a3a79f", 4, 4, 16))
    box(img, f, 0.08, 0.08, 0.92, 0.5, 0.14, 0.22, to_img(mat), side, side)
    return finish(img)


def prop_cabinet(f):
    img = canvas()
    fr = metal_tex(256, 256, "#c9cdc8", 17)
    for k in range(4):
        v = 0.03 + k * 0.24
        rect(fr, 0.04, v, 0.96, v + 0.21, "#b4b9b4")
        rect(fr, 0.4, v + 0.08, 0.6, v + 0.11, "#3a3d40")
    plain = to_img(metal_tex(64, 128, "#aeb3ae", 18))
    box(img, f, 0.16, 0.05, 0.84, 0.4, 0, 0.58, plain, to_img(fr), plain)
    return finish(img)


def prop_console(f):
    img = canvas()
    fr = cb("controlpanel", (256, 160), crop=(0.0, 0.3, 0.42, 0.6), bright=1.6)
    top = cb("controlpanel", (256, 128), crop=(0.0, 0.62, 0.42, 0.82), bright=1.7)
    rect(top, 0.08, 0.15, 0.4, 0.8, "#0c1f12")
    rect(top, 0.12, 0.3, 0.34, 0.4, "#3ddc6a")
    for i, c in enumerate(("#d03a2a", "#e0b020", "#3ddc6a", "#d03a2a")):
        rect(top, 0.5 + i * 0.11, 0.3, 0.57 + i * 0.11, 0.55, c)
    plain = to_img(metal_tex(64, 64, "#3a3e42", 19))
    box(img, f, 0.06, 0.06, 0.94, 0.5, 0, 0.42, to_img(top), to_img(fr), plain)
    return finish(img)


# ----------------------------------------------------------------------
# Exterior of the site: fortress walls, watchtower, roofs, road, stairs
# ----------------------------------------------------------------------

def wall_fort():
    """Pale poured concrete in tall panels, like the compound walls of the reference."""
    a = cb("concretewall", (WALL_W, WALL_H), bright=1.55, tint=(0.97, 0.98, 1.0))
    a[..., :3] = a[..., :3] * 0.55 + 190 * 0.45
    a[..., :3] += noise(WALL_W, WALL_H, 40, 10, 168)[..., None]
    for u in (0.0, 0.5, 1.0):
        vline(a, u, 0.012, "#8e9294")
    hline(a, 0.5, 0.008, "#9a9ea0")
    rect(a, 0, 0.0, 1, 0.025, "#b9bcbd")
    grime(a, 22, 0.22)
    drips(a, 4, "#7c8082", 0.3, 169)
    return to_img(a)


def wall_window():
    """Concrete with a long dark window band (watchtower cabin, main building)."""
    a = np.asarray(wall_fort()).astype(np.float32).copy()
    rect(a, 0.06, 0.22, 0.94, 0.6, "#1d2a33")
    g = np.mgrid[0:WALL_H, 0:WALL_W][1] / WALL_W
    band = (slice(int(0.22 * WALL_H), int(0.6 * WALL_H)), slice(int(0.06 * WALL_W), int(0.94 * WALL_W)))
    a[band][..., :3] += (np.clip(1 - g[band] * 1.6, 0, 1) * 60)[..., None]          # sky reflection
    for u in (0.06, 0.35, 0.65, 0.94):
        vline(a, u, 0.02, "#6f7376")
    rect(a, 0.04, 0.6, 0.96, 0.63, "#8a8e90")
    rect(a, 0.04, 0.2, 0.96, 0.22, "#8a8e90")
    return to_img(a)


PARAPET_H = 0.32


def tile_parapet(tex, side):
    """Low concrete wall (roof edge, watchtower deck): it can be climbed over."""
    img = canvas()
    low = tex.crop((0, int(tex.size[1] * (1 - PARAPET_H)), tex.size[0], tex.size[1]))
    cap = cap_tex("#a8acae")
    t = WALL_T * 1.6
    h = PARAPET_H
    if side == "W":
        face(img, cap, (0, 0, h), (0, 1, h), (t, 0, h))
        face(img, low, (t, 1, h), (t, 0, h), (t, 1, 0), 0.86)
    else:
        face(img, cap, (0, 0, h), (1, 0, h), (0, t, h))
        face(img, low, (0, t, h), (1, t, h), (0, t, 0), 1.0)
    return finish(img)


def tile_stairs(side, piece):
    """One third of a concrete staircase (3 steps). side 'N': climbs north,
    side 'W': climbs west. piece 0 = bottom, 1 = middle, 2 = top."""
    img = canvas()
    tread = to_img(base(128, 64, "#a9adaf", 6, 6, 180 + piece))
    riser = base(128, 64, "#8d9193", 6, 6, 183 + piece)
    hazard(riser, 0, 0, 1, 0.12, period=20)
    riser = to_img(riser)
    side_t = to_img(base(64, 64, "#7d8183", 6, 6, 186))
    for k in (2, 1, 0):             # far (high) steps first
        top = (piece * 3 + k + 1) / 9
        a0, a1 = 1 - (k + 1) / 3, 1 - k / 3
        if side == "N":
            box(img, "n", 0.04, a0, 0.96, a1, 0, top, tread, riser, side_t)
        else:
            box(img, "w", 0.04, a0, 0.96, a1, 0, top, tread, riser, side_t)
    return finish(img)


def prop_solar(f):
    img = canvas()
    pan = base(256, 192, "#1f3550", 4, 8, 190)
    for k in range(1, 6):
        vline(pan, k / 6, 0.012, "#9fb2c4")
    for k in range(1, 4):
        hline(pan, k / 4, 0.014, "#9fb2c4")
    for u0, v0, u1, v1 in ((0, 0, 1, 0.03), (0, 0.97, 1, 1), (0, 0, 0.02, 1), (0.98, 0, 1, 1)):
        rect(pan, u0, v0, u1, v1, "#c9ced2")
    pan[..., :3] += (np.mgrid[0:192, 0:256][1] / 256.0 * 40)[..., None]
    leg = to_img(base(16, 64, "#5d6164", 3, 3, 191))
    if f == "n":     # tilted towards the south
        for x in (0.15, 0.82):
            box(img, "n", x, 0.25, x + 0.04, 0.29, 0, 0.42, leg, leg, leg)
        face(img, to_img(pan), (0.06, 0.2, 0.48), (0.94, 0.2, 0.48), (0.06, 0.88, 0.14))
    else:            # tilted towards the east
        for y in (0.15, 0.82):
            box(img, "n", 0.25, y, 0.29, y + 0.04, 0, 0.42, leg, leg, leg)
        face(img, to_img(pan), (0.2, 0.94, 0.48), (0.2, 0.06, 0.48), (0.88, 0.94, 0.14), 0.9)
    return finish(img)


def prop_fan(f):
    """Rooftop ventilation unit: a round fan housing on a concrete base."""
    img = canvas()
    slab = to_img(base(64, 64, "#9a9ea0", 5, 5, 192))
    box(img, "n", 0.04, 0.04, 0.96, 0.96, 0, 0.08, slab, slab, slab)
    big = Image.new("RGBA", (TW * SS, TH * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    cx, cy = proj(0.5, 0.5, 0.08)
    rx, ry, hgt = 0.4 * 64 * SS * 1.41, 0.4 * 32 * SS * 1.41, 0.22 * 192 * SS
    d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=(92, 96, 99, 255))
    d.rectangle([cx - rx, cy - hgt, cx + rx, cy], fill=(150, 154, 157, 255))
    d.rectangle([cx + rx * 0.3, cy - hgt, cx + rx, cy], fill=(118, 122, 125, 255))
    top = cy - hgt
    d.ellipse([cx - rx, top - ry, cx + rx, top + ry], fill=(40, 42, 44, 255), outline=(175, 178, 180, 255), width=3 * SS)
    for k in range(6):
        ang = math.radians(k * 60 + 15)
        d.line([(cx, top), (cx + math.cos(ang) * rx * 0.9, top + math.sin(ang) * ry * 0.9)],
               fill=(120, 124, 126, 255), width=4 * SS)
    d.ellipse([cx - rx * 0.15, top - ry * 0.15, cx + rx * 0.15, top + ry * 0.15], fill=(160, 164, 166, 255))
    img.alpha_composite(big)
    return finish(img)


def prop_floodlight(f):
    img = canvas()
    pole = to_img(base(16, 128, "#4b4f52", 3, 3, 193))
    box(img, "n", 0.46, 0.46, 0.54, 0.54, 0, 0.92, pole, pole, pole)
    head = base(64, 32, "#2b2e30", 3, 3, 194)
    lamp = base(64, 32, "#fff3c4", 3, 3, 195)
    rect(lamp, 0, 0, 1, 0.12, "#2b2e30")
    if f == "n":
        box(img, "n", 0.3, 0.4, 0.7, 0.58, 0.86, 0.98, to_img(head), to_img(lamp), to_img(head))
    else:
        box(img, "w", 0.3, 0.4, 0.7, 0.58, 0.86, 0.98, to_img(head), to_img(lamp), to_img(head))
    return finish(img)


def prop_barrier(f):
    """Concrete road barrier with red and white stripes."""
    img = canvas()
    c = base(256, 64, "#b7babb", 6, 6, 196)
    for k in range(4):
        rect(c, k * 0.25 + 0.02, 0.15, k * 0.25 + 0.12, 0.55, "#b8322a")
    top = to_img(base(128, 32, "#aeb1b2", 5, 5, 197))
    end = to_img(base(32, 64, "#9ea1a2", 5, 5, 198))
    box(img, f, 0.02, 0.36, 0.98, 0.64, 0, 0.3, top, to_img(c), end)
    return finish(img)


def tile_wire(side):
    """Coils of barbed wire on top of a wall (stands on the square above the wall)."""
    img = Image.new("RGBA", (TW * SS, TH * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for k in range(9):
        a = (k + 0.5) / 9
        p = (WALL_T / 2, 1 - a, 0.08) if side == "W" else (a, WALL_T / 2, 0.08)
        cx, cy = proj(*p)
        r = 0.07 * 192 * SS
        d.ellipse([cx - r * 0.8, cy - r, cx + r * 0.8, cy + r], outline=(70, 74, 78, 255), width=2 * SS)
    for z in (0.02, 0.14):
        a0 = (WALL_T / 2, 1, z) if side == "W" else (0, WALL_T / 2, z)
        a1 = (WALL_T / 2, 0, z) if side == "W" else (1, WALL_T / 2, z)
        d.line([proj(*a0), proj(*a1)], fill=(60, 63, 66, 255), width=SS)
    return finish(img)


def wood_tex(w, h, color, seed):
    a = base(w, h, color, 6, 6, seed)
    yy = np.mgrid[0:h, 0:w][0]
    a[..., :3] += (np.sin(yy / 3.0 + noise(w, h, 8, 3, seed)) * 6)[..., None]
    return a


def prop_chair(f):
    img = canvas()
    leg = to_img(base(8, 32, "#2f3235", 2, 2, 210))
    seat = to_img(base(64, 64, "#3c5a7a", 5, 5, 211))
    for lx, ly in ((0.32, 0.38), (0.6, 0.38), (0.32, 0.66), (0.6, 0.66)):
        box(img, f, lx, ly, lx + 0.05, ly + 0.05, 0, 0.2, leg, leg, leg)
    box(img, f, 0.3, 0.36, 0.68, 0.72, 0.2, 0.25, seat, seat, seat)
    box(img, f, 0.3, 0.3, 0.68, 0.36, 0.2, 0.5, seat, seat, seat)
    return finish(img)


def prop_table(f):
    img = canvas()
    leg = to_img(base(8, 32, "#3a3d40", 2, 2, 212))
    top = to_img(wood_tex(128, 96, "#b7b2a6", 213))
    for lx, ly in ((0.12, 0.12), (0.82, 0.12), (0.12, 0.82), (0.82, 0.82)):
        box(img, f, lx, ly, lx + 0.05, ly + 0.05, 0, 0.27, leg, leg, leg)
    box(img, f, 0.08, 0.08, 0.92, 0.92, 0.27, 0.31, top, top, top)
    return finish(img)


def prop_sofa(f):
    img = canvas()
    c = to_img(base(96, 64, "#5b3a33", 6, 8, 214))
    d = to_img(base(96, 64, "#4a2f29", 6, 8, 215))
    box(img, f, 0.05, 0.12, 0.95, 0.62, 0, 0.16, c, d, d)
    box(img, f, 0.05, 0.08, 0.95, 0.24, 0.16, 0.42, c, c, d)
    for x in (0.05, 0.85):
        box(img, f, x, 0.12, x + 0.1, 0.62, 0.16, 0.28, c, d, d)
    return finish(img)


def prop_vending(f):
    img = canvas()
    fr = base(256, 384, "#8d1e22", 5, 6, 216)
    rect(fr, 0.08, 0.06, 0.7, 0.72, "#1a2026")
    g = np.random.default_rng(217)
    for r in range(5):
        for c in range(4):
            col = ["#e0b020", "#3d9be0", "#d03a2a", "#3ddc6a", "#e8e8e8"][int(g.random() * 5)]
            rect(fr, 0.12 + c * 0.14, 0.1 + r * 0.12, 0.22 + c * 0.14, 0.18 + r * 0.12, col)
    rect(fr, 0.76, 0.2, 0.92, 0.3, "#c9ccce")
    rect(fr, 0.76, 0.34, 0.92, 0.5, "#111111")
    rect(fr, 0.1, 0.8, 0.68, 0.9, "#0d0d0d")
    side = to_img(base(64, 128, "#6e1619", 4, 4, 218))
    box(img, f, 0.1, 0.06, 0.9, 0.5, 0, 0.9, side, to_img(fr), side)
    return finish(img)


def prop_plant(f):
    img = canvas()
    pot = to_img(base(32, 32, "#8a5a3c", 4, 4, 219))
    box(img, "n", 0.38, 0.38, 0.62, 0.62, 0, 0.18, pot, pot, pot)
    big = Image.new("RGBA", (TW * SS, TH * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    g = np.random.default_rng(220 + (1 if f == "w" else 0))
    cx, cy = proj(0.5, 0.5, 0.18)
    for _ in range(14):
        a = g.random() * math.pi * 2
        r = (0.3 + g.random() * 0.7) * 26 * SS
        h = (0.2 + g.random() * 0.5) * 120 * SS
        px, py = cx + math.cos(a) * r, cy - h
        col = (40 + int(g.random() * 30), 110 + int(g.random() * 60), 40 + int(g.random() * 20), 255)
        d.line([(cx, cy), (px, py)], fill=(50, 90, 40, 255), width=2 * SS)
        d.ellipse([px - 9 * SS, py - 5 * SS, px + 9 * SS, py + 5 * SS], fill=col)
    img.alpha_composite(big)
    return finish(img)


def prop_cooler(f):
    img = canvas()
    body = base(128, 192, "#d9dbd7", 4, 4, 221)
    rect(body, 0.3, 0.25, 0.42, 0.32, "#3d6fd0")
    rect(body, 0.58, 0.25, 0.7, 0.32, "#d03a2a")
    side = to_img(base(64, 96, "#c3c5c1", 4, 4, 222))
    box(img, f, 0.32, 0.12, 0.68, 0.42, 0, 0.5, side, to_img(body), side)
    big = Image.new("RGBA", (TW * SS, TH * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    cx, cy = proj(0.5, 0.27, 0.5)
    d.rectangle([cx - 18 * SS, cy - 52 * SS, cx + 18 * SS, cy], fill=(120, 180, 230, 200))
    d.ellipse([cx - 18 * SS, cy - 60 * SS, cx + 18 * SS, cy - 44 * SS], fill=(150, 200, 240, 220))
    img.alpha_composite(big)
    return finish(img)


def prop_bunkbed(f):
    img = canvas()
    frame = to_img(metal_tex(64, 32, "#4a4f54", 223))
    mat = base(256, 128, "#b9bdb6", 5, 10, 224)
    rect(mat, 0.0, 0.0, 0.24, 1.0, "#e2e3dd")
    rect(mat, 0.45, 0.0, 1.0, 1.0, "#55657a", 0.85)
    side = to_img(base(64, 16, "#a3a79f", 4, 4, 225))
    for z in (0.0, 0.42):
        box(img, f, 0.06, 0.06, 0.94, 0.52, z, z + 0.1, frame, frame, frame)
        box(img, f, 0.08, 0.08, 0.92, 0.5, z + 0.1, z + 0.16, to_img(mat), side, side)
    for x in (0.06, 0.9):
        box(img, f, x, 0.48, x + 0.04, 0.52, 0, 0.62, frame, frame, frame)
    return finish(img)


def prop_medbed(f):
    img = canvas()
    frame = to_img(metal_tex(64, 32, "#c9ccce", 226))
    box(img, f, 0.1, 0.06, 0.9, 0.54, 0, 0.24, frame, frame, frame)
    mat = base(256, 128, "#e8eae6", 3, 5, 227)
    rect(mat, 0.0, 0.0, 0.24, 1.0, "#ffffff")
    rect(mat, 0.4, 0.0, 1.0, 1.0, "#8fb3c9", 0.8)
    side = to_img(base(64, 16, "#d5d8d4", 3, 3, 228))
    box(img, f, 0.12, 0.08, 0.88, 0.52, 0.24, 0.3, to_img(mat), side, side)
    rail = to_img(base(16, 16, "#7d8287", 2, 2, 229))
    box(img, f, 0.12, 0.5, 0.88, 0.53, 0.3, 0.38, rail, rail, rail)
    return finish(img)


def prop_labbench(f):
    img = canvas()
    fr = metal_tex(256, 128, "#d8dbd6", 230)
    for u in (0.04, 0.36, 0.68):
        rect(fr, u, 0.15, u + 0.28, 0.85, "#c4c8c3")
        rect(fr, u + 0.11, 0.25, u + 0.17, 0.3, "#3a3d40")
    top = to_img(base(128, 96, "#1f2326", 3, 3, 231))
    side = to_img(metal_tex(64, 64, "#c0c4bf", 232))
    box(img, f, 0.04, 0.12, 0.96, 0.6, 0, 0.32, top, to_img(fr), side)
    big = Image.new("RGBA", (TW * SS, TH * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    for i, (x, col) in enumerate(((0.25, (90, 220, 120, 210)), (0.45, (80, 160, 240, 210)), (0.7, (230, 90, 70, 210)))):
        p = (x, 0.36, 0.32) if f == "n" else (0.36, x, 0.32)
        cx, cy = proj(*p)
        d.rectangle([cx - 4 * SS, cy - 22 * SS, cx + 4 * SS, cy], fill=(220, 235, 240, 180))
        d.rectangle([cx - 4 * SS, cy - 10 * SS, cx + 4 * SS, cy], fill=col)
    img.alpha_composite(big)
    return finish(img)


def prop_whiteboard(f):
    img = canvas()
    b = base(256, 160, "#f2f3f0", 2, 3, 233)
    for k in range(5):
        rect(b, 0.08, 0.15 + k * 0.14, 0.08 + 0.3 + (k * 0.37) % 0.5, 0.18 + k * 0.14, ["#2a4fb0", "#b02a2a", "#222"][k % 3])
    for u0, v0, u1, v1 in ((0, 0, 1, 0.04), (0, 0.96, 1, 1), (0, 0, 0.02, 1), (0.98, 0, 1, 1)):
        rect(b, u0, v0, u1, v1, "#9aa0a5")
    leg = to_img(base(8, 64, "#7d8287", 2, 2, 234))
    for x in (0.12, 0.84):
        box(img, f, x, 0.2, x + 0.04, 0.24, 0, 0.32, leg, leg, leg)
    side = to_img(base(16, 64, "#c9ccce", 2, 2, 235))
    box(img, f, 0.08, 0.18, 0.92, 0.22, 0.32, 0.84, side, to_img(b), side)
    return finish(img)


def prop_trash(f):
    img = canvas()
    t = to_img(metal_tex(64, 64, "#5f6a63", 236))
    box(img, f, 0.36, 0.36, 0.64, 0.64, 0, 0.26, to_img(base(32, 32, "#1d1f1e", 2, 2, 237)), t, t)
    return finish(img)


def prop_workstation(f):
    """Scientist's desk: wooden top, drawers, flat screen, keyboard, papers, a mug."""
    img = canvas()
    top = to_img(wood_tex(128, 96, "#a88a62", 240))
    fr = wood_tex(256, 96, "#8c7050", 241)
    for v in (0.12, 0.42, 0.72):
        rect(fr, 0.66, v, 0.95, v + 0.24, "#7a6044")
        rect(fr, 0.77, v + 0.1, 0.84, v + 0.13, "#2a2522")
    rect(fr, 0.05, 0.1, 0.6, 0.95, "#3a2e22")
    side = to_img(wood_tex(64, 64, "#7d6346", 242))
    box(img, f, 0.03, 0.1, 0.97, 0.62, 0, 0.3, top, to_img(fr), side)
    scr = base(160, 100, "#1c1e20", 2, 2, 243)
    rect(scr, 0.05, 0.07, 0.95, 0.88, "#14324a")
    for k, c in enumerate(("#6fb6e8", "#e8e8e8", "#3ddc6a", "#e8e8e8", "#6fb6e8")):
        rect(scr, 0.1, 0.14 + k * 0.14, 0.1 + 0.25 + (k * 0.29) % 0.55, 0.2 + k * 0.14, c)
    dark = to_img(base(32, 32, "#202224", 2, 2, 244))
    box(img, f, 0.47, 0.22, 0.53, 0.28, 0.3, 0.38, dark, dark, dark)            # stand
    box(img, f, 0.3, 0.2, 0.7, 0.24, 0.38, 0.6, dark, to_img(scr), dark)        # screen
    key = to_img(base(64, 16, "#d6d6d0", 2, 2, 245))
    box(img, f, 0.32, 0.36, 0.66, 0.44, 0.3, 0.315, key, key, key)              # keyboard
    paper = to_img(base(32, 32, "#f4f4ee", 1, 1, 246))
    box(img, f, 0.74, 0.3, 0.92, 0.52, 0.3, 0.34, paper, paper, paper)          # papers
    box(img, f, 0.08, 0.3, 0.22, 0.48, 0.3, 0.32, paper, paper, paper)
    mug = to_img(base(16, 16, "#b02a2a", 2, 2, 247))
    box(img, f, 0.2, 0.46, 0.25, 0.51, 0.3, 0.37, mug, mug, mug)                # mug
    return finish(img)


def prop_officechair(f):
    """Black swivel chair on a five-arm base, turned to the desk north (or west) of it."""
    img = canvas()
    blk = to_img(base(32, 32, "#232527", 3, 3, 248))
    grey = to_img(base(16, 16, "#5a5e62", 2, 2, 249))
    for (a, b) in ((0.5, 0.3), (0.5, 0.7), (0.3, 0.5), (0.7, 0.5)):
        box(img, f, min(a, 0.5) - 0.02, min(b, 0.5) - 0.02, max(a, 0.5) + 0.02, max(b, 0.5) + 0.02, 0, 0.03,
            grey, grey, grey)
    box(img, f, 0.48, 0.48, 0.53, 0.53, 0.03, 0.2, grey, grey, grey)
    box(img, f, 0.3, 0.3, 0.7, 0.68, 0.2, 0.27, blk, blk, blk)
    box(img, f, 0.32, 0.64, 0.68, 0.7, 0.27, 0.56, blk, blk, blk)   # back (south side: faces the desk)
    return finish(img)


def prop_bookcase(f):
    """Wooden bookcase full of coloured binders and books."""
    img = canvas()
    fr = wood_tex(256, 320, "#6e5238", 250)
    g = np.random.default_rng(251)
    for k in range(5):
        v = 0.04 + k * 0.19
        rect(fr, 0.04, v, 0.96, v + 0.16, "#2a2018")
        u = 0.06
        while u < 0.9:
            w = 0.05 + g.random() * 0.06
            col = ["#2a4fb0", "#b02a2a", "#e0b020", "#3d8a4a", "#e8e8e0", "#5a3a7a"][int(g.random() * 6)]
            h = 0.1 + g.random() * 0.05
            rect(fr, u, v + 0.16 - h, min(0.94, u + w), v + 0.16, col)
            rect(fr, u + w * 0.3, v + 0.16 - h * 0.6, u + w * 0.7, v + 0.16 - h * 0.45, "#f0f0e8")
            u += w + 0.01
    side = to_img(wood_tex(64, 128, "#5d4430", 252))
    box(img, f, 0.06, 0.05, 0.94, 0.36, 0, 0.82, side, to_img(fr), side)
    return finish(img)


def prop_printer(f):
    """Office photocopier."""
    img = canvas()
    body = base(192, 160, "#d8d9d4", 3, 3, 253)
    rect(body, 0.05, 0.1, 0.95, 0.3, "#b9bab5")
    for v in (0.4, 0.62, 0.84):
        rect(body, 0.08, v, 0.92, v + 0.14, "#c4c5c0")
        rect(body, 0.42, v + 0.05, 0.58, v + 0.08, "#4a4d50")
    side = to_img(base(64, 64, "#c6c7c2", 3, 3, 254))
    box(img, f, 0.14, 0.12, 0.86, 0.6, 0, 0.42, side, to_img(body), side)
    lid = base(96, 64, "#3a3d40", 2, 2, 255)
    rect(lid, 0.6, 0.2, 0.9, 0.5, "#3ddc6a")
    box(img, f, 0.16, 0.14, 0.84, 0.58, 0.42, 0.46, to_img(lid), to_img(lid), to_img(lid))
    paper = to_img(base(32, 32, "#f6f6f0", 1, 1, 256))
    box(img, f, 0.6, 0.62, 0.84, 0.76, 0.22, 0.25, paper, paper, paper)
    return finish(img)


def prop_coffee(f):
    """Low cabinet with a coffee machine, cups and a kettle."""
    img = canvas()
    fr = wood_tex(256, 128, "#9a9c98", 257)
    for u in (0.04, 0.52):
        rect(fr, u, 0.1, u + 0.44, 0.9, "#868884")
        rect(fr, u + 0.36, 0.45, u + 0.4, 0.55, "#3a3d40")
    top = to_img(base(96, 64, "#2a2c2e", 2, 2, 258))
    side = to_img(base(64, 64, "#80827e", 3, 3, 259))
    box(img, f, 0.05, 0.1, 0.95, 0.5, 0, 0.3, top, to_img(fr), side)
    mach = base(64, 96, "#1d1f21", 2, 2, 260)
    rect(mach, 0.25, 0.15, 0.75, 0.3, "#d03a2a")
    rect(mach, 0.3, 0.55, 0.7, 0.85, "#0a0a0a")
    m = to_img(base(32, 32, "#2a2c2e", 2, 2, 261))
    box(img, f, 0.12, 0.14, 0.38, 0.38, 0.3, 0.56, m, to_img(mach), m)
    cup = to_img(base(16, 16, "#f0f0ea", 1, 1, 262))
    for x in (0.5, 0.6, 0.7):
        box(img, f, x, 0.3, x + 0.06, 0.36, 0.3, 0.36, cup, cup, cup)
    ket = to_img(base(16, 16, "#9aa0a5", 2, 2, 263))
    box(img, f, 0.8, 0.16, 0.9, 0.28, 0.3, 0.42, ket, ket, ket)
    return finish(img)


def prop_microscope(f):
    """Lab desk with a microscope, sample tray and a lamp."""
    img = canvas()
    fr = metal_tex(256, 128, "#d8dbd6", 264)
    rect(fr, 0.66, 0.12, 0.95, 0.88, "#c4c8c3")
    rect(fr, 0.77, 0.4, 0.84, 0.45, "#3a3d40")
    top = to_img(base(128, 96, "#e6e8e4", 2, 2, 265))
    side = to_img(metal_tex(64, 64, "#c0c4bf", 266))
    box(img, f, 0.04, 0.12, 0.96, 0.6, 0, 0.3, top, to_img(fr), side)
    blk = to_img(base(16, 16, "#26292c", 2, 2, 267))
    wht = to_img(base(16, 16, "#eceeea", 2, 2, 268))
    box(img, f, 0.3, 0.2, 0.46, 0.36, 0.3, 0.33, blk, blk, blk)        # foot
    box(img, f, 0.36, 0.2, 0.42, 0.26, 0.33, 0.52, wht, wht, wht)      # arm
    box(img, f, 0.34, 0.24, 0.42, 0.34, 0.44, 0.47, blk, blk, blk)     # stage
    box(img, f, 0.36, 0.26, 0.41, 0.31, 0.52, 0.62, blk, blk, blk)     # eyepiece
    tray = to_img(base(32, 16, "#8fb3c9", 2, 2, 269))
    box(img, f, 0.58, 0.3, 0.86, 0.44, 0.3, 0.32, tray, tray, tray)
    box(img, f, 0.12, 0.2, 0.15, 0.23, 0.3, 0.6, blk, blk, blk)        # lamp
    box(img, f, 0.1, 0.2, 0.22, 0.3, 0.58, 0.62, wht, wht, wht)
    return finish(img)


def prop_filingboxes(f):
    """Stacked archive boxes."""
    img = canvas()
    c = base(96, 64, "#c9b48a", 4, 6, 270)
    rect(c, 0.3, 0.3, 0.7, 0.55, "#f2f0e6")
    t = to_img(c)
    sd = to_img(base(64, 64, "#b39f78", 4, 6, 271))
    box(img, f, 0.12, 0.1, 0.52, 0.42, 0, 0.18, sd, t, sd)
    box(img, f, 0.5, 0.1, 0.9, 0.42, 0, 0.18, sd, t, sd)
    box(img, f, 0.3, 0.12, 0.7, 0.42, 0.18, 0.36, sd, t, sd)
    return finish(img)


def prop_desklamp(f):
    """Small desk with papers, a reading lamp and a phone (for offices)."""
    img = canvas()
    top = to_img(wood_tex(128, 96, "#7d6346", 272))
    fr = wood_tex(256, 96, "#6a5238", 273)
    rect(fr, 0.06, 0.12, 0.4, 0.88, "#5a4430")
    rect(fr, 0.2, 0.45, 0.26, 0.5, "#c9b48a")
    side = to_img(wood_tex(64, 64, "#5d4430", 274))
    box(img, f, 0.05, 0.1, 0.95, 0.58, 0, 0.3, top, to_img(fr), side)
    paper = to_img(base(32, 32, "#f4f4ee", 1, 1, 275))
    for k in range(3):
        box(img, f, 0.4 + k * 0.02, 0.24, 0.62 + k * 0.02, 0.48, 0.3 + k * 0.012, 0.312 + k * 0.012,
            paper, paper, paper)
    grn = to_img(base(16, 16, "#2d6a3a", 2, 2, 276))
    brs = to_img(base(16, 16, "#c9a640", 2, 2, 277))
    box(img, f, 0.14, 0.18, 0.18, 0.22, 0.3, 0.5, brs, brs, brs)
    box(img, f, 0.08, 0.18, 0.3, 0.3, 0.48, 0.54, grn, grn, grn)
    blk = to_img(base(16, 16, "#1d1f21", 2, 2, 278))
    box(img, f, 0.74, 0.2, 0.9, 0.34, 0.3, 0.35, blk, blk, blk)
    return finish(img)


# ----------------------------------------------------------------------
# Surroundings: fence, gravel, dirt, vegetation (tiles 248+)
# ----------------------------------------------------------------------

def tile_fence(side):
    """Chain-link fence, 1 storey, with three strands of barbed wire on top and a post at each end."""
    img = Image.new("RGBA", (TW * SS, TH * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    H = 0.82
    def P(a, z):
        return proj(WALL_T / 2, 1 - a, z) if side == "W" else proj(a, WALL_T / 2, z)
    mesh = (150, 156, 160, 150)
    n = 14
    for k in range(n + 1):           # diagonal mesh
        a = k / n
        d.line([P(a, 0.02), P(min(1, a + 0.25), H)], fill=mesh, width=SS)
        d.line([P(a, 0.02), P(max(0, a - 0.25), H)], fill=mesh, width=SS)
    for z in (0.02, H):
        d.line([P(0, z), P(1, z)], fill=(110, 116, 120, 255), width=2 * SS)
    for z in (H + 0.05, H + 0.1, H + 0.15):
        d.line([P(0, z), P(1, z)], fill=(70, 74, 78, 255), width=SS)
    for a in (0.0, 1.0):
        d.line([P(a, 0), P(a, H + 0.16)], fill=(80, 86, 90, 255), width=3 * SS)
    return finish(img)


def tile_fence_post():
    img = Image.new("RGBA", (TW * SS, TH * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.line([proj(0, 0, 0), proj(0, 0, 0.98)], fill=(80, 86, 90, 255), width=3 * SS)
    return finish(img)


def floor_gravel():
    g = np.random.default_rng(301)
    a = base(FLOOR, FLOOR, "#8e8a80", 22, 10, 302)
    for _ in range(900):
        u, v = g.random(), g.random()
        c = ["#6f6b62", "#a9a59b", "#7d786d", "#b8b3a8"][int(g.random() * 4)]
        rect(a, u, v, min(1, u + 0.012), min(1, v + 0.012), c)
    return to_img(a)


def floor_dirt():
    a = base(FLOOR, FLOOR, "#6e5a40", 16, 22, 303)
    g = np.random.default_rng(304)
    for _ in range(140):      # tufts of grass
        u, v = g.random(), g.random()
        rect(a, u, v, min(1, u + 0.03), min(1, v + 0.02), ["#4f6b34", "#5d7a3a", "#435c2c"][int(g.random() * 3)], 0.9)
    return to_img(a)


def prop_bush(f):
    img = Image.new("RGBA", (TW * SS, TH * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    g = np.random.default_rng(305 + (f == "w"))
    for _ in range(46):
        x, y = 0.2 + g.random() * 0.6, 0.2 + g.random() * 0.6
        z = g.random() * 0.32
        cx, cy = proj(x, y, z)
        r = (8 + g.random() * 10) * SS
        col = (40 + int(g.random() * 40), 80 + int(g.random() * 60), 30 + int(g.random() * 25), 255)
        d.ellipse([cx - r, cy - r * 0.8, cx + r, cy + r * 0.8], fill=col)
    return finish(img)


def prop_pine(f):
    """Small conifer (a stand-in when the game's own trees cannot be used)."""
    img = Image.new("RGBA", (TW * SS, TH * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    bx, by = proj(0.5, 0.5, 0)
    d.rectangle([bx - 4 * SS, by - 30 * SS, bx + 4 * SS, by], fill=(84, 60, 40, 255))
    g = np.random.default_rng(307 + (f == "w"))
    tiers = 5
    for t in range(tiers):
        z0 = 0.14 + t * 0.15
        w = (46 - t * 8) * SS
        _, ty = proj(0.5, 0.5, z0)
        _, tt = proj(0.5, 0.5, z0 + 0.28)
        base_col = (34 + t * 4, 70 + t * 6, 40 + t * 2, 255)
        d.polygon([(bx - w, ty), (bx + w, ty), (bx, tt)], fill=base_col)
        d.polygon([(bx, ty), (bx + w, ty), (bx, tt)], fill=tuple(int(c * 0.78) for c in base_col[:3]) + (255,))
    return finish(img)


def prop_rocks(f):
    img = Image.new("RGBA", (TW * SS, TH * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    g = np.random.default_rng(309 + (f == "w"))
    for _ in range(5):
        x, y = 0.25 + g.random() * 0.5, 0.25 + g.random() * 0.5
        cx, cy = proj(x, y, 0)
        r = (10 + g.random() * 14) * SS
        v = 110 + int(g.random() * 40)
        d.ellipse([cx - r, cy - r * 0.9, cx + r, cy + r * 0.3], fill=(v, v, v - 6, 255))
        d.ellipse([cx - r * 0.6, cy - r * 0.85, cx + r * 0.3, cy - r * 0.2], fill=(v + 25, v + 25, v + 20, 255))
    return finish(img)


def prop_sandbags(f):
    img = canvas()
    bag = base(64, 32, "#a8946a", 6, 8, 311)
    rect(bag, 0, 0.45, 1, 0.55, "#8f7c56")
    t = to_img(bag)
    for row, z in enumerate((0, 0.08, 0.16)):
        off = 0.08 * (row % 2)
        for k in range(3):
            x0 = 0.06 + off + k * 0.3
            if x0 + 0.28 <= 1.0:
                box(img, f, x0, 0.32, x0 + 0.28, 0.6, z, z + 0.08, t, t, t)
    return finish(img)


def prop_warnsign(f):
    """Free-standing 'Restricted area' sign on two posts."""
    img = canvas()
    tex = label_tex(["RESTRICTED", "AREA"], bg=(232, 232, 226, 255), fg=(170, 30, 25, 255), bar=(170, 30, 25, 255))
    leg = to_img(base(8, 64, "#5a5e62", 2, 2, 312))
    for x in (0.25, 0.71):
        box(img, f, x, 0.48, x + 0.04, 0.52, 0, 0.42, leg, leg, leg)
    side = to_img(base(16, 64, "#c9ccce", 2, 2, 313))
    box(img, f, 0.16, 0.47, 0.84, 0.5, 0.36, 0.66, side, tex, side)
    return finish(img)


def prop_camonet(f):
    """Camouflage net on poles, a little above head height."""
    img = Image.new("RGBA", (TW * SS, TH * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for (x, y) in ((0.05, 0.05), (0.95, 0.95)):
        d.line([proj(x, y, 0), proj(x, y, 0.62)], fill=(70, 60, 45, 255), width=2 * SS)
    g = np.random.default_rng(314 + (f == "w"))
    for _ in range(120):
        x, y = g.random(), g.random()
        cx, cy = proj(x, y, 0.62 - 0.06 * abs(x - y))
        r = (5 + g.random() * 7) * SS
        col = [(70, 82, 48), (96, 90, 60), (52, 62, 38), (110, 104, 74)][int(g.random() * 4)] + (235,)
        d.ellipse([cx - r, cy - r * 0.6, cx + r, cy + r * 0.6], fill=col)
    return finish(img)


LAND = [("bush", prop_bush), ("pine", prop_pine), ("rocks", prop_rocks), ("sandbags", prop_sandbags),
        ("warnsign", prop_warnsign), ("camonet", prop_camonet)]


PROPS2 = [("chair", prop_chair), ("table", prop_table), ("sofa", prop_sofa), ("vending", prop_vending),
          ("plant", prop_plant), ("cooler", prop_cooler), ("bunkbed", prop_bunkbed), ("medbed", prop_medbed),
          ("labbench", prop_labbench), ("whiteboard", prop_whiteboard), ("trash", prop_trash),
          ("workstation", prop_workstation), ("officechair", prop_officechair), ("bookcase", prop_bookcase),
          ("printer", prop_printer), ("coffee", prop_coffee), ("microscope", prop_microscope),
          ("filingboxes", prop_filingboxes), ("desklamp", prop_desklamp)]


def lift_door_tex():
    """Brushed steel sliding lift door, seam in the middle."""
    a = cb("metal", (256, 512), bright=1.25)
    a[..., :3] = a[..., :3] * 0.7 + 150 * 0.3
    vline(a, 0.5, 0.012, "#2b2e31")
    for u in (0.0, 1.0):
        vline(a, u, 0.03, "#4a4e52")
    rect(a, 0, 0.0, 1, 0.04, "#3a3d40")
    hazard(a, 0, 0.94, 1, 1.0, period=24)
    rect(a, 0.06, 0.4, 0.44, 0.43, "#6c7176")
    rect(a, 0.56, 0.4, 0.94, 0.43, "#6c7176")
    return to_img(a)


def lift_panel_tex():
    img = Image.new("RGBA", (96, 192), (120, 126, 130, 255))
    d = ImageDraw.Draw(img)
    d.rectangle([2, 2, 93, 189], outline=(40, 42, 44, 255), width=4)
    d.rectangle([14, 14, 81, 44], fill=(12, 20, 14, 255))
    d.text((24, 16), "GATE A", fill=(80, 230, 110, 255), font=ImageFont.truetype(FONT_BOLD, 14))
    for k, lab in enumerate(("S", "EZ")):
        cy = 80 + k * 50
        d.ellipse([28, cy - 18, 68, cy + 18], fill=(210, 60, 40, 255) if k else (230, 190, 40, 255),
                  outline=(30, 30, 30, 255), width=3)
        d.text((40 if k == 0 else 34, cy - 9), lab, fill=(20, 20, 20, 255), font=ImageFont.truetype(FONT_BOLD, 15))
    return img


def floor_concrete_pale():
    a = cb("concretefloor", (FLOOR, FLOOR), bright=2.25)
    a[..., :3] = a[..., :3] * 0.6 + 168 * 0.4
    for i in (0, 1):
        hline(a, i, 0.008, "#8d9092")
        vline(a, i, 0.008, "#8d9092")
    return to_img(a)


def floor_road_line():
    a = np.asarray(floor_asphalt()).astype(np.float32).copy()
    rect(a, 0.0, 0.1, 0.035, 0.6, "#e0b52a")

    return to_img(a)


def floor_road_stop():
    a = np.asarray(floor_asphalt()).astype(np.float32).copy()
    rect(a, 0, 0.4, 1, 0.6, "#e7e7e2")
    return to_img(a)


def floor_roof_pale():
    a = base(FLOOR, FLOOR, "#a7aaab", 8, 10, 199)
    for i in (0, 1):
        hline(a, i, 0.01, "#8b8e90")
    return to_img(a)



PROPS = [("locker", prop_locker), ("shelf", prop_shelf), ("desk", prop_desk), ("crate", prop_crate),
         ("barrel", prop_barrel), ("rack", prop_rack), ("bed", prop_bed), ("cabinet", prop_cabinet),
         ("console", prop_console)]


def label_tex(lines, bg=(232, 232, 226, 255), fg=(20, 20, 20, 255), bar=(170, 40, 32, 255)):
    img = text_tex(256, 96, bg, fg, lines, (20, 20, 20, 255))
    d = ImageDraw.Draw(img)
    d.rectangle([6, 6, 249, 16], fill=bar)
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
    if kind == "SE":
        return [("WallSE", ""), ("MaterialType", mat)]


def door_props(side, closed, label, sound="SCPDoor"):
    # DoorSound: the game plays <prefix>Open, Close, Locked, Lock, Unlock, Blocked, Break
    # (sounds in media/scripts/sounds/scp_sounds.txt)
    p = [("CustomName", label), ("GroupName", "SCP"), ("Material", "MetalPlates"), ("Material2", "Door"),
         ("MaterialType", "Metal"), ("attached" + side, ""), ("DoorSound", sound)]
    if closed:
        p.append(("door" + side, ""))
    return p


def floor_props(label):
    return [("CustomName", label), ("GroupName", "SCP"), ("solidfloor", ""), ("diamondFloor", ""),
            ("attachedFloor", ""), ("Material", "Concrete")]


def sign_props(side, label):
    return [("CustomName", label), ("GroupName", "SCP"), ("attached" + side, "")]


def prop_props(label):
    return [("CustomName", label), ("GroupName", "SCP"), ("solidtrans", ""), ("MaterialType", "Metal")]


SHEET = "scp_facility_02"
COLS = 8
ROWS = 34

# Where everything is on the sheet (also written into the mod as Lua by tools/make_site_layout.py).
WALLS = {"a": 0, "b": 8, "c": 16, "d": 56, "e": 64}      # +0 W, +1 N, +2 NW, +3 frame W, +4 frame N
PERIMETER = 72                                              # +0 W, +1 N, +2 NW
PILLARS = {"a": 63, "b": 62, "c": 70, "d": 61, "e": 69, "f": 71, "x": 173, "y": 173}
FLOORS = {"t": 5, "h": 6, "c": 13, "g": 14, "e": 15, "m": 21, "a": 75, "k": 76, "roof": 77,
          "p": 186, "r": 187, "s": 188, "o": 189}
DOORS = {"standard": 24, "heavy": 28, "gate": 80, "lift": 200}   # +0 W, +1 N, +2 open W, +3 open N
FITTINGS = {"pipes": 84, "vent": 86}
FENCE = 248                 # chain-link fence: +0 W, +1 N, +2 post (corner)
FLOORS3 = {"v": 251, "u": 252}   # gravel, dirt with grass
LAND0 = 254                 # LAND props: + 2 * k (n), + 1 (w)                        # +0 W, +1 N
SIGNS = ["ez", "lcz", "hcz", "logo", "danger"]              # 40 + k (W), 48 + k (N)
SIGNS2 = ["scp173", "scp914", "scp500", "scp939", "scp106", "scp049", "scp096", "scp035", "scp008", "scp079",
          "scp966", "warhead", "femur", "electric", "gatea", "cafeteria", "medical", "security",
          "gateb"]   # 96 + k, 120 + k
PROP0 = 144                                                 # + 2 * k (against north wall), + 1 (against west wall)
# exterior (tiles 168+)
FORT = 168                  # pale concrete wall: +0 W, +1 N, +2 NW, +3 frame W, +4 frame N; pillar 173
WINDOW = 174                # window band wall: +0 W, +1 N, +2 NW
PARAPET = 177               # low wall: +0 W, +1 N
STAIRS = {"N": 180, "W": 183}   # + piece (0 bottom, 1 middle, 2 top)
FLOORS2 = {"p": 186, "r": 187, "s": 188, "o": 189}
EXTRA = {"solar": 190, "fan": 192, "floodlight": 193, "barrier": 195, "wire": 197}   # n/w pairs except fan
LIFT_PANEL = 204            # lift call panel: +0 on a west wall, +1 on a north wall
PROP2 = 206                 # more furniture (PROPS2): + 2 * k against a north wall, + 1 against a west wall


def build_tiles():
    tiles = {}

    def put(i, img, props):
        assert i not in tiles, i
        tiles[i] = (img, props)

    styles = [("a", wall_ez(), "Cinderblock"), ("b", wall_lcz(), "Cinderblock"), ("c", wall_hcz(), "Cinderblock"),
              ("d", wall_cell(), "Metal"), ("e", wall_bunker(), "Cinderblock")]
    for key, tex, mat in styles:
        i0 = WALLS[key]
        put(i0 + 0, tile_wall(tex, "W"), wall_props("W", SHEET, i0 + 0, mat))
        put(i0 + 1, tile_wall(tex, "N"), wall_props("N", SHEET, i0 + 1, mat))
        put(i0 + 2, tile_wall(tex, "NW"), wall_props("NW", SHEET, i0 + 2, mat))
        put(i0 + 3, tile_frame(tex, "W"), wall_props("FW", SHEET, i0 + 3, mat))
        put(i0 + 4, tile_frame(tex, "N"), wall_props("FN", SHEET, i0 + 4, mat))
        put(PILLARS[key], tile_pillar(tex), wall_props("SE", SHEET, 0, mat))
    pt = wall_perimeter()
    put(PERIMETER + 0, tile_wall(pt, "W"), wall_props("W", SHEET, PERIMETER))
    put(PERIMETER + 1, tile_wall(pt, "N"), wall_props("N", SHEET, PERIMETER + 1))
    put(PERIMETER + 2, tile_wall(pt, "NW"), wall_props("NW", SHEET, PERIMETER + 2))
    put(PILLARS["f"], tile_pillar(pt), wall_props("SE", SHEET, 0))

    for key, fn, label in (("t", floor_ez, "White Tile Floor"), ("h", floor_hazard_line, "Hazard Line Floor"),
                           ("c", floor_lcz, "Concrete Floor"), ("g", floor_grate, "Containment Grating"),
                           ("e", floor_elevator, "Lift Platform"), ("m", floor_hcz, "Steel Plate Floor"),
                           ("a", floor_asphalt, "Asphalt"), ("k", floor_slab, "Bunker Slab"),
                           ("roof", floor_roof, "Bunker Roof")):
        put(FLOORS[key], tile_floor(fn()), floor_props(label))

    for base_i, tex, label, snd in ((DOORS["standard"], door_standard(), "Foundation Door", "SCPDoor"),
                                    (DOORS["heavy"], door_containment(), "Containment Door", "SCPHeavyDoor")):
        put(base_i + 0, tile_door(tex, "W", False), door_props("W", True, label, snd))
        put(base_i + 1, tile_door(tex, "N", False), door_props("N", True, label, snd))
        put(base_i + 2, tile_door(tex, "W", True), door_props("W", False, label, snd))
        put(base_i + 3, tile_door(tex, "N", True), door_props("N", False, label, snd))
    gt = gate_tex()
    g0 = DOORS["gate"]
    put(g0 + 0, tile_gate(gt, "W", False), door_props("W", True, "Site Gate", "SCPGate"))
    put(g0 + 1, tile_gate(gt, "N", False), door_props("N", True, "Site Gate", "SCPGate"))
    put(g0 + 2, tile_gate(gt, "W", True), door_props("W", False, "Site Gate", "SCPGate"))
    put(g0 + 3, tile_gate(gt, "N", True), door_props("N", False, "Site Gate", "SCPGate"))

    pw = wall_pocket()
    put(32, tile_wall(pw, "W"), wall_props("W", SHEET, 32, "Stone"))
    put(33, tile_wall(pw, "N"), wall_props("N", SHEET, 33, "Stone"))
    put(34, tile_wall(pw, "NW"), wall_props("NW", SHEET, 34, "Stone"))
    put(35, tile_floor(floor_pocket(60)), floor_props("Corroded Floor"))
    put(36, tile_floor(floor_pocket(65)), floor_props("Corroded Floor"))
    put(37, tile_floor(floor_pocket_exit()), floor_props("Corroded Floor"))

    pipes = to_img(cb("misc", (512, 64), crop=(0, 0, 1, 0.115), bright=1.2))
    vent = to_img(cb("vent", (128, 128)))
    f0 = FITTINGS["pipes"]
    put(f0 + 0, tile_overlay(pipes, "W", 0.8, 0.95), sign_props("W", "Pipes"))
    put(f0 + 1, tile_overlay(pipes, "N", 0.8, 0.95), sign_props("N", "Pipes"))
    v0 = FITTINGS["vent"]
    put(v0 + 0, tile_overlay(vent, "W", 0.62, 0.84, 0.3, 0.7, 0.006), sign_props("W", "Vent"))
    put(v0 + 1, tile_overlay(vent, "N", 0.62, 0.84, 0.3, 0.7, 0.006), sign_props("N", "Vent"))

    signs = {
        "ez": text_tex(256, 96, (36, 86, 150, 255), (240, 244, 248, 255), ["ENTRANCE", "ZONE"], (230, 236, 240, 255)),
        "lcz": text_tex(256, 96, (232, 186, 28, 255), (20, 20, 20, 255), ["LIGHT", "CONTAINMENT"], (20, 20, 20, 255)),
        "hcz": text_tex(256, 96, (165, 40, 32, 255), (245, 240, 235, 255), ["HEAVY", "CONTAINMENT"], (245, 240, 235, 255)),
        "logo": logo_tex(),
        "danger": danger_tex(),
    }
    for k, name in enumerate(SIGNS):
        put(40 + k, tile_sign(signs[name], "W"), sign_props("W", "Sign " + name))
        put(48 + k, tile_sign(signs[name], "N"), sign_props("N", "Sign " + name))
    yellow = dict(bg=(232, 186, 28, 255), bar=(20, 20, 20, 255))
    blue = dict(bg=(36, 86, 150, 255), fg=(240, 244, 248, 255), bar=(240, 244, 248, 255))
    labels = {"warhead": (["ALPHA", "WARHEAD"], yellow), "femur": (["FEMUR", "BREAKER"], yellow),
              "electric": (["ELECTRICAL", "CENTER"], yellow), "gatea": (["GATE A"], blue), "gateb": (["GATE B"], blue),
              "cafeteria": (["CAFETERIA"], blue), "medical": (["MEDICAL", "BAY"], blue),
              "security": (["SECURITY"], blue)}
    for k, name in enumerate(SIGNS2):
        if name in labels:
            tex = label_tex(labels[name][0], **labels[name][1])
        else:
            tex = label_tex(["SCP-" + name[3:]])
        put(96 + k, tile_sign(tex, "W"), sign_props("W", "Sign " + name))
        put(120 + k, tile_sign(tex, "N"), sign_props("N", "Sign " + name))

    for k, (name, fn) in enumerate(PROPS):
        put(PROP0 + 2 * k, fn("n"), prop_props(name.capitalize()))
        put(PROP0 + 2 * k + 1, fn("w"), prop_props(name.capitalize()))

    # exterior
    ft = wall_fort()
    for i0, tex, n in ((FORT, ft, 5), (WINDOW, wall_window(), 3)):
        put(i0 + 0, tile_wall(tex, "W"), wall_props("W", SHEET, i0 + 0))
        put(i0 + 1, tile_wall(tex, "N"), wall_props("N", SHEET, i0 + 1))
        put(i0 + 2, tile_wall(tex, "NW"), wall_props("NW", SHEET, i0 + 2))
        if n == 5:
            put(i0 + 3, tile_frame(tex, "W"), wall_props("FW", SHEET, i0 + 3))
            put(i0 + 4, tile_frame(tex, "N"), wall_props("FN", SHEET, i0 + 4))
    put(PILLARS["x"], tile_pillar(ft), wall_props("SE", SHEET, 0))
    for k, side in enumerate(("W", "N")):
        put(PARAPET + k, tile_parapet(ft, side),
            [("CustomName", "Low Wall"), ("GroupName", "SCP"), ("collide" + side, ""), ("Hoppable" + side, ""),
             ("MaterialType", "Cinderblock")])
    for side in ("N", "W"):
        for piece in range(3):
            flag = "stairs" + "BMT"[piece] + side
            put(STAIRS[side] + piece, tile_stairs(side, piece),
                [("CustomName", "Concrete Stairs"), ("GroupName", "SCP"), (flag, ""), ("MaterialType", "Concrete")])
    for key, fn, label in (("p", floor_concrete_pale, "Concrete Yard"), ("r", floor_road_line, "Road"),
                           ("s", floor_road_stop, "Road"), ("o", floor_roof_pale, "Concrete Roof")):
        put(FLOORS2[key], tile_floor(fn()), floor_props(label))
    put(EXTRA["solar"], prop_solar("n"), prop_props("Solar Panel"))
    put(EXTRA["solar"] + 1, prop_solar("w"), prop_props("Solar Panel"))
    put(EXTRA["fan"], prop_fan("n"), prop_props("Ventilation Unit"))
    put(EXTRA["floodlight"], prop_floodlight("n"), prop_props("Floodlight"))
    put(EXTRA["floodlight"] + 1, prop_floodlight("w"), prop_props("Floodlight"))
    put(EXTRA["barrier"], prop_barrier("n"), prop_props("Road Barrier"))
    put(EXTRA["barrier"] + 1, prop_barrier("w"), prop_props("Road Barrier"))
    put(EXTRA["wire"], tile_wire("W"), sign_props("W", "Barbed Wire"))
    put(EXTRA["wire"] + 1, tile_wire("N"), sign_props("N", "Barbed Wire"))
    lt = lift_door_tex()
    l0 = DOORS["lift"]
    put(l0 + 0, tile_gate(lt, "W", False), door_props("W", True, "Lift Door", "SCPLiftDoor"))
    put(l0 + 1, tile_gate(lt, "N", False), door_props("N", True, "Lift Door", "SCPLiftDoor"))
    put(l0 + 2, tile_gate(lt, "W", True), door_props("W", False, "Lift Door", "SCPLiftDoor"))
    put(l0 + 3, tile_gate(lt, "N", True), door_props("N", False, "Lift Door", "SCPLiftDoor"))
    for k, (name, fn) in enumerate(PROPS2):
        put(PROP2 + 2 * k, fn("n"), prop_props(name.capitalize()))
        put(PROP2 + 2 * k + 1, fn("w"), prop_props(name.capitalize()))
    for k, side in enumerate(("W", "N")):
        put(FENCE + k, tile_fence(side),
            [("CustomName", "Fence"), ("GroupName", "SCP"), ("Wall" + side + "Trans", ""), ("wall", ""),
             ("TallHoppable" + side, ""), ("MaterialType", "Metal")])
    put(FENCE + 2, tile_fence_post(), [("CustomName", "Fence Post"), ("GroupName", "SCP"), ("MaterialType", "Metal")])
    put(FLOORS3["v"], tile_floor(floor_gravel()), floor_props("Gravel"))
    put(FLOORS3["u"], tile_floor(floor_dirt()), floor_props("Dirt"))
    for k, (name, fn) in enumerate(LAND):
        lp = [("CustomName", name.capitalize()), ("GroupName", "SCP")]
        if name in ("sandbags", "rocks", "pine", "warnsign"):
            lp.append(("solidtrans", ""))
        put(LAND0 + 2 * k, fn("n"), lp)
        put(LAND0 + 2 * k + 1, fn("w"), lp)
    pt2 = lift_panel_tex()
    put(LIFT_PANEL, tile_sign(pt2, "W", 0.3, 0.75, 0.3, 0.7), sign_props("W", "Lift Panel"))
    put(LIFT_PANEL + 1, tile_sign(pt2, "N", 0.3, 0.75, 0.3, 0.7), sign_props("N", "Lift Panel"))
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


def main():
    tiles = build_tiles()
    rows = ROWS
    sheet = make_sheet(tiles, rows)
    os.makedirs(ART, exist_ok=True)
    sheet.save(os.path.join(ART, SHEET + "_tilesheet.png"))

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
