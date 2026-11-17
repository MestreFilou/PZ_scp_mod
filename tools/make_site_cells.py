#!/usr/bin/env python3
"""
Builds the map cells that hold the SCP site: new land added to the game's
world (Build 42 cell files), so the site has its own place on the map.

The cells hold only the land: grass, a forest, a clearing where the site
stands, and the access road that links the site to a road of the game's map.
The site itself (walls, rooms, the underground levels) is still built by the
mod's Lua when the game starts (lua/server/SCP_Facility.lua), at the gate
written here into lua/shared/SCP_SiteLocation.lua.

Outputs (media/maps/SCP Site/):
  X_Y.lotheader, world_X_Y.lotpack, chunkdata_X_Y.bin   one set per cell
  objects.lua                     zones (forest, road)
  worldmap.xml, worldmap.xml.bin  the site and its road on the world map
  spawnpoints.lua, map.info       the "SCP Site" start region
  worldmap-annotations.lua        the "SITE SCP" label
and lua/shared/SCP_SiteLocation.lua (the gate, read by the mod's Lua),
art/renders/site_cells.png (top-down view of the cells).

File formats as written by osm2zomboid (MIT, github.com/jinxlover/osm2zomboid,
lotwriter.py, chunkdata.py, worldmapbin.py) and read by libpzmap
(github.com/LtdJorge/pzmap-rs). This script reads every file back to check it.

Usage: python3 tools/make_site_cells.py   (from the repository root)
Needs Pillow and numpy.
"""

import os
import random
import struct
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEDIA = os.path.join(ROOT, "Contents/mods/SCPFoundation/42/media")
MAP_DIR = os.path.join(MEDIA, "maps", "SCP Site")
LUA_OUT = os.path.join(MEDIA, "lua", "shared", "SCP_SiteLocation.lua")
RENDER = os.path.join(ROOT, "art", "renders", "site_cells.png")

CELL = 256              # squares per cell side (Build 42)
CHUNK = 8               # squares per chunk side
CPC = CELL // CHUNK     # chunks per cell side

# ---------------------------------------------------------------- placement
# The new cells: CELLS_W x CELLS_H cells from cell (CELL_X0, CELL_Y0).
# They must lie outside the game's own cells (no X_Y.lotheader of the game
# there), touching the edge of the world where one of its roads ends, so the
# road goes on into them (ROAD_ENTRY is that point, on the edge).
CELL_X0, CELL_Y0 = 78, 32
CELLS_W, CELLS_H = 2, 2
ROAD_ENTRY = (CELL_X0 * CELL, CELL_Y0 * CELL + 300)     # (x, y): where the road comes in
ROAD_SIDE = "W"                                         # edge it comes in by: W, E, N or S

# Size and gate of the site (from tools/make_site_layout.py: W, H, ANCHOR).
SITE_W, SITE_H = 100, 156
ANCHOR = (40, 155)
# Site origin (north-west corner), in squares from the cells' corner.
SITE_AT = (230, 120)

ROAD_HALF = 2           # the road is 2 * ROAD_HALF + 1 squares wide
CLEARING = 10           # free land around the site, in squares
TREE_DENSITY = 0.16
BUSH_DENSITY = 0.05
ZOMBIES = 3             # zombie intensity of the forest (0..255, towns are 20+)
SEED = 4242

GRASS = ["blends_natural_01_16", "blends_natural_01_21", "blends_natural_01_22", "blends_natural_01_23"]
ASPHALT = ["blends_street_01_80", "blends_street_01_85", "blends_street_01_86", "blends_street_01_87"]
TREES = ["vegetation_trees_01_8", "vegetation_trees_01_9", "vegetation_trees_01_10", "vegetation_trees_01_11"]
BUSHES = ["vegetation_foliage_01_%d" % i for i in range(8, 15)]

AW, AH = CELLS_W * CELL, CELLS_H * CELL
AX, AY = CELL_X0 * CELL, CELL_Y0 * CELL
SITE_X, SITE_Y = AX + SITE_AT[0], AY + SITE_AT[1]
GATE = (SITE_X + ANCHOR[0], SITE_Y + ANCHOR[1])


