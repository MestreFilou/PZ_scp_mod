#!/usr/bin/env python3
"""
Renders isometric previews of the SCP site with the real tiles, following
the same rules as the in-game builder (server/SCP_Facility.lua):
floor, then walls / door frames / doors on the west and north edges, corner
posts, then signs, fittings, furniture and machines.

Walls that would hide a room (the ones standing on rock, seen from behind)
are cut low, as the game does around the player.

Outputs art/preview_*.png.  Usage: python3 tools/make_site_preview.py
"""

import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_facility_tiles as T
import make_site_layout as L

ART = os.path.join(T.ROOT, "art")
TILES = {i: img for i, (img, _) in T.build_tiles().items()}
OLD = Image.open(os.path.join(ART, "scp_facility_01_tilesheet.png")).convert("RGBA")
OLD_TILES = {i: OLD.crop(((i % 8) * 128, (i // 8) * 256, (i % 8) * 128 + 128, (i // 8) * 256 + 256)) for i in range(16)}
MACHINES = {"scp914": 1, "scp914In": 0, "scp914Out": 2, "scp294": 3, "terminal": 4, "generator": 5, "warhead": 6,
            "femur": 6}
WALLS = dict(T.WALLS, f=T.PERIMETER)
PROPS = {name: T.PROP0 + 2 * k for k, (name, _) in enumerate(T.PROPS)}
SIGN_W = {n: 40 + k for k, n in enumerate(T.SIGNS)}
SIGN_W.update({n: 96 + k for k, n in enumerate(T.SIGNS2)})
SIGN_N = {n: 48 + k for k, n in enumerate(T.SIGNS)}
SIGN_N.update({n: 120 + k for k, n in enumerate(T.SIGNS2)})


def stub(img):
    """Cuts a wall down to a low kerb, following the slope of its base."""
    out = img.copy()
    px = out.load()
    for x in range(128):
        base = 192 + abs(x - 64) * 0.5
        for y in range(0, int(base - 36)):
            px[x, y] = (0, 0, 0, 0)
    return out


def render(level, crop, title, scale=0.5, open_doors=(), roofs=False, dim=1.0):
    x0, y0, x1, y1 = crop
    w, h = x1 - x0 + 1, y1 - y0 + 1
    img = Image.new("RGBA", ((w + h) * 64 + 40, (w + h) * 32 + 300 + (192 if roofs else 0)), (10, 11, 12, 255))
    ox, oy = h * 64 + 20 - 64, 60 + (192 if roofs else 0)
    west, north = level.walls()
    objs = {}
    for o in level.objects:
        objs.setdefault((o["x"], o["y"]), []).append(o)
    doors = {(d["x"], d["y"], d["north"]): d for d in level.doors}
    tesla = {(t["x"], t["y"]): t for t in level.tesla}
    grass = Image.new("RGBA", (128, 256), (0, 0, 0, 0))
    ImageDraw.Draw(grass).polygon([(64, 192), (128, 224), (64, 256), (0, 224)], fill=(46, 66, 40, 255))

    def put(tile, x, y, z=0):
        img.alpha_composite(tile, (ox + (x - y) * 64 - (x0 - y0) * 64, oy + (x + y - x0 - y0) * 32 - z * 192))

    def door_tile(d, is_north):
        base = T.DOORS["gate"] if d.get("gate") else T.DOORS["heavy"] if d["heavy"] else T.DOORS["standard"]
        opened = (d["x"], d["y"]) in open_doors or d.get("gate") in open_doors
        return TILES[base + (1 if is_north else 0) + (2 if opened else 0)]

    roof_cells = set()
    for r in level.regions:
        if r and r.get("roof"):
            roof_cells |= {(x, y) for x in range(r["x0"], r["x1"] + 1) for y in range(r["y0"], r["y1"] + 1)}

    for s in range(x0 + y0, x1 + y1 + 1):
        for x in range(x0, x1 + 1):
            y = s - x
            if y < y0 or y > y1:
                continue
            fl = level.floor[y][x]
            rock = fl == " "
            if not rock:
                put(TILES[T.FLOORS[fl]], x, y)
            elif level is L.S:
                put(grass, x, y)
            wc, nc = west[y][x], north[y][x]
            low = rock and level is L.U
            fix = stub if low else (lambda t: t)
            if wc != "." and nc != "." and wc == nc and wc.islower():
                put(fix(TILES[WALLS[wc] + 2]), x, y)
            else:
                for ch, off, is_north in ((wc, 0, False), (nc, 1, True)):
                    if ch == ".":
                        continue
                    if ch.isupper():
                        put(fix(TILES[WALLS[ch.lower()] + 3 + off]), x, y)
                    else:
                        put(fix(TILES[WALLS[ch] + off]), x, y)
            if wc == "." and nc == "." and x > 0 and y > 0 and north[y][x - 1] != "." and west[y - 1][x] != ".":
                put(fix(TILES[T.PILLARS[north[y][x - 1].lower()]]), x, y)
            for is_north in (False, True):
                d = doors.get((x, y, is_north))
                if d:
                    put(door_tile(d, is_north), x, y)
            if (x, y) in tesla:
                put(OLD_TILES[8 if tesla[(x, y)]["north"] else 7], x, y)
            for o in objs.get((x, y), []):
                k = o["kind"]
                if k == "prop":
                    put(TILES[PROPS[o["prop"]] + (0 if o["face"] == "n" else 1)], x, y)
                elif k == "sign":
                    put(TILES[(SIGN_N if o["north"] else SIGN_W)[o["sign"]]], x, y)
                elif k in ("pipes", "vent"):
                    put(TILES[T.FITTINGS[k] + (1 if o["north"] else 0)], x, y)
                elif k in MACHINES:
                    put(OLD_TILES[MACHINES[k]], x, y)
    if roofs:
        for s in range(x0 + y0, x1 + y1 + 1):
            for x in range(x0, x1 + 1):
                y = s - x
                if (x, y) in roof_cells:
                    put(TILES[T.FLOORS["roof"]], x, y, 1)
    if dim != 1.0:
        img = Image.blend(Image.new("RGBA", img.size, (0, 0, 0, 255)), img, dim)
    bbox = img.convert("RGB").point(lambda v: 255 if v > 14 else 0).getbbox()
    img = img.crop((max(0, bbox[0] - 30), 0, min(img.width, bbox[2] + 30), min(img.height, bbox[3] + 30)))
    img = img.resize((int(img.width * scale), int(img.height * scale)), Image.LANCZOS).convert("RGB")
    d = ImageDraw.Draw(img)
    d.text((14, 10), title, fill=(240, 240, 240), font=ImageFont.truetype(L.FONT_BOLD, 22))
    return img


def main():
    U, S = L.build()
    shots = [
        ("preview_lcz", U, (1, 0, 34, 24), "Confinement léger : cellules classe D, SCP-173, SCP-939", 0.5, {}),
        ("preview_hcz", U, (7, 47, 47, 64), "Confinement lourd : SCP-106, broyeur de fémur, portail Tesla", 0.5, {}),
        ("preview_ez", U, (30, 95, 60, 122), "Zone d'entrée : hall principal, cafétéria, hall de la Porte A", 0.5, {}),
        ("preview_surface", S, (18, 104, 61, 139), "Surface : enceinte, bunker de la Porte A, grande porte",
         0.45, dict(roofs=True)),
        ("preview_surface_open", S, (28, 106, 52, 139), "Surface, toit retiré et portes ouvertes", 0.5,
         dict(open_doors=("A", "MAIN"))),
        ("preview_corridor", U, (12, 9, 30, 24), "Détail : couloirs de 2 cases", 0.9, {}),
    ]
    for name, level, crop, title, scale, kw in shots:
        render(level, crop, title, scale, **kw).save(os.path.join(ART, name + ".png"))
        print(name)


if __name__ == "__main__":
    sys.exit(main())
