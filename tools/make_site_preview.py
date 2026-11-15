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
WALLS = dict(T.WALLS, f=T.PERIMETER, x=T.FORT, y=T.WINDOW, p=T.PARAPET, q=T.FENCE)
FLOOR_TILES = dict(T.FLOORS, **T.FLOORS3)
LAND = {name: T.LAND0 + 2 * k for k, (name, _) in enumerate(T.LAND)}
LOW = {"p", "q"}
# the game's trees are about two storeys tall: the preview draws the pine twice as big
TREE_BIG = []
for _k in (0, 1):
    _t = TILES[LAND["pine"] + _k]
    TREE_BIG.append(_t.resize((_t.width * 2, _t.height * 2), Image.LANCZOS))                     # low walls: no corner tile, no post
PROPS = {name: T.PROP0 + 2 * k for k, (name, _) in enumerate(T.PROPS)}
PROPS.update({name: T.PROP2 + 2 * k for k, (name, _) in enumerate(T.PROPS2)})
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


def grass_tile(seed):
    g = Image.new("RGBA", (128, 256), (0, 0, 0, 0))
    d = ImageDraw.Draw(g)
    v = (seed * 7919) % 13 - 6
    d.polygon([(64, 192), (128, 224), (64, 256), (0, 224)], fill=(64 + v, 92 + v, 52 + v // 2, 255))
    return g


def render(level, crop, title, scale=0.5, open_doors=(), roofs=False, dim=1.0, above=(), sky=False, hide=(),
           frame=None):
    """above: [(z, level), ...] drawn on top of `level`, as the game draws
    levels bottom-up. hide: the levels of `above` to leave out (cutaway)."""
    x0, y0, x1, y1 = crop
    w, h = x1 - x0 + 1, y1 - y0 + 1
    top_z = max([z for z, _ in above] + [1 if roofs else 0])
    img = Image.new("RGBA", ((w + h) * 64 + 40, (w + h) * 32 + 300 + 192 * top_z), (10, 11, 12, 255))
    ox, oy = h * 64 + 20 - 64, 60 + 192 * top_z
    if sky:
        # sky down to the far corners of the area, ground below
        horizon = oy + min(w, h) * 32 + 192
        d = ImageDraw.Draw(img)
        for yy in range(img.height):
            k = min(1.0, yy / max(1, horizon))
            col = (int(120 + 90 * k), int(156 + 70 * k), int(200 + 40 * k), 255) if yy < horizon else (62, 90, 51, 255)
            d.line([(0, yy), (img.width, yy)], fill=col)
    grass = [grass_tile(i) for i in range(5)]

    def put(tile, x, y, z=0, dx=0, dy=0):
        px = ox + (x - y) * 64 - (x0 - y0) * 64 + dx
        py = oy + (x + y - x0 - y0) * 32 - z * 192 + dy
        if px < 0 or py < 0:
            tile = tile.crop((max(0, -px), max(0, -py), tile.width, tile.height))
            px, py = max(0, px), max(0, py)
        img.alpha_composite(tile, (px, py))

    for zz, lvl in [(0, level)] + [(z, l) for z, l in above if z not in hide]:
        draw_level(lvl, zz, crop, put, grass, open_doors, ground=(zz == 0))
    if roofs:
        roof_cells = set()
        for r in level.regions:
            if r and r.get("roof"):
                roof_cells |= {(x, y) for x in range(r["x0"], r["x1"] + 1) for y in range(r["y0"], r["y1"] + 1)}
        for s in range(x0 + y0, x1 + y1 + 1):
            for x in range(x0, x1 + 1):
                y = s - x
                if (x, y) in roof_cells:
                    put(TILES[T.FLOORS["roof"]], x, y, 1)
    if dim != 1.0:
        img = Image.blend(Image.new("RGBA", img.size, (0, 0, 0, 255)), img, dim)
    if frame:
        # keep the rectangle around `frame` (tiles), with the sky above the tallest level
        fx0, fy0, fx1, fy1 = frame
        sx = lambda x, y: ox + (x - y) * 64 - (x0 - y0) * 64 + 64
        sy = lambda x, y: oy + (x + y - x0 - y0) * 32 + 192
        left, right = sx(fx0, fy1), sx(fx1, fy0)
        top, bottom = sy(fx0, fy0) - 192 * (top_z + 1), sy(fx1, fy1) + 40
        img = img.crop((int(left), int(max(0, top)), int(right), int(bottom)))
    else:
        bbox = img.convert("RGB").point(lambda v: 255 if v > 14 else 0).getbbox()
        img = img.crop((max(0, bbox[0] - 30), 0, min(img.width, bbox[2] + 30), min(img.height, bbox[3] + 30)))
    img = img.resize((int(img.width * scale), int(img.height * scale)), Image.LANCZOS).convert("RGB")
    d = ImageDraw.Draw(img)
    fnt = ImageFont.truetype(L.FONT_BOLD, 22)
    d.text((15, 11), title, fill=(0, 0, 0), font=fnt)
    d.text((14, 10), title, fill=(240, 240, 240), font=fnt)
    return img


def draw_level(level, zz, crop, put, grass, open_doors, ground):
    x0, y0, x1, y1 = crop
    west, north = level.walls()
    objs = {}
    for o in level.objects:
        objs.setdefault((o["x"], o["y"]), []).append(o)
    doors = {(d["x"], d["y"], d["north"]): d for d in level.doors}
    tesla = {(t["x"], t["y"]): t for t in level.tesla}

    def door_tile(d, is_north):
        base = T.DOORS["lift"] if d.get("lift") else T.DOORS["gate"] if d.get("gate") else \
            T.DOORS["heavy"] if d["heavy"] else T.DOORS["standard"]
        opened = (d["x"], d["y"]) in open_doors or d.get("gate") in open_doors
        return TILES[base + (1 if is_north else 0) + (2 if opened else 0)]

    def wall_tile(ch, off):
        if ch.lower() in LOW:
            return TILES[WALLS[ch.lower()] + off]
        if ch.isupper():
            return TILES[WALLS[ch.lower()] + 3 + off]
        return TILES[WALLS[ch] + off]

    for s in range(x0 + y0, x1 + y1 + 1):
        for x in range(x0, x1 + 1):
            y = s - x
            if y < y0 or y > y1:
                continue
            if not (0 <= x < L.W and 0 <= y < L.H):
                if ground:
                    put(grass[(x * 31 + y * 17) % 5], x, y, zz)
                continue
            fl = level.floor[y][x]
            rock = fl == " "
            if fl == "n":
                if ground:
                    put(grass[(x * 31 + y * 17) % 5], x, y, zz)
            elif not rock:
                put(TILES[FLOOR_TILES[fl]], x, y, zz)
            elif ground and level is L.S:
                put(grass[(x * 31 + y * 17) % 5], x, y, zz)
            wc, nc = west[y][x], north[y][x]
            low = rock and level is L.U
            fix = stub if low else (lambda t: t)
            if wc != "." and nc != "." and wc == nc and wc.islower() and wc not in LOW:
                put(fix(TILES[WALLS[wc] + 2]), x, y, zz)
            else:
                for ch, off in ((wc, 0), (nc, 1)):
                    if ch != ".":
                        put(fix(wall_tile(ch, off)), x, y, zz)
            if wc == "." and nc == "." and 0 < x and 0 < y and y < L.H and north[y][x - 1] != "." and west[y - 1][x] != ".":
                post = T.PILLARS.get(north[y][x - 1].lower())
                if post is not None and north[y][x - 1].lower() not in LOW:
                    put(fix(TILES[post]), x, y, zz)
            for is_north in (False, True):
                d = doors.get((x, y, is_north))
                if d:
                    put(door_tile(d, is_north), x, y, zz)
            if (x, y) in tesla:
                put(OLD_TILES[8 if tesla[(x, y)]["north"] else 7], x, y, zz)
            for o in objs.get((x, y), []):
                k = o["kind"]
                if k == "prop":
                    put(TILES[PROPS[o["prop"]] + (0 if o["face"] == "n" else 1)], x, y, zz)
                elif k == "sign":
                    put(TILES[(SIGN_N if o["north"] else SIGN_W)[o["sign"]]], x, y, zz)
                elif k in ("pipes", "vent"):
                    put(TILES[T.FITTINGS[k] + (1 if o["north"] else 0)], x, y, zz)
                elif k == "ext":
                    put(TILES[T.EXTRA[o["ext"]] + (1 if o["face"] == "w" else 0)], x, y, zz)
                elif k == "liftpanel":
                    put(TILES[T.LIFT_PANEL + (1 if o["north"] else 0)], x, y, zz)
                elif k == "vprop":
                    # the game's furniture is not drawn here: the mod's closest tile stands in
                    stand = L.VPROPS[o["prop"]]["stand"] if "prop" in o else \
                        ("officechair" if o["s"].startswith("furniture_seating") else None)
                    face = o.get("face", "n")
                    if stand:
                        put(TILES[PROPS[stand] + (0 if face == "n" else 1)], x, y, zz)
                elif k == "land":
                    put(TILES[LAND[o["land"]] + (0 if o["face"] == "n" else 1)], x, y, zz)
                elif k == "tree":
                    put(TREE_BIG[o["n"] % 2], x, y, zz, -64, -224)
                elif k == "stairs":
                    put(TILES[T.STAIRS[o["dir"]] + o["piece"]], x, y, zz)
                elif k in MACHINES:
                    put(OLD_TILES[MACHINES[k]], x, y, zz)


def main():
    U, S = L.build()
    above = L.LEVELS_ABOVE
    shots = [
        ("rendu_exterieur_site", S, (-4, 66, 103, 158),
         "Site SCP vu de l'extérieur : route, enceinte en béton, tour de guet, bâtiment de la Porte A, hangar de la Porte B, clôture et lisière de forêt",
         0.3, dict(above=above, sky=True, frame=(-2, 70, 101, 156))),
        ("preview_gateb", S, (74, 98, 98, 128), "Porte B : hangar et monte-charge (toit retiré), sa propre route", 0.5,
         dict(above=above, hide=(1, 2, 3, 4), open_doors=("B",))),
        ("preview_surface_open", S, (24, 98, 56, 141), "Bâtiment de la Porte A, toit retiré : la cabine d'ascenseur",
         0.5, dict(above=above, hide=(1, 2, 3, 4), open_doors=("A", "MAIN", "INNER"))),
        ("preview_tower", S, (60, 128, 75, 144), "Tour de guet : escaliers, cabine vitrée, barbelés", 0.6,
         dict(above=above, sky=True, frame=(62, 130, 74, 142))),
        ("preview_lcz", U, (1, 0, 34, 24), "Confinement léger : cellules classe D, SCP-173, SCP-939", 0.5, {}),
        ("preview_hcz", U, (7, 47, 47, 64), "Confinement lourd : SCP-106, broyeur de fémur, portail Tesla", 0.5, {}),
        ("preview_ez", U, (30, 95, 60, 122), "Zone d'entrée : hall principal, cafétéria, hall de la Porte A", 0.5, {}),
        ("preview_corridor", U, (12, 9, 30, 24), "Détail : couloirs de 2 cases", 0.9, {}),
        ("preview_bureaux", U, (26, 11, 52, 23), "Bureau des chercheurs, bureau et archives (confinement léger)", 0.6, {}),
        ("preview_106", L.L, (9, 49, 34, 62), "SCP-106 : la grande chambre, sa fosse et le broyeur de fémur", 0.55,
         dict(above=[(1, U)])),
        ("preview_049", L.L, (42, 49, 71, 72), "Niveau inférieur : aile de SCP-049 (cellule, observation, morgue, bloc)",
         0.5, {}),
    ]
    for name, level, crop, title, scale, kw in shots:
        render(level, crop, title, scale, **kw).save(os.path.join(ART, name + ".png"))
        print(name)


if __name__ == "__main__":
    sys.exit(main())