# ---------------------------------------------------------------- the land
def road_path():
    """Axis-aligned segments from the edge to the gate, as (x0, y0, x1, y1) world squares."""
    ex, ey = ROAD_ENTRY
    gx, gy = GATE
    bend_y = gy + 24                     # the road runs east-west a bit south of the gate
    if ROAD_SIDE in ("W", "E"):
        return [(ex, ey, ex + (40 if ROAD_SIDE == "W" else -40), ey),
                (ex + (40 if ROAD_SIDE == "W" else -40), ey, ex + (40 if ROAD_SIDE == "W" else -40), bend_y),
                (ex + (40 if ROAD_SIDE == "W" else -40), bend_y, gx, bend_y),
                (gx, bend_y, gx, gy)]
    return [(ex, ey, ex, bend_y), (ex, bend_y, gx, bend_y), (gx, bend_y, gx, gy)]


def road_rects():
    out = []
    for x0, y0, x1, y1 in road_path():
        xa, xb = sorted((x0, x1))
        ya, yb = sorted((y0, y1))
        out.append((xa - ROAD_HALF, ya - ROAD_HALF, xb + ROAD_HALF, yb + ROAD_HALF))   # inclusive
    return out


def build_land():
    """-> (tiles[y][x] = list of tile names, kind[y][x]) over the whole area."""
    rng = random.Random(SEED)
    kind = np.zeros((AH, AW), np.uint8)           # 0 forest, 1 clearing, 2 road, 3 site
    sx, sy = SITE_AT
    kind[max(0, sy - CLEARING):sy + SITE_H + CLEARING, max(0, sx - CLEARING):sx + SITE_W + CLEARING] = 1
    kind[sy:sy + SITE_H, sx:sx + SITE_W] = 3
    for xa, ya, xb, yb in road_rects():
        x0, y0 = max(0, xa - AX), max(0, ya - AY)
        x1, y1 = min(AW - 1, xb - AX), min(AH - 1, yb - AY)
        kind[y0:y1 + 1, x0:x1 + 1] = 2
    # a parking spot in front of the gate (where the region's players appear)
    gx, gy = GATE[0] - AX, GATE[1] - AY
    kind[gy + 1:gy + 16, gx - 8:gx + 9] = 2
    # trees are thinner along the road and the clearing
    free = (kind != 0).astype(np.float32)
    near = free.copy()
    for _ in range(4):
        near = np.maximum(near, np.maximum(np.roll(near, 1, 0), np.roll(near, -1, 0)))
        near = np.maximum(near, np.maximum(np.roll(near, 1, 1), np.roll(near, -1, 1)))
    # clumps: coarse random field, smoothed
    coarse = np.array([[rng.random() for _ in range(AW // 16 + 2)] for _ in range(AH // 16 + 2)])
    clump = np.kron(coarse, np.ones((16, 16)))[:AH, :AW]
    tiles = [[None] * AW for _ in range(AH)]
    for y in range(AH):
        for x in range(AW):
            k = kind[y, x]
            if k == 2:
                tiles[y][x] = [rng.choice(ASPHALT)]
                continue
            t = [rng.choice(GRASS)]
            if k == 0:
                p = TREE_DENSITY * (0.4 + 1.2 * clump[y, x]) * (0.3 if near[y, x] else 1.0)
                r = rng.random()
                if r < p:
                    t.append(rng.choice(TREES))
                elif r < p + BUSH_DENSITY:
                    t.append(rng.choice(BUSHES))
            tiles[y][x] = t
    return tiles, kind


# ---------------------------------------------------------------- cell files
def write_cell(cx, cy, tiles):
    """Writes X_Y.lotheader, world_X_Y.lotpack and chunkdata_X_Y.bin for one cell."""
    ox, oy = (cx - CELL_X0) * CELL, (cy - CELL_Y0) * CELL
    names, index = [], {}

    def tid(n):
        if n not in index:
            index[n] = len(names)
            names.append(n)
        return index[n]
    for y in range(CELL):
        for x in range(CELL):
            for n in tiles[oy + y][ox + x]:
                tid(n)
    # lotpack: 32 x 32 blocks (block index bx * 32 + by), each z 0..0, x 0..7, y 0..7
    blocks = []
    for bx in range(CPC):
        for by in range(CPC):
            out, skip = bytearray(), 0
            for x in range(CHUNK):
                for y in range(CHUNK):
                    t = tiles[oy + by * CHUNK + y][ox + bx * CHUNK + x]
                    if not t:
                        skip += 1
                        continue
                    if skip:
                        out += struct.pack("<ii", -1, skip)
                        skip = 0
                    out += struct.pack("<ii", len(t) + 1, -1)
                    out += struct.pack("<%di" % len(t), *[tid(n) for n in t])
            if skip:
                out += struct.pack("<ii", -1, skip)
            blocks.append(bytes(out))
    assert len(blocks) == CPC * CPC
    head = struct.pack("<4siI", b"LOTP", 1, len(blocks))
    pos = len(head) + 8 * len(blocks)
    table, body = bytearray(), bytearray()
    for b in blocks:
        table += struct.pack("<II", pos + len(body), 0)
        body += b
    with open(os.path.join(MAP_DIR, "world_%d_%d.lotpack" % (cx, cy)), "wb") as f:
        f.write(head + table + body)
    # lotheader: tile names, levels 0..0, no rooms, no buildings, zombie intensity
    h = bytearray(b"LOTH") + struct.pack("<ii", 1, len(names))
    for n in names:
        h += n.encode("utf8") + b"\n"
    h += struct.pack("<iiii", CHUNK, CHUNK, 0, 0)
    h += struct.pack("<ii", 0, 0)
    zb = bytearray(CPC * CPC)
    for bx in range(CPC):
        for by in range(CPC):
            x, y = ox + bx * CHUNK, oy + by * CHUNK
            inside_site = (SITE_AT[0] - CLEARING <= x + 4 < SITE_AT[0] + SITE_W + CLEARING and
                           SITE_AT[1] - CLEARING <= y + 4 < SITE_AT[1] + SITE_H + CLEARING)
            zb[bx * CPC + by] = 0 if inside_site else ZOMBIES
    with open(os.path.join(MAP_DIR, "%d_%d.lotheader" % (cx, cy)), "wb") as f:
        f.write(bytes(h + zb))
    # chunkdata: nothing blocks the zombies' pathing here (grass, trees, road) -> all chunks "empty"
    with open(os.path.join(MAP_DIR, "chunkdata_%d_%d.bin" % (cx, cy)), "wb") as f:
        f.write((1).to_bytes(2, "big") + bytes(CPC * CPC))
    return names


def read_cell(cx, cy):
    """Reads a cell back (libpzmap's rules) -> {(x, y): [tile names]} for squares that hold tiles."""
    b = open(os.path.join(MAP_DIR, "%d_%d.lotheader" % (cx, cy)), "rb").read()
    assert b[:4] == b"LOTH"
    ver, n = struct.unpack_from("<ii", b, 4)
    assert ver == 1
    p, names = 12, []
    for _ in range(n):
        e = b.index(b"\n", p)
        names.append(b[p:e].decode("utf8"))
        p = e + 1
    w, hh, zmin, zmax, nrooms, nbuild = struct.unpack_from("<iiiiii", b, p)
    assert (w, hh, zmin, zmax, nrooms, nbuild) == (8, 8, 0, 0, 0, 0)
    p += 24
    assert len(b) - p == CPC * CPC, "zombie bytes"
    lp = open(os.path.join(MAP_DIR, "world_%d_%d.lotpack" % (cx, cy)), "rb").read()
    magic, ver, nb = struct.unpack_from("<4siI", lp, 0)
    assert magic == b"LOTP" and ver == 1 and nb == CPC * CPC
    sq = {}
    for bi in range(nb):
        off, zero = struct.unpack_from("<II", lp, 12 + 8 * bi)
        assert zero == 0
        bx, by = divmod(bi, CPC)
        p, skip = off, 0
        for z in range(zmin, zmax + 1):
            for x in range(CHUNK):
                for y in range(CHUNK):
                    if skip > 0:
                        skip -= 1
                        continue
                    count, = struct.unpack_from("<i", lp, p)
                    p += 4
                    if count == -1:
                        skip, = struct.unpack_from("<i", lp, p)
                        p += 4
                        skip -= 1
                        continue
                    assert count > 1
                    room, = struct.unpack_from("<i", lp, p)
                    assert room == -1
                    ids = struct.unpack_from("<%di" % (count - 1), lp, p + 4)
                    p += 4 * count
                    sq[(bx * CHUNK + x, by * CHUNK + y)] = [names[i] for i in ids]
        end = struct.unpack_from("<I", lp, 12 + 8 * (bi + 1))[0] if bi + 1 < nb else len(lp)
        assert p == end, "block %d: read to %d, next block at %d" % (bi, p, end)
    cd = open(os.path.join(MAP_DIR, "chunkdata_%d_%d.bin" % (cx, cy)), "rb").read()
    assert cd[:2] == b"\x00\x01" and len(cd) == 2 + CPC * CPC
    return sq


# ---------------------------------------------------------------- other map files
def write_objects():
    """Zones: the whole area is deep forest, minus the clearing; the road is a Nav zone."""
    rows = []
    sx, sy = SITE_X - CLEARING, SITE_Y - CLEARING
    sw, sh = SITE_W + 2 * CLEARING, SITE_H + 2 * CLEARING
    # forest = area minus the clearing, as four rectangles around it
    for x, y, w, h in ((AX, AY, AW, sy - AY), (AX, sy + sh, AW, AY + AH - sy - sh),
                       (AX, sy, sx - AX, sh), (sx + sw, sy, AX + AW - sx - sw, sh)):
        if w > 0 and h > 0:
            rows.append(("", "DeepForest", x, y, w, h))
    for xa, ya, xb, yb in road_rects():
        xa, ya = max(xa, AX), max(ya, AY)
        xb, yb = min(xb, AX + AW - 1), min(yb, AY + AH - 1)
        rows.append(("", "Nav", xa, ya, xb - xa + 1, yb - ya + 1))
    with open(os.path.join(MAP_DIR, "objects.lua"), "w") as f:
        f.write("-- Made by tools/make_site_cells.py\nobjects = {\n")
        for name, typ, x, y, w, h in rows:
            f.write('  { name = "%s", type = "%s", x = %d, y = %d, z = 0, width = %d, height = %d },\n'
                    % (name, typ, x, y, w, h))
        f.write("}\n")


def worldmap_features():
    """-> {(cell x, cell y): [(type, rings, props)]}, coordinates local to 256-square cells."""
    feats = {}

    def rect(x0, y0, x1, y1, props):          # world squares, x1/y1 exclusive; split over cells
        for cy in range(y0 // CELL, (y1 - 1) // CELL + 1):
            for cx in range(x0 // CELL, (x1 - 1) // CELL + 1):
                a, b = max(x0, cx * CELL) - cx * CELL, max(y0, cy * CELL) - cy * CELL
                c, d = min(x1, (cx + 1) * CELL) - cx * CELL, min(y1, (cy + 1) * CELL) - cy * CELL
                ring = [(a, b), (c, b), (c, d), (a, d)]
                feats.setdefault((cx, cy), []).append(("Polygon", [ring], props))
    for xa, ya, xb, yb in road_rects():
        rect(max(xa, AX), max(ya, AY), min(xb, AX + AW - 1) + 1, min(yb, AY + AH - 1) + 1,
             {"highway": "tertiary"})
    # the surface compound (fence of make_site_layout.py: tiles 3..97 x 79..145)
    rect(SITE_X + 3, SITE_Y + 79, SITE_X + 98, SITE_Y + 146, {"building": "CommunityServices"})
    return feats


def write_worldmap():
    feats = worldmap_features()
    cells = sorted(feats)
    xml = ['<?xml version="1.0" encoding="UTF-8"?>', '<world version="1.0">']
    for cx, cy in cells:
        xml.append(' <cell x="%d" y="%d">' % (cx, cy))
        for typ, rings, props in feats[(cx, cy)]:
            xml += ['  <feature>', '   <geometry type="%s">' % typ]
            for ring in rings:
                xml.append('    <coordinates>')
                xml += ['     <point x="%d" y="%d"/>' % p for p in ring]
                xml.append('    </coordinates>')
            xml += ['   </geometry>', '   <properties>']
            xml += ['    <property name="%s" value="%s"/>' % kv for kv in props.items()]
            xml += ['   </properties>', '  </feature>']
        xml.append(' </cell>')
    xml.append('</world>')
    with open(os.path.join(MAP_DIR, "worldmap.xml"), "w") as f:
        f.write("\n".join(xml) + "\n")
    # binary form (worldmapbin.py of osm2zomboid): the game's XML reader fails on shapes
    index = {}

    def sid(s):
        return index.setdefault(s, len(index))
    body = bytearray()
    for cx, cy in cells:
        body += struct.pack("<iii", cx, cy, len(feats[(cx, cy)]))
        for typ, rings, props in feats[(cx, cy)]:
            body += struct.pack("<hB", sid(typ), len(rings))
            for ring in rings:
                body += struct.pack("<h", len(ring))
                for x, y in ring:
                    body += struct.pack("<hh", x, y)
            body += struct.pack("<B", len(props))
            for k, v in props.items():
                body += struct.pack("<hh", sid(k), sid(v))
    head = bytearray(b"IGMB") + struct.pack("<iiii", 2, CELL, len(cells), 1)
    head += struct.pack("<i", len(index))
    for s in sorted(index, key=index.get):
        e = s.encode("utf8")
        head += struct.pack("<h", len(e)) + e
    with open(os.path.join(MAP_DIR, "worldmap.xml.bin"), "wb") as f:
        f.write(bytes(head + body))
    return len(cells), sum(len(v) for v in feats.values())


def write_region():
    gx, gy = GATE
    spots = [(gx - 4, gy + 8), (gx, gy + 9), (gx + 4, gy + 8)]
    pts = ",\n".join("        { posX = %d, posY = %d, posZ = 0 }" % p for p in spots)
    with open(os.path.join(MAP_DIR, "spawnpoints.lua"), "w") as f:
        f.write("""-- Made by tools/make_site_cells.py.
-- SCP site region: everyone starts on the parking in front of the site gate.
-- The SCP occupations are then moved into their start room inside the site
-- (lua/shared/SCP_Professions.lua).
function SpawnPoints()
    local gate = {
%s,
    }
    return {
        unemployed = gate,
        scp_classd = gate,
        scp_scientist = gate,
        scp_mtf = gate,
    }
end
""" % pts)
    cxm, cym = SITE_X + SITE_W // 2, SITE_Y + SITE_H // 2
    with open(os.path.join(MAP_DIR, "map.info"), "w") as f:
        f.write("""title=Site SCP / SCP Foundation Site
lots=Muldraugh, KY
fixed2x=true
description=A Foundation containment site hidden in a forest at the edge of Kentucky, at the end of a lone road. Start at its gate, or inside it with the SCP occupations (Class-D, scientist, MTF guard). / Un site de confinement de la Fondation cache dans une foret au bout d'une route. Depart devant son portail, ou a l'interieur avec les metiers SCP.
zoomX=%d
zoomY=%d
zoomS=14.5
""" % (cxm, cym))
    with open(os.path.join(MAP_DIR, "worldmap-annotations.lua"), "w") as f:
        f.write("""-- Made by tools/make_site_cells.py. Label of the SCP site on the world map.
return function(mapUI)
    local ok, mapAPI = pcall(function() return mapUI.javaObject:getAPIv3() end)
    if not ok or not mapAPI then return end
    local symbolsAPI = mapAPI:getSymbolsAPIv2()
    -- the label style names come from the game; the river style is the one known for sure
    for _, style in ipairs({ "text-town", "text-water-nofade" }) do
        local done, symbol = pcall(symbolsAPI.addUntranslatedText, symbolsAPI, "SITE SCP", style, %d, %d)
        if done and symbol then
            pcall(function()
                symbol:setRGBA(0.6, 0.05, 0.05, 1.0)
                symbol:setAnchor(0.5, 0.5)
                symbol:setScale(3.0)
                symbol:setRotation(0.0)
                symbol:setMatchPerspective(true)
                symbol:setApplyZoom(true)
                symbol:setMinZoom(0.0)
            end)
            return
        end
    end
end
""" % (cxm, SITE_Y + 60))
    with open(LUA_OUT, "w") as f:
        f.write("""-- Made by tools/make_site_cells.py: where the site's own map cells put it.
SCP = SCP or {}
SCP.SiteLocation = {
    gate = { x = %d, y = %d },                       -- end of the access road, in front of the gate
    cells = { x0 = %d, y0 = %d, x1 = %d, y1 = %d },  -- the mod's cells (squares, x1/y1 excluded)
}
""" % (gx, gy, AX, AY, AX + AW, AY + AH))


def render(kind):
    col = np.array([[44, 82, 40], [96, 140, 70], [70, 70, 74], [150, 40, 40]], np.uint8)
    img = Image.fromarray(col[kind], "RGB")
    os.makedirs(os.path.dirname(RENDER), exist_ok=True)
    img.save(RENDER)


def main():
    os.makedirs(MAP_DIR, exist_ok=True)
    tiles, kind = build_land()
    for cy in range(CELL_Y0, CELL_Y0 + CELLS_H):
        for cx in range(CELL_X0, CELL_X0 + CELLS_W):
            names = write_cell(cx, cy, tiles)
            back = read_cell(cx, cy)
            ox, oy = (cx - CELL_X0) * CELL, (cy - CELL_Y0) * CELL
            assert len(back) == CELL * CELL
            for (x, y), t in back.items():
                assert t == tiles[oy + y][ox + x], (cx, cy, x, y)
            print("cell %d_%d: %d tile names, read back OK" % (cx, cy, len(names)))
    write_objects()
    nc, nf = write_worldmap()
    write_region()
    render(kind)
    print("world map: %d cells, %d features" % (nc, nf))
    print("gate at", GATE, " cells", (AX, AY), "to", (AX + AW, AY + AH))


if __name__ == "__main__":
    main()
