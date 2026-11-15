#!/usr/bin/env python3
"""
Draws the plan of the SCP site and writes it as Lua data for the mod.

The site is one underground level, laid out like SCP - Containment Breach:
three zones in a strip (Light Containment -> Heavy Containment -> Entrance
Zone), narrow 2-tile hallways, rooms hanging off them, keycard checkpoints
between zones, and a lift (Gate A) up to a walled compound on the surface.

Reference: the room meshes of SCP - Containment Breach (hallways are about
2 m wide in 8 m map cells) - see art/cb_textures/README.md.

Outputs:
  Contents/mods/SCPFoundation/42/media/lua/shared/SCP_Facility_Data.lua
  art/site_plan.png            (labelled top-down plan)

Usage: python3 tools/make_site_layout.py   (from the repository root)
Needs Pillow.
"""

import os
import random
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_facility_tiles as T   # tile numbers of the scp_facility_02 sheet

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LUA_OUT = os.path.join(ROOT, "Contents/mods/SCPFoundation/42/media/lua/shared/SCP_Facility_Data.lua")
PLAN_OUT = os.path.join(ROOT, "art", "site_plan.png")
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

W, H = 100, 156
ANCHOR = (40, 155)      # end of the access road: where it meets the town road, where the admin clicks

# Wall styles (letters used in the edge layers)
STYLE = {"EZ": "a", "LCZ": "b", "HCZ": "c", "CELL": "d", "BUNKER": "e", "PERIM": "f", "FORT": "x"}
# Floor letters: c concrete, t white tiles, m dark plate, g grating, h hazard threshold,
# e lift platform, a asphalt, k bunker slab
ZONE_FLOOR = {"LCZ": "c", "HCZ": "m", "EZ": "t"}
ZONE_CHAR = {"LCZ": "L", "HCZ": "H", "EZ": "E"}

rng = random.Random(173)


class Level:
    def __init__(self, name, enclosed_default):
        self.name = name
        self.floor = [[" "] * W for _ in range(H)]
        self.reg = [[0] * W for _ in range(H)]
        self.regions = [None]
        self.doors = []          # dict(x, y, north, level, heavy, gate)
        self.door_edges = set()  # (x, y, north)
        self.extra_walls = {}    # (x, y, north) -> style
        self.objects = []        # dict(kind, x, y, ...)
        self.lights = []
        self.tesla = []
        self.lifts = []
        self.cor_region = {}
        self.enclosed_default = enclosed_default

    # -- regions ------------------------------------------------------
    def new_region(self, **kw):
        kw.setdefault("enclosed", self.enclosed_default)
        self.regions.append(kw)
        return len(self.regions) - 1

    def fill(self, rid, x0, y0, x1, y1, floor, allow_same=False):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                cur = self.reg[y][x]
                if cur and not (allow_same and cur == rid):
                    raise SystemExit(f"{self.name}: overlap at {x},{y} ({self.regions[cur].get('name')})")
                self.reg[y][x] = rid
                self.floor[y][x] = floor

    def corridor(self, zone, x0, y0, x1, y1):
        if zone not in self.cor_region:
            self.cor_region[zone] = self.new_region(kind="corridor", zone=zone, style=STYLE[zone],
                                                    name="Couloir " + zone, corridor=True)
        self.fill(self.cor_region[zone], x0, y0, x1, y1, ZONE_FLOOR[zone], allow_same=True)

    def room(self, kind, zone, x, y, w, h, name, level=0, floor=None, style=None, heavy=None, **kw):
        rid = self.new_region(kind=kind, zone=zone, style=style or STYLE.get(zone, "a"), name=name, level=level,
                              heavy=(level >= 3) if heavy is None else heavy,
                              x0=x, y0=y, x1=x + w - 1, y1=y + h - 1, **kw)
        self.fill(rid, x, y, x + w - 1, y + h - 1, floor or ("t" if zone in ("LCZ", "EZ") else "m"))
        return rid

    def door(self, x, y, level=None, heavy=None):
        """Doorway tile in a one-tile-thick wall. The door hangs on its north or west edge."""
        if self.reg[y][x]:
            raise SystemExit(f"{self.name}: door on a used tile {x},{y}")
        ns = self.reg[y - 1][x] and self.reg[y + 1][x]
        we = self.reg[y][x - 1] and self.reg[y][x + 1]
        if bool(ns) == bool(we):
            raise SystemExit(f"{self.name}: door at {x},{y} does not join two areas")
        a, b = ((x, y - 1), (x, y + 1)) if ns else ((x - 1, y), (x + 1, y))
        ra, rb = self.regions[self.reg[a[1]][a[0]]], self.regions[self.reg[b[1]][b[0]]]
        owner = ra if not ra.get("corridor") else rb
        if level is None:
            level = owner.get("level", 0)
        if heavy is None:
            heavy = owner.get("heavy", level >= 3)
        owner.setdefault("doors", []).append((x, y))
        other = rb if owner is ra else ra
        if not other.get("corridor"):
            other.setdefault("doors", []).append((x, y))
        rid = self.new_region(kind="door", zone=owner["zone"], style=owner["style"], name="door", doorway=True)
        self.reg[y][x] = rid
        self.floor[y][x] = "h"
        self.doors.append(dict(x=x, y=y, north=bool(ns), level=level, heavy=bool(heavy)))
        self.door_edges.add((x, y, bool(ns)))

    def edge_door(self, x, y, north, level=0, heavy=False, gate=None, frame=True, lift=None):
        """Door on the north or west edge of (x, y), in a thin wall."""
        self.doors.append(dict(x=x, y=y, north=north, level=level, heavy=heavy, gate=gate, frame=frame, lift=lift))
        self.door_edges.add((x, y, north))

    # -- derived ------------------------------------------------------
    def region_at(self, x, y):
        if 0 <= x < W and 0 <= y < H and self.reg[y][x]:
            return self.regions[self.reg[y][x]]
        return None

    def enclosed(self, x, y):
        r = self.region_at(x, y)
        return bool(r and r["enclosed"])

    def walls(self):
        """Edge layers: '.', a wall style letter, or its capital for a door frame."""
        west = [["."] * W for _ in range(H)]
        north = [["."] * W for _ in range(H)]
        for y in range(H):
            for x in range(W):
                for is_north, layer, (ox, oy) in ((False, west, (x - 1, y)), (True, north, (x, y - 1))):
                    a, b = self.region_at(x, y), self.region_at(ox, oy)
                    ea, eb = bool(a and a["enclosed"]), bool(b and b["enclosed"])
                    ch = "."
                    if (x, y, is_north) in self.door_edges:
                        d = next(d for d in self.doors if (d["x"], d["y"], d["north"]) == (x, y, is_north))
                        if d.get("frame", True):
                            src = a if ea else b
                            ch = (src or a or b)["style"].upper()
                    elif (x, y, is_north) in self.extra_walls:
                        ch = self.extra_walls[(x, y, is_north)]
                    elif ea != eb or (ea and eb and a is not b and not self.passable(a, b)):
                        src = a if ea else b
                        # a cell wall facing a corridor still looks like the cell from inside
                        ch = src["style"]
                    layer[y][x] = ch
        return west, north

    @staticmethod
    def passable(a, b):
        return a.get("doorway") or b.get("doorway")


# ----------------------------------------------------------------------
# Underground level
# ----------------------------------------------------------------------

U = Level("underground", True)
C, R, D = U.corridor, U.room, U.door

# ---- Light Containment Zone (north) ----------------------------------
C("LCZ", 6, 10, 73, 11)      # hallways (2 tiles wide)
C("LCZ", 14, 22, 65, 23)
C("LCZ", 6, 34, 73, 35)
C("LCZ", 14, 12, 15, 21)
C("LCZ", 40, 12, 41, 21)
C("LCZ", 64, 12, 65, 21)
C("LCZ", 24, 24, 25, 33)
C("LCZ", 52, 24, 53, 33)
C("LCZ", 6, 12, 7, 33)
C("LCZ", 72, 12, 73, 33)
C("LCZ", 6, 1, 7, 9)         # Class-D wing

for i, cy in enumerate((1, 4, 7)):
    R("classd", "LCZ", 2, cy, 3, 2, "Cellule classe D", level=1, heavy=False, floor="c")
    D(5, cy)
    R("classd", "LCZ", 9, cy, 3, 2, "Cellule classe D", level=1, heavy=False, floor="c")
    D(8, cy)

R("scp173", "LCZ", 16, 1, 10, 8, "SCP-173", level=3, floor="g", style="d"); D(21, 9)
R("office", "LCZ", 28, 3, 5, 6, "Surveillance", level=1); D(30, 9)
R("scp914", "LCZ", 35, 2, 9, 7, "SCP-914", level=2); D(39, 9)
R("storage", "LCZ", 46, 4, 6, 5, "Réserve", level=2); D(48, 9)
R("scp500", "LCZ", 54, 5, 4, 4, "SCP-500", level=3, style="d"); D(55, 9)
R("anomalous", "LCZ", 60, 4, 5, 5, "Objets anormaux", level=3, style="d"); D(62, 9)
R("lab", "LCZ", 67, 2, 7, 7, "Salle de test", level=2); D(70, 9)

R("closet", "LCZ", 9, 13, 4, 4, "Placard", level=0); D(8, 14)
R("closet", "LCZ", 9, 18, 4, 3, "Local technique", level=1); D(13, 19)
R("scp939", "LCZ", 17, 13, 10, 8, "SCP-939", level=4, floor="g", style="d"); D(21, 12)
R("office", "LCZ", 29, 13, 5, 4, "Bureau", level=1); D(31, 12)
R("archive", "LCZ", 36, 13, 3, 5, "Archives", level=1); D(37, 12)
R("dorm", "LCZ", 29, 18, 6, 3, "Salle de repos", level=0); D(32, 21)
R("research", "LCZ", 43, 13, 8, 8, "Bureau des chercheurs", level=2); D(42, 16)
R("storage", "LCZ", 53, 13, 5, 4, "Réserve", level=2); D(55, 12)
R("office", "LCZ", 60, 13, 3, 4, "Bureau", level=1); D(61, 12)
R("dorm", "LCZ", 53, 18, 10, 3, "Salle de pause", level=0); D(58, 21)
R("electric", "LCZ", 67, 13, 4, 8, "Local électrique", level=2); D(66, 16)

R("showers", "LCZ", 9, 25, 6, 8, "Douches", level=0); D(8, 28)
R("storage", "LCZ", 17, 25, 6, 8, "Entrepôt", level=2); D(23, 28)
R("office", "LCZ", 27, 25, 6, 4, "Bureau", level=1); D(29, 24)
R("medical", "LCZ", 35, 25, 7, 4, "Infirmerie", level=2); D(38, 24)
R("lab", "LCZ", 44, 25, 7, 4, "Salle d'observation", level=2); D(47, 24)
R("archive", "LCZ", 27, 30, 12, 3, "Archives", level=1); D(32, 33)
R("closet", "LCZ", 41, 30, 10, 3, "Stockage", level=0); D(45, 33)
R("lab", "LCZ", 55, 25, 8, 8, "Laboratoire", level=2); D(54, 28)
R("security", "LCZ", 65, 25, 6, 8, "Poste de garde", level=2); D(71, 28)

R("dorm", "LCZ", 25, 37, 10, 5, "Réfectoire", level=0); D(30, 36)
R("guardroom", "LCZ", 39, 37, 15, 5, "Quartier des gardes", level=2); D(46, 36)

# checkpoints LCZ -> HCZ
C("LCZ", 20, 36, 21, 40); C("HCZ", 20, 42, 21, 47)
C("LCZ", 58, 36, 59, 40); C("HCZ", 58, 42, 59, 47)
R("checkpoint", "LCZ", 16, 38, 3, 3, "Guérite", level=2, heavy=False); D(19, 39)
R("checkpoint", "LCZ", 61, 38, 3, 3, "Guérite", level=2, heavy=False); D(60, 39)
D(20, 41, level=3, heavy=True)
D(58, 41, level=3, heavy=True)

# ---- Heavy Containment Zone (middle) ---------------------------------
C("HCZ", 8, 48, 71, 49)
C("HCZ", 8, 62, 45, 63)
C("HCZ", 34, 72, 71, 73)
C("HCZ", 8, 86, 71, 87)
C("HCZ", 8, 50, 9, 85)
C("HCZ", 70, 50, 71, 85)
C("HCZ", 34, 50, 35, 61)
C("HCZ", 44, 64, 45, 71)
C("HCZ", 22, 64, 23, 85)
C("HCZ", 56, 74, 57, 85)

# SCP-106: a giant chamber around a pit, like in the games. A ledge runs
# round it, a catwalk goes out to a platform in the middle, and the bottom
# of the pit (where 106 is kept) is on the level below. The femur breaker
# looks into it.
R("scp106", "HCZ", 11, 51, 17, 10, "SCP-106", level=5, floor="m", style="d")
R("femur", "HCZ", 29, 51, 4, 6, "Broyeur de fémur", level=5); D(28, 53, level=5); D(30, 50)
R("storage", "HCZ", 29, 58, 4, 3, "Stockage", level=2); D(33, 59)
PIT = (12, 53, 26, 59)
for y in range(PIT[1], PIT[3] + 1):
    for x in range(PIT[0], PIT[2] + 1):
        U.floor[y][x] = " "
for x in range(21, 27):
    U.floor[56][x] = "g"           # catwalk from the east ledge ...
for y in range(55, 58):
    for x in range(17, 21):
        U.floor[y][x] = "g"        # ... to the platform in the middle
R("research", "HCZ", 37, 51, 9, 10, "Bureau des chercheurs", level=2); D(36, 55)
# SCP-049 is kept one level down: a stair hall leads to its wing.
R("stairs049", "HCZ", 48, 51, 7, 8, "Escalier SCP-049", level=4); D(51, 50)
STAIRS049 = (53, 55)               # x, y of the top piece (the bottom one is 2 tiles south)
for p in range(3):
    U.floor[STAIRS049[1] + p][STAIRS049[0]] = " "
R("armory", "HCZ", 56, 51, 5, 8, "Armurerie", level=4); D(58, 50)
R("scp096", "HCZ", 63, 51, 6, 6, "SCP-096", level=4, floor="g", style="d"); D(69, 53)
R("scp035", "HCZ", 63, 58, 6, 6, "SCP-035", level=3, floor="g", style="d"); D(69, 60)
R("scp008", "HCZ", 47, 60, 9, 11, "SCP-008", level=4, style="d"); D(46, 66)
R("generators", "HCZ", 58, 65, 11, 6, "Salle des générateurs", level=3); D(63, 71)
R("scp079", "HCZ", 11, 65, 10, 8, "SCP-079", level=4, style="d"); D(21, 68)
R("scp966", "HCZ", 11, 75, 10, 10, "SCP-966", level=3, floor="g", style="d"); D(10, 79)
R("armory", "HCZ", 25, 65, 8, 6, "Armurerie", level=4); D(24, 67)
R("security", "HCZ", 35, 65, 8, 6, "Sécurité", level=2); D(43, 67)
R("storage", "HCZ", 25, 73, 8, 5, "Stockage", level=2); D(24, 75)
R("hazmat", "HCZ", 25, 80, 8, 5, "Vestiaire hazmat", level=2); D(28, 85)
R("medical", "HCZ", 35, 75, 9, 10, "Infirmerie", level=2); D(39, 74)
R("lab", "HCZ", 46, 75, 9, 10, "Laboratoire", level=2); D(55, 79)
R("servers", "HCZ", 59, 75, 10, 10, "Salle des serveurs", level=3, heavy=False); D(63, 74)

# checkpoints HCZ -> EZ
C("HCZ", 16, 88, 17, 90); C("EZ", 16, 92, 17, 95)
C("HCZ", 62, 88, 63, 90); C("EZ", 62, 92, 63, 95)
D(16, 91, level=3, heavy=True)
D(62, 91, level=3, heavy=True)
R("checkpoint", "HCZ", 19, 89, 3, 3, "Guérite", level=2, heavy=False); D(18, 90)
R("checkpoint", "HCZ", 65, 89, 3, 3, "Guérite", level=2, heavy=False); D(64, 90)

# ---- Entrance Zone (south) -------------------------------------------
C("EZ", 8, 96, 71, 97)
C("EZ", 8, 110, 71, 111)
C("EZ", 8, 98, 9, 109)
C("EZ", 70, 98, 71, 109)
C("EZ", 38, 98, 41, 109)     # main hall, 4 wide

R("office", "EZ", 11, 99, 6, 4, "Bureau", level=1); D(13, 98)
R("office", "EZ", 19, 99, 6, 4, "Bureau", level=1); D(21, 98)
R("conference", "EZ", 27, 99, 10, 4, "Salle de réunion", level=1); D(31, 98)
R("research", "EZ", 11, 104, 10, 5, "Bureau des chercheurs", level=2); D(15, 109)
R("medical", "EZ", 23, 104, 7, 5, "Infirmerie", level=2); D(26, 109)
R("security", "EZ", 32, 104, 5, 5, "Sécurité", level=2); D(37, 106)
R("cafeteria", "EZ", 43, 99, 12, 4, "Cafétéria", level=0); D(48, 98)
R("office", "EZ", 57, 99, 5, 4, "Bureau", level=1); D(59, 98)
R("office", "EZ", 64, 99, 5, 4, "Bureau", level=1); D(66, 98)
R("servers", "EZ", 43, 104, 8, 5, "Serveurs", level=3, heavy=False); D(42, 106)
R("storage", "EZ", 53, 104, 6, 5, "Réserve", level=2); D(55, 109)
R("warhead", "EZ", 61, 104, 8, 5, "Ogive Alpha", level=5); D(64, 109)

R("lockers", "EZ", 11, 113, 10, 6, "Vestiaire FIM", level=3, heavy=False); D(15, 112)
R("dorm", "EZ", 23, 113, 9, 6, "Dortoir", level=1); D(27, 112)
R("lobby", "EZ", 34, 113, 12, 8, "Hall de la Porte A", level=3)
D(38, 112, level=3, heavy=True); D(41, 112, level=3, heavy=True)
R("storage", "EZ", 48, 113, 10, 6, "Quai de livraison", level=2); D(52, 112)
R("director", "EZ", 60, 113, 9, 6, "Bureau du directeur", level=4, heavy=False); D(64, 112)

LIFT = (39, 116)   # 2x2 platform, same tiles on the surface

# Tesla gates (a line across a hallway)
U.tesla += [dict(x=16, y=48, north=False), dict(x=16, y=49, north=False),
            dict(x=40, y=86, north=False), dict(x=40, y=87, north=False),
            dict(x=70, y=66, north=True), dict(x=71, y=66, north=True),
            dict(x=50, y=72, north=False), dict(x=50, y=73, north=False)]

# ----------------------------------------------------------------------
# Level below the site (one level under the underground): the SCP-049 wing
# and the bottom of the SCP-106 pit.
# ----------------------------------------------------------------------

L = Level("lower", True)
L.corridor("HCZ", 52, 55, 54, 61)            # from the foot of the stairs
L.corridor("HCZ", 44, 62, 71, 63)
L.room("scp049", "HCZ", 56, 51, 14, 10, "SCP-049", level=4, floor="t", style="d"); L.door(55, 57)
L.room("obs049", "HCZ", 44, 51, 7, 10, "Observation SCP-049", level=3, floor="t"); L.door(51, 55)
L.room("morgue", "HCZ", 44, 65, 12, 6, "Morgue", level=3, floor="t"); L.door(48, 64)
L.room("surgery", "HCZ", 58, 65, 12, 6, "Bloc opératoire", level=3, floor="t"); L.door(62, 64)
# stairs up to the stair hall (bottom at the south)
L.objects += [dict(kind="stairs", dir="N", piece=p, x=STAIRS049[0], y=STAIRS049[1] + 2 - p) for p in range(3)]

# bottom of the 106 pit: stairs up the west side to the ledge
L.room("scp106pit", "HCZ", 12, 53, 15, 7, "Fosse de SCP-106", level=5, floor="k", style="d")
L.regions[-1]["doors"] = [(11, 56)]          # no door: reached by the stairs (keeps validate happy)
L.objects += [dict(kind="stairs", dir="W", piece=p, x=14 - p, y=58) for p in range(3)]
L.objects += [dict(kind="sign", sign="scp106", north=True, x=19, y=53)]

# ----------------------------------------------------------------------
# Surface: a fortified concrete compound reached by a road from town
#
#   road (south) -> main gate in a two-storey wall -> entrance court
#   (guard post, watchtower in the corner) -> inner gate -> three courts:
#   garage (west), main building with the Gate A lift (middle),
#   power house (east). Roofs, the upper course of the walls, the tower
#   floors and the barbed wire are on the levels above (UPPER).
# ----------------------------------------------------------------------

def lift_cabin(level, gate, label, at=LIFT, size=2, link="A"):
    """Platform, walls on three sides of the lift, sliding doors on the south
    side, and the call panel inside on the west wall."""
    for dx in range(size):
        for dy in range(size):
            level.floor[at[1] + dy][at[0] + dx] = "e"
            level.lifts.append(dict(x=at[0] + dx, y=at[1] + dy, link=link))
    for dy in range(size):
        level.extra_walls[(at[0], at[1] + dy, False)] = "e"
        level.extra_walls[(at[0] + size, at[1] + dy, False)] = "e"
    for dx in range(size):
        level.extra_walls[(at[0] + dx, at[1], True)] = "e"
        level.edge_door(at[0] + dx, at[1] + size, True, level=0, gate=gate, frame=False, lift=True)
    level.objects.append(dict(kind="liftpanel", north=False, x=at[0], y=at[1] + size - 1, level=label, link=link))


# Gate B: a 3x3 freight lift at the far east end of the Entrance Zone, up to
# a hangar outside the compound with its own road (the second way out).
LIFTB = (85, 108)
C("EZ", 72, 110, 79, 111)
R("lobbyb", "EZ", 81, 104, 11, 12, "Hall de la Porte B", level=3)
D(80, 110, level=3, heavy=True); D(80, 111, level=3, heavy=True)

lift_cabin(U, "LIFT_EZ", "SITE")
lift_cabin(U, "LIFTB_EZ", "SITE", at=LIFTB, size=3, link="B")

S = Level("surface", False)
UPPER = {z: Level(f"upper{z}", False) for z in (1, 2, 3, 4)}

COMPOUND = (8, 84, 71, 139)          # inside of the outer wall
ROAD = (37, 42)                      # road columns (6 wide); centre line on the west edge of x = 40
GATE_X = (38, 39, 40, 41)
INNER_Y = 126                        # north edge of this row: inner wall
TOWER = (68, 135, 71, 139)           # watchtower inside, in the south-east corner
BUILDING = (28, 102, 51, 121)        # main building (Gate A hall in the middle)
GUARD = (30, 133, 35, 138)
GARAGE = (12, 88, 23, 97)
POWER = (56, 88, 67, 97)


def paint(level, x0, y0, x1, y1, ch):
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            level.floor[y][x] = ch


def wall_box(level, x0, y0, x1, y1, style, skip=()):
    """Walls on the outline of a rectangle (edges of the tiles inside it)."""
    for y in range(y0, y1 + 1):
        for edge in ((x0, y, False), (x1 + 1, y, False)):
            if edge not in skip:
                level.extra_walls[edge] = style
    for x in range(x0, x1 + 1):
        for edge in ((x, y0, True), (x, y1 + 1, True)):
            if edge not in skip:
                level.extra_walls[edge] = style


def wall_h(level, y, xa, xb, style):
    for x in range(xa, xb + 1):
        level.extra_walls[(x, y, True)] = style


def wall_v(level, x, ya, yb, style):
    for y in range(ya, yb + 1):
        level.extra_walls[(x, y, False)] = style


def ext(level, name, x, y, face="n"):
    level.objects.append(dict(kind="ext", ext=name, face=face, x=x, y=y))


# ---- ground level -----------------------------------------------------
court = S.new_region(kind="yard", zone="SURFACE", style="x", name="Cour d'entrée")
S.fill(court, COMPOUND[0], INNER_Y, COMPOUND[2], COMPOUND[3], "p")
west_court = S.new_region(kind="yard", zone="SURFACE", style="x", name="Cour du garage")
S.fill(west_court, COMPOUND[0], COMPOUND[1], 25, INNER_Y - 1, "p")
mid_court = S.new_region(kind="yard", zone="SURFACE", style="x", name="Cour centrale")
S.fill(mid_court, 26, COMPOUND[1], 53, INNER_Y - 1, "p")
east_court = S.new_region(kind="yard", zone="SURFACE", style="x", name="Cour technique")
S.fill(east_court, 54, COMPOUND[1], COMPOUND[2], INNER_Y - 1, "p")
road = S.new_region(kind="road", zone="SURFACE", style="x", name="Route d'accès")
S.fill(road, ROAD[0], COMPOUND[3] + 1, ROAD[1], H - 1, "a")
apron = S.new_region(kind="apron", zone="SURFACE", style="x", name="Parvis")
S.fill(apron, 33, COMPOUND[3] + 1, ROAD[0] - 1, COMPOUND[3] + 3, "a")
S.fill(apron, ROAD[1] + 1, COMPOUND[3] + 1, 46, COMPOUND[3] + 3, "a", allow_same=True)

# asphalt inside: from the main gate to the Gate A doors, and in front of the garage
paint(S, ROAD[0], BUILDING[3] + 1, ROAD[1], COMPOUND[3], "a")
paint(S, 14, GARAGE[3] + 1, 21, 101, "a")
for y in range(BUILDING[3] + 1, H):
    if S.floor[y][40] == "a":
        S.floor[y][40] = "r"
for x in range(ROAD[0], ROAD[1] + 1):
    S.floor[146][x] = "s"            # stop line before the checkpoint


def carve(level, rect):
    for y in range(rect[1], rect[3] + 1):
        for x in range(rect[0], rect[2] + 1):
            level.reg[y][x] = 0


def building(kind, name, rect, level=0, floor="k", **kw):
    carve(S, rect)
    rid = S.new_region(kind=kind, zone="SURFACE", style="x", name=name, enclosed=True,
                       x0=rect[0], y0=rect[1], x1=rect[2], y1=rect[3], level=level, **kw)
    S.fill(rid, *rect, floor)
    return rid


# main building: Gate A hall in the middle, two wings
building("bunker", "Hall de la Porte A", (34, 102, 45, 121), level=2)
building("security", "Sécurité", (28, 102, 33, 111), level=2)
building("lockers", "Vestiaire FIM", (28, 112, 33, 121), level=3, heavy=False)
building("medical", "Infirmerie", (46, 102, 51, 111), level=2)
building("storage", "Réserve", (46, 112, 51, 121), level=2)
S.edge_door(34, 106, False, level=2)
S.edge_door(34, 116, False, level=3)
S.edge_door(46, 106, False, level=2)
S.edge_door(46, 116, False, level=2)
for x in GATE_X:   # Gate A: blast doors of the main building
    S.edge_door(x, BUILDING[3] + 1, True, level=2, heavy=True, gate="A", frame=False)
for x in (29, 30, 31, 32, 47, 48, 49, 50):     # window bands on the facade
    S.extra_walls[(x, BUILDING[3] + 1, True)] = "y"
for y in (104, 105, 108, 109, 114, 115, 118, 119):
    S.extra_walls[(BUILDING[0], y, False)] = "y"
    S.extra_walls[(BUILDING[2] + 1, y, False)] = "y"

lift_cabin(S, "LIFT_SURFACE", "SURFACE")

# Gate B hangar, east of the compound, with its own road to the south
HANGAR = (80, 102, 93, 117)
GATEB_X = (85, 86, 87, 88)
ROADB = (84, 89)
building("lobbyb", "Hangar de la Porte B", HANGAR, level=3, heavy=False)
lift_cabin(S, "LIFTB_SURFACE", "SURFACE", at=LIFTB, size=3, link="B")
wall_box(S, *HANGAR, "x")
for x in GATEB_X:
    del S.extra_walls[(x, HANGAR[3] + 1, True)]
    S.edge_door(x, HANGAR[3] + 1, True, level=3, heavy=True, gate="B", frame=False)
for x in (81, 82, 83, 90, 91, 92):
    S.extra_walls[(x, HANGAR[3] + 1, True)] = "y"
for y in (104, 105, 110, 111):
    S.extra_walls[(HANGAR[0], y, False)] = "y"
    S.extra_walls[(HANGAR[2] + 1, y, False)] = "y"
apron_b = S.new_region(kind="apron", zone="SURFACE", style="x", name="Parvis de la Porte B")
S.fill(apron_b, HANGAR[0], HANGAR[3] + 1, HANGAR[2], HANGAR[3] + 4, "a")
road_b = S.new_region(kind="road", zone="SURFACE", style="x", name="Route de la Porte B")
S.fill(road_b, ROADB[0], HANGAR[3] + 5, ROADB[1], H - 1, "a")
for y in range(HANGAR[3] + 5, H):
    S.floor[y][87] = "r"
S.objects += [dict(kind="sign", sign="gateb", north=True, x=84, y=HANGAR[3] + 1),
              dict(kind="sign", sign="logo", north=True, x=89, y=HANGAR[3] + 1)]

building("gatehouse", "Poste de garde", GUARD)
S.edge_door(GUARD[2] + 1, 135, False, level=0)
for x in range(GUARD[0] + 1, GUARD[2]):
    S.extra_walls[(x, GUARD[3] + 1, True)] = "y"
S.extra_walls[(GUARD[2] + 1, 137, False)] = "y"

building("garage", "Garage", GARAGE, floor="a")
for x in range(16, 20):
    S.edge_door(x, GARAGE[3] + 1, True, level=0, heavy=True, gate="GARAGE", frame=False)
building("powerhouse", "Centrale électrique", POWER, level=1)
S.edge_door(61, POWER[3] + 1, True, level=1)

building("tower", "Tour de guet", TOWER, floor="p")
S.edge_door(TOWER[0], TOWER[3], False, level=0)

# outer wall (two storeys), inner walls (one storey) and their gates
wall_box(S, *COMPOUND, "x")
for x in GATE_X:
    del S.extra_walls[(x, COMPOUND[3] + 1, True)]
    S.edge_door(x, COMPOUND[3] + 1, True, level=0, heavy=True, gate="MAIN", frame=False)
wall_h(S, INNER_Y, COMPOUND[0], COMPOUND[2], "x")
for x in GATE_X:
    del S.extra_walls[(x, INNER_Y, True)]
    S.edge_door(x, INNER_Y, True, level=2, heavy=True, gate="INNER", frame=False)
wall_v(S, 26, COMPOUND[1], INNER_Y - 1, "x")
wall_v(S, 54, COMPOUND[1], INNER_Y - 1, "x")
for y in range(112, 116):
    del S.extra_walls[(26, y, False)]
for y in range(98, 102):
    del S.extra_walls[(54, y, False)]
# the tower's own walls win over the outer wall where they meet
for y in range(TOWER[1], TOWER[3] + 1):
    S.extra_walls.pop((TOWER[2] + 1, y, False), None)
for x in range(TOWER[0], TOWER[2] + 1):
    S.extra_walls.pop((x, TOWER[3] + 1, True), None)

# stairs of the watchtower: up along its east side, then along its west side
S.objects += [dict(kind="stairs", dir="N", piece=p, x=TOWER[2], y=TOWER[3] - 1 - p) for p in range(3)]

# signs, floodlights, barriers
S.objects += [dict(kind="sign", sign="gatea", north=True, x=37, y=BUILDING[3] + 1),
              dict(kind="sign", sign="logo", north=True, x=42, y=BUILDING[3] + 1),
              dict(kind="sign", sign="logo", north=True, x=36, y=INNER_Y),
              dict(kind="sign", sign="danger", north=True, x=43, y=INNER_Y),
              dict(kind="sign", sign="security", north=False, x=GUARD[2] + 1, y=134),
              dict(kind="sign", sign="electric", north=True, x=59, y=POWER[3] + 1)]
for (x, y) in ((80, 119), (93, 119), (27, 127), (52, 127), (10, 130), (60, 128), (36, 99), (43, 99), (24, 86), (56, 123),
               (10, 123), (70, 86)):
    ext(S, "floodlight", x, y)
for (x, y, f) in ((37, 150, "n"), (38, 150, "n"), (41, 152, "n"), (42, 152, "n"),
                  (33, 141, "n"), (46, 141, "n")):
    ext(S, "barrier", x, y, f)
for (x, y, prop) in ((12, 100, "crate"), (13, 100, "crate"), (12, 101, "barrel"), (24, 118, "crate"),
                     (24, 119, "barrel"), (22, 110, "crate"), (57, 110, "crate"), (58, 110, "barrel"),
                     (69, 105, "barrel"), (69, 106, "barrel"), (62, 120, "crate"), (63, 120, "crate"),
                     (10, 136, "crate"), (11, 137, "barrel"), (57, 133, "crate"), (58, 133, "crate"),
                     (57, 134, "barrel"), (20, 128, "crate")):
    S.objects.append(dict(kind="prop", prop=prop, face="n" if (x + y) % 2 else "w", x=x, y=y))

# ---- surroundings: blend the site into the countryside ------------------
#   - a gravel patrol strip along the outside of the outer wall and the hangar
#   - a chain-link fence with barbed wire further out, crossed by the two roads
#   - between fence and wall the ground is kept but cleared ('n'), with
#     sandbags, floodlights and warning signs
#   - outside the fence: a forest edge (trees thinning out away from the
#     fence, bushes, rocks), dirt shoulders along the roads
FENCE_RECT = (3, 79, 97, 145)        # tiles inside the fence
land_rng = random.Random(1999)


def ground(x, y, ch, only_empty=True):
    if 0 < x < W - 1 and 0 < y < H and (not only_empty or S.floor[y][x] == " ") and not S.reg[y][x]:
        S.floor[y][x] = ch


# cleared ground inside the fence
for y in range(FENCE_RECT[1], FENCE_RECT[3] + 1):
    for x in range(FENCE_RECT[0], FENCE_RECT[2] + 1):
        ground(x, y, "n")
# gravel strips
for y in range(COMPOUND[1] - 2, COMPOUND[3] + 3):
    for x in range(COMPOUND[0] - 2, COMPOUND[2] + 3):
        if S.floor[y][x] == "n":
            S.floor[y][x] = "v"
for y in range(HANGAR[1] - 2, HANGAR[3] + 1):
    for x in range(HANGAR[0] - 2, HANGAR[2] + 3):
        if S.floor[y][x] == "n":
            S.floor[y][x] = "v"
# path between the compound strip and the hangar strip
for y in range(110, 112):
    for x in range(COMPOUND[2] + 3, HANGAR[0] - 2):
        if S.floor[y][x] == "n":
            S.floor[y][x] = "v"
# dirt shoulders along the roads, outside the compound
for y in range(COMPOUND[3] + 4, H):
    for x in (ROAD[0] - 1, ROAD[1] + 1):
        if S.floor[y][x] in " n":
            S.floor[y][x] = "u"
for y in range(HANGAR[3] + 5, H):
    for x in (ROADB[0] - 1, ROADB[1] + 1):
        if S.floor[y][x] in " n":
            S.floor[y][x] = "u"

# the fence (open where the roads cross it)
road_cols = set(range(ROAD[0] - 1, ROAD[1] + 2)) | set(range(ROADB[0] - 1, ROADB[1] + 2))
fx0, fy0, fx1, fy1 = FENCE_RECT
for x in range(fx0, fx1 + 1):
    S.extra_walls[(x, fy0, True)] = "q"
    if x not in road_cols:
        S.extra_walls[(x, fy1 + 1, True)] = "q"
for y in range(fy0, fy1 + 1):
    S.extra_walls[(fx0, y, False)] = "q"
    S.extra_walls[(fx1 + 1, y, False)] = "q"
for x in (ROAD[0] - 2, ROAD[1] + 2, ROADB[0] - 2, ROADB[1] + 2):
    ext(S, "floodlight", x, fy1)
    S.objects.append(dict(kind="land", land="warnsign", face="n", x=x, y=fy1 + 1))
# barrier across Gate B road at the fence
for x in (ROADB[0], ROADB[0] + 1, ROADB[1] - 1, ROADB[1]):
    ext(S, "barrier", x, fy1 + 2)

# sandbag posts and floodlights in the cleared zone, signs on the fence
for (x, y) in ((5, 82), (5, 141), (95, 82), (95, 141), (50, 81), (20, 81), (76, 130)):
    S.objects.append(dict(kind="land", land="sandbags", face="n", x=x, y=y))
for (x, y) in ((5, 100), (5, 120), (95, 100), (95, 125), (30, 80), (65, 80), (88, 80)):
    ext(S, "floodlight", x, y)
for x in range(fx0 + 6, fx1, 12):
    S.objects.append(dict(kind="land", land="warnsign", face="n", x=x, y=fy0 - 1))
for y in range(fy0 + 8, fy1, 14):
    S.objects.append(dict(kind="land", land="warnsign", face="w", x=fx0 - 1, y=y))
for (x, y) in ((76, 113), (77, 113), (76, 114)):
    S.objects.append(dict(kind="land", land="camonet", face="n", x=x, y=y))

# forest edge outside the fence: thick near it, thinning out
def dist_to_fence(x, y):
    dx = max(fx0 - x, 0, x - fx1)
    dy = max(fy0 - y, 0, y - fy1)
    return max(dx, dy)


taken_land = {(o["x"], o["y"]) for o in S.objects}
for y in range(1, H - 1):
    for x in range(1, W - 1):
        if S.floor[y][x] != " " or S.reg[y][x] or (x, y) in taken_land:
            continue
        d = dist_to_fence(x, y)
        if d < 2:
            continue
        p_tree = 0.32 if d <= 8 else 0.16
        r = land_rng.random()
        if r < p_tree:
            S.objects.append(dict(kind="tree", n=land_rng.randrange(1000), x=x, y=y))
        elif r < p_tree + 0.06:
            S.objects.append(dict(kind="land", land="bush", face=land_rng.choice("nw"), x=x, y=y))
        elif r < p_tree + 0.075:
            S.objects.append(dict(kind="land", land="rocks", face=land_rng.choice("nw"), x=x, y=y))

# ---- levels above -----------------------------------------------------
U1, U2, U3 = UPPER[1], UPPER[2], UPPER[3]

# upper course of the outer wall, barbed wire on top
for edge, style in list(S.extra_walls.items()):
    x, y, north = edge
    on_outline = (not north and x in (COMPOUND[0], COMPOUND[2] + 1)) or (north and y in (COMPOUND[1], COMPOUND[3] + 1))
    if on_outline and style == "x":
        U1.extra_walls[edge] = "x"
for x in GATE_X:   # lintel over the main gate
    U1.extra_walls[(x, COMPOUND[3] + 1, True)] = "x"
for edge in list(U1.extra_walls):
    x, y, north = edge
    in_tower = TOWER[0] <= x <= TOWER[2] + 1 and TOWER[1] <= y <= TOWER[3] + 1
    if not in_tower:
        U2.objects.append(dict(kind="ext", ext="wire", face="n" if north else "w", x=x, y=y))
for y in range(INNER_Y, INNER_Y + 1):
    for x in range(COMPOUND[0], COMPOUND[2] + 1):
        if x not in GATE_X:
            U1.objects.append(dict(kind="ext", ext="wire", face="n", x=x, y=y))

# roofs with a low wall around them
for rect in (BUILDING, GUARD, GARAGE, POWER, HANGAR):
    paint(U1, *rect, "o")
    wall_box(U1, *rect, "p")
# rooftop of the main building: solar panels and ventilation units, like the reference
for y in (104, 107, 110):
    for x in list(range(29, 35)) + list(range(45, 51)):
        ext(U1, "solar", x, y)
for (x, y) in ((38, 105), (41, 105), (38, 109), (41, 109), (63, 91), (59, 91), (82, 104), (91, 104),
               (82, 114), (91, 114)):
    ext(U1, "fan", x, y)
for x in range(30, 50, 3):
    ext(U1, "solar", x, 114)
    ext(U1, "solar", x + 1, 114)

# watchtower: rooms on z1 and z2, glazed cabin on z3, roof on z4.
# Flights of stairs go up along the east side, then the west side, then the east side again.
U4 = UPPER[4]
T0x, T0y, T1x, T1y = TOWER
for lvl in (U1, U2, U3):
    paint(lvl, *TOWER, "p")
paint(U4, *TOWER, "o")
for p in range(3):
    U1.floor[T1y - 1 - p][T1x] = " "           # hole over the first flight
    U2.floor[T1y - 1 - p][T0x] = " "           # ... the second
    U3.floor[T1y - 1 - p][T1x] = " "           # ... the third
U1.objects += [dict(kind="stairs", dir="N", piece=p, x=T0x, y=T1y - 1 - p) for p in range(3)]
U2.objects += [dict(kind="stairs", dir="N", piece=p, x=T1x, y=T1y - 1 - p) for p in range(3)]
wall_box(U1, *TOWER, "x")
wall_box(U2, *TOWER, "x")
wall_box(U3, *TOWER, "y")
wall_box(U4, *TOWER, "p")
ext(U4, "floodlight", T1x, T1y)
ext(U4, "floodlight", T0x, T0y, "w")

LEVELS_ABOVE = [(z, UPPER[z]) for z in (1, 2, 3, 4)]


# ----------------------------------------------------------------------
# Dressing: specials, props, lights, signs
# ----------------------------------------------------------------------


# ----------------------------------------------------------------------
# The game's own furniture (sprite names, facings and multi-tile parts read
# from the 42.22 tile definitions). Each entry: face "n" = against a north
# wall (front looks south), "w" = against a west wall (front looks east);
# a list of (sprite, dx, dy) pieces (dx east, dy south; several pieces on
# one tile are stacked: desk, then the computer on it). These are real
# game objects: desks, cabinets, lockers and fridges can be searched, beds
# slept in, chairs sat on. "stand" = the mod tile drawn in the previews.
# ----------------------------------------------------------------------

def _v(sheet, *pieces):
    return [(f"{sheet}_{i}", dx, dy) for (i, dx, dy) in pieces]


OFF1, OFF2 = "location_business_office_generic_01", "location_business_office_generic_02"
SEAT1, SEAT2, SEAT3 = "furniture_seating_indoor_01", "furniture_seating_indoor_02", "furniture_seating_indoor_03"
BED, MED = "furniture_bedding_01", "location_community_medical_01"
SHELF, STOR2 = "furniture_shelving_01", "furniture_storage_02"
COM, CNT, SINK, FRIDGE = "appliances_com_01", "fixtures_counters_01", "fixtures_sinks_01", "appliances_refrigeration_01"

VPROPS = {
    # desk (2 tiles) with a computer
    "desk": dict(stand="workstation",
                 n=_v(OFF1, (5, 0, 0), (6, 1, 0)) + _v(COM, (72, 0, 0)),
                 w=_v(OFF1, (1, 0, 0), (0, 0, 1)) + _v(COM, (73, 0, 0))),
    # the same with its swivel chair in front (the middle of offices)
    "workstation": dict(stand="workstation",
                        n=_v(OFF1, (5, 0, 0), (6, 1, 0)) + _v(COM, (72, 0, 0)) + _v(SEAT1, (51, 0, 1)),
                        w=_v(OFF1, (1, 0, 0), (0, 0, 1)) + _v(COM, (73, 0, 0)) + _v(SEAT1, (48, 1, 0))),
    "desklamp": dict(stand="desklamp",
                     n=_v(OFF1, (42, 0, 0), (43, 1, 0)) + _v("lighting_indoor_02", (2, 1, 0)) + _v(OFF2, (20, 0, 0))
                     + _v(SEAT1, (51, 0, 1)),
                     w=_v(OFF1, (41, 0, 0), (40, 0, 1)) + _v("lighting_indoor_02", (1, 0, 0)) + _v(OFF2, (23, 0, 1))
                     + _v(SEAT1, (48, 1, 1))),
    "cabinet": dict(stand="cabinet", n=_v(OFF1, (16, 0, 0)), w=_v(OFF1, (17, 0, 0))),
    "locker": dict(stand="locker", n=_v(STOR2, (0, 0, 0)), w=_v(STOR2, (1, 0, 0))),
    "milocker": dict(stand="locker", n=_v("location_military_generic_01", (22, 0, 0)),
                     w=_v("location_military_generic_01", (23, 0, 0))),
    "shelf": dict(stand="shelf", n=_v(SHELF, (26, 0, 0), (27, 1, 0)), w=_v(SHELF, (25, 0, 0), (24, 0, 1))),
    "bookcase": dict(stand="bookcase", n=_v(SHELF, (40, 0, 0)), w=_v(SHELF, (41, 0, 0))),
    "bed": dict(stand="bed", n=_v(BED, (35, 0, 0), (34, 0, 1)), w=_v(BED, (32, 0, 0), (33, 1, 0))),
    "bunkbed": dict(stand="bunkbed", n=_v(BED, (85, 0, 0), (84, 0, 1)), w=_v(BED, (86, 0, 0), (87, 1, 0))),
    "medbed": dict(stand="medbed", n=_v(BED, (65, 0, 0), (64, 0, 1)), w=_v(BED, (66, 0, 0), (67, 1, 0))),
    "morguetable": dict(stand="medbed", n=_v(MED, (79, 0, 0), (78, 0, 1)), w=_v(MED, (76, 0, 0), (77, 1, 0))),
    "sofa": dict(stand="sofa", n=_v(SEAT2, (24, 0, 0), (25, 1, 0)), w=_v(SEAT2, (27, 0, 0), (26, 0, 1))),
    "armchair": dict(stand="sofa", n=_v(SEAT2, (44, 0, 0)), w=_v(SEAT2, (45, 0, 0))),
    "chair": dict(stand="chair", n=_v(SEAT3, (69, 0, 0)), w=_v(SEAT3, (68, 0, 0))),
    "table": dict(stand="table", n=_v("furniture_tables_high_01", (4, 0, 0)), w=_v("furniture_tables_high_01", (5, 0, 0))),
    "longtable": dict(stand="table", n=_v("furniture_tables_high_02", (16, 0, 0), (17, 1, 0), (18, 2, 0)),
                      w=_v("furniture_tables_high_02", (21, 0, 0), (20, 0, 1), (19, 0, 2))),
    "vending": dict(stand="vending", n=_v("location_shop_accessories_01", (17, 0, 0)),
                    w=_v("location_shop_accessories_01", (16, 0, 0))),
    "soda": dict(stand="vending", n=_v("location_shop_accessories_01", (19, 0, 0)),
                 w=_v("location_shop_accessories_01", (18, 0, 0))),
    "plant": dict(stand="plant", n=_v("vegetation_indoor_01", (12, 0, 0)), w=_v("vegetation_indoor_01", (20, 0, 0))),
    "cooler": dict(stand="cooler", n=_v(OFF1, (49, 0, 0)), w=_v(OFF1, (48, 0, 0))),
    "labbench": dict(stand="labbench", n=_v(CNT, (37, 0, 0)), w=_v(CNT, (35, 0, 0))),
    "microscope": dict(stand="microscope", n=_v(CNT, (77, 0, 0)) + _v(MED, (136, 0, 0)),
                       w=_v(CNT, (75, 0, 0)) + _v(MED, (137, 0, 0))),
    "sink": dict(stand="labbench", n=_v(SINK, (33, 0, 0)), w=_v(SINK, (32, 0, 0))),
    "fridge": dict(stand="cabinet", n=_v(FRIDGE, (40, 0, 0)), w=_v(FRIDGE, (41, 0, 0))),
    "counter": dict(stand="labbench", n=_v(CNT, (77, 0, 0)), w=_v(CNT, (75, 0, 0))),
    "medcabinet": dict(stand="cabinet", n=_v(MED, (37, 0, 0)), w=_v(MED, (36, 0, 0))),
    "whiteboard": dict(stand="whiteboard", wall=True, n=_v(OFF1, (53, 0, 0), (54, 1, 0), (55, 2, 0)),
                       w=_v(OFF1, (52, 0, 0), (51, 0, 1), (50, 0, 2))),
    "corkboard": dict(stand=None, wall=True, n=_v(OFF1, (7, 0, 0)), w=_v(OFF1, (15, 0, 0))),
    "trash": dict(stand="trash", n=_v("trashcontainers_01", (18, 0, 0)), w=_v("trashcontainers_01", (19, 0, 0))),
    "secconsole": dict(stand="console", n=_v("security_01", (0, 0, 0)), w=_v("security_01", (1, 0, 0))),
}

# kind -> (loot, zombies outfit/count, scp, count, special)
T_GUARD = "SCP_ZombieGuard"
VANILLA = True          # False: only the mod's own furniture tiles
ROOMS = {
    "classd": dict(loot=["SCP_ClassD_Jumpsuit", 1], props=["bunkbed"]),
    "office": dict(loot=["SCP_Keycard_L1", 1, "SCP_Keycard_L2", 1, "SCP_Document_Containment", 1, "Torch", 1],
                   props=["bookcase", "printer", "cabinet", "cabinet", "plant", "corkboard", "coffee", "trash", "filingboxes"],
                   islands=(4, "workstation")),
    "research": dict(loot=["SCP_LabCoat", 1, "SCP_Keycard_L2", 1, "SCP_Keycard_L3", 1, "SCP_Document_Containment", 2,
                           "Torch", 1],
                     zombies=["SCP_Scientist", 2],
                     props=["bookcase", "bookcase", "whiteboard", "printer", "coffee", "microscope", "microscope",
                            "plant", "plant", "cabinet", "filingboxes", "trash", "cooler"],
                     islands=(12, "workstation")),
    "director": dict(loot=["SCP_Keycard_L5", 1, "SCP_Document_Containment", 2, "SCP_Document_008", 1],
                     props=["bookcase", "bookcase", "sofa", "armchair", "cabinet", "coffee", "plant", "plant", "corkboard"],
                     islands=(1, "desklamp")),
    "conference": dict(loot=["SCP_Document_Containment", 1], props=["whiteboard", "longtable", "chair", "chair", "chair",
                                                                     "plant", "coffee", "cabinet"],
                       islands=(1, "longtable")),
    "archive": dict(loot=["SCP_Document_Containment", 2, "SCP_Document_008", 1],
                    props=["shelf", "bookcase", "shelf", "bookcase", "cabinet", "cabinet", "filingboxes", "filingboxes"],
                    islands=(1, "desklamp")),
    "security": dict(loot=["SCP_MTF_Baton", 1, "SCP_MTF_Helmet", 1, "SCP_Keycard_L3", 1, "Torch", 1],
                     zombies=[T_GUARD, 2], props=["secconsole", "locker", "locker", "cooler", "trash", "rack", "corkboard"],
                     islands=(2, "workstation")),
    "guardroom": dict(loot=["SCP_MTF_Baton", 1, "SCP_Keycard_L2", 1, "Torch", 1], zombies=[T_GUARD, 3],
                      props=["bunkbed", "bunkbed", "bunkbed", "milocker", "milocker", "milocker", "table", "chair", "trash"]),
    "checkpoint": dict(loot=["SCP_Keycard_L3", 1], zombies=[T_GUARD, 1], props=["console", "chair", "locker"]),
    "armory": dict(loot=["SCP_MTF_Vest", 2, "SCP_MTF_Helmet", 2, "SCP_MTF_Uniform", 2, "SCP_MTF_Knife", 2,
                         "SCP_Keycard_L5", 1],
                   zombies=[T_GUARD, 3], props=["milocker", "milocker", "milocker", "milocker", "shelf", "crate", "crate", "shelf"]),
    "lockers": dict(loot=["SCP_MTF_Uniform", 1, "SCP_MTF_Helmet", 1, "SCP_GasMask", 1, "SCP_GasFilter", 2],
                    zombies=[T_GUARD, 2], props=["locker"] * 7),
    "storage": dict(loot=["SCP_GasMask", 1, "SCP_GasFilter", 3, "SCP_Hazmat_Suit", 1, "SCP_Keycard_L2", 1, "Torch", 1],
                    props=["shelf", "shelf", "crate", "crate", "crate", "barrel", "barrel"]),
    "closet": dict(loot=["Torch", 1, "SCP_GasFilter", 1], props=["shelf", "crate", "barrel"]),
    "electric": dict(loot=["Torch", 1], props=["rack", "rack", "console", "barrel"]),
    "hazmat": dict(loot=["SCP_Hazmat_Suit", 2, "SCP_GasMask", 2, "SCP_GasFilter", 4],
                   props=["locker", "locker", "locker", "shelf", "crate"]),
    "medical": dict(loot=["Bandage", 4, "Pills", 2, "SCP_Keycard_L3", 1],
                    props=["medbed", "medbed", "medbed", "medcabinet", "medcabinet", "sink", "fridge", "desk", "trash", "plant"]),
    "lab": dict(loot=["SCP_LabCoat", 1, "SCP_Hazmat_Suit", 1, "SCP_Document_Containment", 2, "SCP_Keycard_L3", 1],
                zombies=["SCP_Scientist", 2], props=["labbench", "sink", "microscope", "microscope", "fridge", "console", "cabinet", "whiteboard", "trash"],
                islands=(2, "workstation")),
    "dorm": dict(loot=["Torch", 1], zombies=["SCP_ClassD", 1], props=["bed", "bunkbed", "bed", "locker", "locker", "desk", "armchair", "plant", "trash"]),
    "showers": dict(loot=["SCP_ClassD_Jumpsuit", 2], zombies=["SCP_ClassD", 2], props=["locker", "locker", "barrel"]),
    "cafeteria": dict(loot=["SCP_Keycard_L1", 1], zombies=["SCP_Scientist", 1], special="scp294",
                      props=["counter", "counter", "fridge", "sink", "vending", "soda", "cooler", "trash", "plant", "corkboard"],
                      islands=(6, "longtable")),
    "servers": dict(loot=["SCP_Keycard_L4", 1], props=["rack"] * 8 + ["console"]),
    "generators": dict(loot=["SCP_Keycard_L4", 1, "Torch", 1], special="generators", props=["barrel", "barrel", "crate"]),
    "lobby": dict(loot=["SCP_Keycard_L1", 1], zombies=[T_GUARD, 2], props=["sofa", "sofa", "armchair", "plant", "plant", "secconsole", "cooler", "vending", "soda"]),
    "lobbyb": dict(loot=["SCP_Keycard_L2", 1, "Torch", 1], zombies=[T_GUARD, 2],
                   props=["crate", "crate", "crate", "barrel", "barrel", "console", "chair", "locker", "shelf"]),
    "warhead": dict(special="warhead", props=["console", "rack", "rack"]),
    "femur": dict(special="femur", props=["console", "locker"]),
    "scp173": dict(scp="SCP_173"),
    "scp500": dict(loot=["SCP_500_Pill", 1], props=["cabinet"]),
    "anomalous": dict(loot=["SCP_714_Ring", 1, "SCP_1025_Book", 1], props=["cabinet", "shelf", "labbench"]),
    "scp914": dict(special="scp914", loot=["SCP_Document_Containment", 1], props=["crate"]),
    "scp939": dict(scp="SCP_939", count=3, props=["crate", "crate", "shelf"]),
    "scp106": dict(),
    "scp106pit": dict(scp="SCP_106", loot=["SCP_Document_Containment", 1]),
    "stairs049": dict(props=["locker", "chair", "plant"]),
    "obs049": dict(loot=["SCP_Document_Containment", 1, "SCP_Keycard_L4", 1], zombies=["SCP_Scientist", 1],
                   props=["secconsole", "desk", "chair", "whiteboard", "cabinet", "fridge", "coffee"],
                   islands=(1, "workstation")),
    "morgue": dict(loot=["Bandage", 2], zombies=["SCP_ClassD", 3],
                   props=["morguetable", "morguetable", "morguetable", "fridge", "fridge", "sink", "medcabinet", "trash"]),
    "surgery": dict(loot=["Bandage", 3, "Pills", 1], zombies=["SCP_Scientist", 1],
                    props=["medbed", "counter", "sink", "medcabinet", "medcabinet", "microscope", "trash"],
                    islands=(1, "morguetable")),
    "scp049": dict(scp="SCP_049", loot=["SCP_Keycard_L5", 1], props=["bed", "bookcase", "desklamp", "armchair", "medcabinet", "microscope", "plant", "corkboard"]),
    "scp096": dict(scp="SCP_096"),
    "scp035": dict(loot=["SCP_035_Mask", 1], props=["cabinet"]),
    "scp008": dict(special="scp008", loot=["SCP_008_Sample", 2, "SCP_Document_008", 1, "SCP_GasFilter", 2],
                   props=["cabinet", "cabinet", "console", "barrel"]),
    "scp079": dict(special="scp079", props=["rack", "rack", "rack", "rack"]),
    "scp966": dict(scp="SCP_966", count=2),
    "bunker": dict(zombies=[T_GUARD, 2], props=["crate", "crate", "crate", "barrel", "barrel", "locker", "console"]),
    "gatehouse": dict(loot=["SCP_Keycard_L1", 1, "SCP_Keycard_L2", 1, "Torch", 1], zombies=[T_GUARD, 1],
                      props=["desk", "secconsole", "locker", "cooler", "trash"]),
}

SIGN_FOR = {"scp173": "scp173", "scp914": "scp914", "scp500": "scp500", "scp939": "scp939", "scp106": "scp106",
            "scp049": "scp049", "stairs049": "scp049", "obs049": "scp049", "scp096": "scp096", "scp035": "scp035", "scp008": "scp008", "scp079": "scp079",
            "scp966": "scp966", "warhead": "warhead", "femur": "femur", "armory": "danger", "generators": "electric",
            "electric": "electric", "bunker": "gatea", "lobby": "gatea", "lobbyb": "gateb", "cafeteria": "cafeteria",
            "medical": "medical", "security": "security", "checkpoint": "security", "guardroom": "security"}


def dress(level):
    used = set()

    def take(x, y):
        used.add((x, y))

    for l in level.lifts:
        take(l["x"], l["y"])
    for o in level.objects:
        if o["kind"] == "stairs":
            take(o["x"], o["y"])
            take(o["x"] - (o["dir"] == "W"), o["y"] - (o["dir"] == "N"))   # the way off the top

    for rid, r in enumerate(level.regions):
        if not r or "x0" not in r:
            continue
        spec = ROOMS.get(r["kind"], {})
        x0, y0, x1, y1 = r["x0"], r["y0"], r["x1"], r["y1"]
        cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
        if r["kind"] in ("bunker", "lobby", "lobbyb"):
            cx, cy = x0 + 2, cy   # keep the lift platform clear
        r["cx"], r["cy"] = cx, cy
        take(cx, cy)
        # tiles in front of the doors stay free
        blocked = set()
        for (dx, dy) in r.get("doors", []):
            for ox in (-1, 0, 1):
                for oy in (-1, 0, 1):
                    blocked.add((dx + ox, dy + oy))
        if level is S:
            for d in level.doors:
                for ox in (-1, 0, 1):
                    for oy in (-2, -1, 0, 1):
                        blocked.add((d["x"] + ox, d["y"] + oy))

        def free(x, y):
            return (x, y) not in used and (x, y) not in blocked and level.reg[y][x] == rid \
                and level.floor[y][x] != " "

        special = spec.get("special")
        top = cx
        if special == "scp914":
            for dx, kind in ((0, "scp914"), (-1, "scp914In"), (1, "scp914Out")):
                level.objects.append(dict(kind=kind, x=top + dx, y=y0)); take(top + dx, y0)
        elif special == "scp079":
            level.objects.append(dict(kind="terminal", x=top, y=y0)); take(top, y0)
        elif special == "scp294":
            level.objects.append(dict(kind="scp294", x=x1 - 1, y=y0)); take(x1 - 1, y0)
        elif special == "warhead":
            level.objects.append(dict(kind="warhead", x=top, y=y0)); take(top, y0)
        elif special == "femur":
            level.objects.append(dict(kind="femur", x=top, y=y0)); take(top, y0)
        elif special == "generators":
            for i in range(3):
                gx = x0 + 1 + i * 3
                level.objects.append(dict(kind="generator", x=gx, y=y0, n=i + 1)); take(gx, y0)

        def place(prop, face, x, y):
            """Puts one piece of furniture with its corner on (x, y) if all its tiles are free."""
            v = VPROPS.get(prop) if VANILLA else None
            if not v:
                if not free(x, y):
                    return False
                level.objects.append(dict(kind="prop", prop=prop, face=face, x=x, y=y)); take(x, y)
                return True
            cells = {(x + dx, y + dy) for (_, dx, dy) in v[face]}
            if not all(free(cx_, cy_) for cx_, cy_ in cells):
                return False
            for k, (sprite, dx, dy) in enumerate(v[face]):
                o = dict(kind="vprop", s=sprite, x=x + dx, y=y + dy)
                if k == 0:
                    o.update(prop=prop, face=face)    # the previews draw the mod's tile there
                level.objects.append(o)
            for c in cells:
                take(*c)
            return True

        # furniture along the north and west walls (the two walls that face the camera)
        slots = [(x, y0, "n") for x in range(x0, x1 + 1)] + [(x0, y, "w") for y in range(y0 + 1, y1 + 1)]
        rng.shuffle(slots)
        for prop in spec.get("props", []):
            tries = list(slots)
            for (x, y, face) in tries:
                if place(prop, face, x, y):
                    slots.remove((x, y, face))
                    break

        # desks in the middle of the room, each with its chair on its south side,
        # in rows with an aisle between the desks
        count, desk = spec.get("islands", (0, None))
        step = 3 if VANILLA else 2
        for y in range(y0 + 2, y1, 3):
            for x in range(x0 + 2, x1, step):
                if count > 0 and place(desk, "n", x, y):
                    count -= 1
        if count > 0 and spec.get("islands") and x1 - x0 >= 2 and y1 - y0 >= 2:
            # small room: one desk in the middle
            for x, y in ((cx + 1, cy), (cx - 1, cy), (cx + 1, cy - 1), (cx - 1, cy - 1), (cx, cy - 1)):
                if place(desk, "n", x, y):
                    break

        # room sign, on the room's own north wall
        sign = SIGN_FOR.get(r["kind"])
        if sign:
            for x in range(x0 + 1, x1):
                if (x, y0, True) not in level.door_edges:
                    level.objects.append(dict(kind="sign", sign=sign, north=True, x=x, y=y0))
                    break
        # ... and beside the door, on the hallway side, when that wall faces the camera
        for (dx, dy) in r.get("doors", []):
            if sign and level.reg[dy - 1][dx] == rid and level.region_at(dx, dy + 1) \
                    and level.region_at(dx, dy + 1).get("corridor"):
                sx = dx + 1 if level.region_at(dx + 1, dy + 1) else dx - 1
                if level.region_at(sx, dy + 1) and level.region_at(sx, dy + 1).get("corridor") \
                        and not level.region_at(sx, dy):
                    level.objects.append(dict(kind="sign", sign=sign, north=True, x=sx, y=dy + 1))
            if sign and level.reg[dy][dx - 1] == rid and level.region_at(dx + 1, dy) \
                    and level.region_at(dx + 1, dy).get("corridor"):
                sy = dy + 1
                if level.region_at(dx + 1, sy) and level.region_at(dx + 1, sy).get("corridor") \
                        and not level.region_at(dx, sy):
                    level.objects.append(dict(kind="sign", sign=sign, north=False, x=dx + 1, y=sy))

    # lights: every region gets its own (walls stop the light)
    for rid, r in enumerate(level.regions):
        if not r or r.get("doorway") or r["kind"] in ("apron",):
            continue
        step = 9 if r["kind"] == "yard" else 5
        mine = []
        cells = [(x, y) for y in range(H) for x in range(W) if level.reg[y][x] == rid]
        if "cx" in r and r["kind"] != "yard":
            mine.append((r["cx"], r["cy"]))
        for (x, y) in cells:
            if all(max(abs(x - lx), abs(y - ly)) >= step for lx, ly in mine):
                mine.append((x, y))
        level.lights += [dict(x=x, y=y) for x, y in mine]

    # zone signs and pipes on hallway walls that face the camera
    west, north = level.walls()
    n = 0
    for y in range(H):
        for x in range(W):
            r = level.region_at(x, y)
            if not r or not r.get("corridor"):
                continue
            taken = any(o["kind"] == "sign" and o["x"] == x and o["y"] == y for o in level.objects)
            if north[y][x] in "abc" and not taken:
                n += 1
                if n % 9 == 0:
                    level.objects.append(dict(kind="sign", sign=r["zone"].lower(), north=True, x=x, y=y))
                elif r["zone"] == "HCZ" and n % 3 == 0:
                    level.objects.append(dict(kind="pipes", north=True, x=x, y=y))
                elif n % 7 == 3:
                    level.objects.append(dict(kind="vent", north=True, x=x, y=y))
            elif west[y][x] in "abc" and not taken:
                n += 1
                if r["zone"] == "HCZ" and n % 3 == 0:
                    level.objects.append(dict(kind="pipes", north=False, x=x, y=y))


def validate(level):
    # every pair of touching tiles is the same area, or one is a doorway
    for y in range(H):
        for x in range(W):
            a = level.region_at(x, y)
            if not a or not a["enclosed"]:
                continue
            for ox, oy in ((1, 0), (0, 1)):
                b = level.region_at(x + ox, y + oy)
                if level is U and b and b["enclosed"] and a is not b and not Level.passable(a, b):
                    raise SystemExit(f"{level.name}: {a['name']} touches {b['name']} at {x},{y}")
            if x in (0, W - 1) or y in (0, H - 1):
                raise SystemExit(f"{level.name}: floor on the border at {x},{y}")
    if level is U:
        seen, todo = set(), [LIFT]
        while todo:
            x, y = todo.pop()
            if (x, y) in seen or not level.region_at(x, y):
                continue
            seen.add((x, y))
            todo += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
        for rid, r in enumerate(level.regions):
            if r and "x0" in r and (r["x0"], r["y0"]) not in seen:
                raise SystemExit(f"unreachable room {r['name']} at {r['x0']},{r['y0']}")
            if r and "x0" in r and not r.get("doors"):
                raise SystemExit(f"room without a door: {r['name']}")


# ----------------------------------------------------------------------
# Lua output
# ----------------------------------------------------------------------

def lua_str(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def lua_val(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, str):
        return lua_str(v)
    if isinstance(v, (list, tuple)):
        return "{ " + ", ".join(lua_val(i) for i in v) + " }"
    if isinstance(v, dict):
        return "{ " + ", ".join(f"{k} = {lua_val(val)}" for k, val in v.items() if val is not None) + " }"
    raise TypeError(v)


def level_lua(level, key, z=None):
    west, north = level.walls()
    out = [f"{key} = {{"]
    if z is not None:
        out.append(f"    z = {z},")
    for name, grid in (("floor", level.floor), ("west", west), ("north", north)):
        out.append(f"    {name} = {{")
        out += [f"        {lua_str(''.join(row))}," for row in grid]
        out.append("    },")
    if level in (U, L):
        out.append("    zone = {")
        for y in range(H):
            row = "".join(ZONE_CHAR.get((level.region_at(x, y) or {}).get("zone"), " ") for x in range(W))
            out.append(f"        {lua_str(row)},")
        out.append("    },")
    rooms = []
    for r in level.regions:
        if r and "x0" in r:
            spec = ROOMS.get(r["kind"], {})
            rooms.append(dict(kind=r["kind"], name=r["name"], zone=r["zone"], level=r.get("level", 0),
                              x0=r["x0"], y0=r["y0"], x1=r["x1"], y1=r["y1"], cx=r["cx"], cy=r["cy"],
                              roof=r.get("roof"), cell=(r["style"] == "d") or None,
                              loot=spec.get("loot"), zombies=spec.get("zombies"),
                              scp=spec.get("scp"), count=spec.get("count")))
    for name, items in (("rooms", rooms), ("doors", level.doors), ("objects", level.objects),
                        ("lights", level.lights), ("tesla", level.tesla), ("lifts", level.lifts)):
        out.append(f"    {name} = {{")
        out += [f"        {lua_val(i)}," for i in items]
        out.append("    },")
    out.append("}")
    return "\n".join(out)


# checked in the 42.22 packs (Tiles2x.pack); e_easternwhitepine does not exist
TREE_SPRITES = ["e_canadianhemlock_1_", "e_virginiapine_1_", "e_americanholly_1_", "e_riverbirch_1_",
                "e_redmaple_1_", "e_americanlinden_1_", "e_yellowwood_1_", "e_dogwood_1_"]


def tiles_lua():
    walls = dict(T.WALLS, f=T.PERIMETER)
    sign_w = {n: 40 + k for k, n in enumerate(T.SIGNS)}
    sign_n = {n: 48 + k for k, n in enumerate(T.SIGNS)}
    sign_w.update({n: 96 + k for k, n in enumerate(T.SIGNS2)})
    sign_n.update({n: 120 + k for k, n in enumerate(T.SIGNS2)})
    props = {name: T.PROP0 + 2 * k for k, (name, _) in enumerate(T.PROPS)}
    props.update({name: T.PROP2 + 2 * k for k, (name, _) in enumerate(T.PROPS2)})
    walls.update(x=T.FORT, y=T.WINDOW, p=T.PARAPET, q=T.FENCE)
    land = {name: T.LAND0 + 2 * k for k, (name, _) in enumerate(T.LAND)}
    # the game's own trees, tried in this order; the mod's pine when none is found
    trees = TREE_SPRITES
    extra = dict(T.EXTRA, liftPanel=T.LIFT_PANEL)
    floors = dict(T.FLOORS, **T.FLOORS3)
    return lua_val(dict(sheet=T.SHEET + "_", walls=walls, pillars=T.PILLARS, floors=floors, doors=T.DOORS,
                        fittings=T.FITTINGS, signW=sign_w, signN=sign_n, props=props, stairs=T.STAIRS,
                        ext=extra, lowWalls=dict(p=True, q=True), land=land, trees=trees))


def write_lua():
    text = f"""--[[
    Plan of the SCP site. GENERATED by tools/make_site_layout.py: edit that
    script and run it again instead of changing this file.

    One character = one tile, rows run north to south.
      floor : ' ' nothing, c concrete, t white tiles, m dark plate, g grating,
              h door threshold, e lift platform, a asphalt, k bunker slab,
              p pale concrete, r road centre line, s stop line, o concrete roof
      west / north : what stands on the west / north edge of the tile:
              '.' nothing, a-f a wall (a EZ, b LCZ, c HCZ, d containment cell,
              e bunker, f perimeter), x compound concrete, y window band,
              p low wall (can be climbed over); capitals: the same wall with a door frame
      zone  : L / H / E (Light Containment, Heavy Containment, Entrance Zone)

    D.tiles gives the tile numbers on the scp_facility_02 sheet:
      walls: +0 west, +1 north, +2 north-west corner, +3 / +4 door frames
      doors: +0 west, +1 north (closed); +2 / +3 the same, open
      props: +0 against a north wall, +1 against a west wall
      fittings: +0 on a west wall, +1 on a north wall
]]

require "SCP_System"

SCP.Facility = SCP.Facility or {{}}
SCP.Facility.Data = {{ width = {W}, height = {H}, anchor = {{ x = {ANCHOR[0]}, y = {ANCHOR[1]} }} }}
local D = SCP.Facility.Data

D.tiles = {tiles_lua()}

{level_lua(U, "D.underground")}

{level_lua(S, "D.surface")}

-- One level below the underground (z = underground - 1): the SCP-049 wing
-- and the bottom of the SCP-106 pit.
{level_lua(L, "D.lower", -1)}

-- Levels above the surface (z = 1 to 4): upper course of the outer wall,
-- roofs, the watchtower, barbed wire.
D.upper = {{}}
""" + "\n\n".join(level_lua(lvl, f"D.upper[{i + 1}]", z) for i, (z, lvl) in enumerate(LEVELS_ABOVE)) + "\n"
    with open(LUA_OUT, "w", encoding="utf-8") as f:
        f.write(text)


# ----------------------------------------------------------------------
# Plan picture
# ----------------------------------------------------------------------

FLOOR_RGB = {"c": (150, 150, 146), "t": (214, 214, 208), "m": (92, 96, 100), "g": (60, 64, 70), "h": (226, 178, 30),
             "e": (240, 200, 40), "a": (70, 72, 76), "k": (128, 130, 126), "p": (176, 178, 176), "r": (90, 88, 60),
             "s": (200, 200, 196), "o": (160, 162, 160),
             "n": (58, 80, 50), "v": (140, 136, 126), "u": (110, 92, 64)}
ZONE_TINT = {"LCZ": (236, 222, 150), "HCZ": (200, 96, 84), "EZ": (120, 160, 214), "SURFACE": (150, 170, 150)}
SCP_RGB = (176, 60, 52)


def draw_level(level, px, crop, title, labels=True):
    x0, y0, x1, y1 = crop
    west, north = level.walls()
    img = Image.new("RGB", ((x1 - x0 + 1) * px + 20, (y1 - y0 + 1) * px + 50), (16, 17, 19))
    d = ImageDraw.Draw(img)
    f = ImageFont.truetype(FONT, max(9, px - 2))
    fb = ImageFont.truetype(FONT_BOLD, 20)
    d.text((10, 8), title, fill=(235, 235, 235), font=fb)
    ox, oy = 10 - x0 * px, 40 - y0 * px
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            ch = level.floor[y][x]
            if ch == " ":
                if level is S:
                    d.rectangle([ox + x * px, oy + y * px, ox + x * px + px - 1, oy + y * px + px - 1], fill=(44, 62, 40))
                continue
            r = level.region_at(x, y)
            col = FLOOR_RGB[ch]
            if r and r["kind"].startswith("scp") and ch != "e":
                col = tuple((a + b) // 2 for a, b in zip(col, SCP_RGB))
            elif r and r.get("corridor"):
                t = ZONE_TINT[r["zone"]]
                col = tuple((a * 3 + b) // 4 for a, b in zip(col, t))
            d.rectangle([ox + x * px, oy + y * px, ox + x * px + px - 1, oy + y * px + px - 1], fill=col)
    for o in level.objects:
        if o["kind"] in ("sign", "pipes", "vent") or not (x0 <= o["x"] <= x1 and y0 <= o["y"] <= y1):
            continue
        col = {"prop": (120, 86, 50), "tree": (24, 46, 26), "land": (90, 120, 60)}.get(o["kind"], (60, 200, 220))
        d.rectangle([ox + o["x"] * px + 2, oy + o["y"] * px + 2, ox + o["x"] * px + px - 3, oy + o["y"] * px + px - 3], fill=col)
    for t in level.tesla:
        d.rectangle([ox + t["x"] * px + 1, oy + t["y"] * px + 1, ox + t["x"] * px + px - 2, oy + t["y"] * px + px - 2],
                    fill=(90, 150, 255))
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            X, Y = ox + x * px, oy + y * px
            for ch, line in ((west[y][x], [X, Y, X, Y + px]), (north[y][x], [X, Y, X + px, Y])):
                if ch == ".":
                    continue
                if ch.isupper():
                    d.line(line, fill=(40, 220, 90), width=3)
                else:
                    d.line(line, fill=(250, 250, 250) if ch not in "fxq" else
                            (230, 160, 60) if ch != "q" else (170, 176, 180), width=2)
    for dr in level.doors:
        if dr.get("gate"):
            X, Y = ox + dr["x"] * px, oy + dr["y"] * px
            d.line([X, Y, X + px, Y], fill=(255, 60, 60), width=5)
    if labels:
        for r in level.regions:
            if r and "x0" in r and r["kind"] != "classd":
                w = (r["x1"] - r["x0"] + 1) * px
                name = r["name"]
                words, lines, cur = name.split(" "), [], ""
                for wd in words:
                    if d.textlength((cur + " " + wd).strip(), font=f) > w - 4 and cur:
                        lines.append(cur); cur = wd
                    else:
                        cur = (cur + " " + wd).strip()
                lines.append(cur)
                if r.get("level"):
                    lines.append(f"N{r['level']}")
                ty = oy + (r["y0"] + r["y1"] + 1) * px / 2 - len(lines) * (px + 1) / 2
                for ln in lines:
                    tw = d.textlength(ln, font=f)
                    tx = ox + (r["x0"] + r["x1"] + 1) * px / 2 - tw / 2
                    d.text((tx + 1, ty + 1), ln, fill=(0, 0, 0), font=f)
                    d.text((tx, ty), ln, fill=(255, 255, 255), font=f)
                    ty += px + 1
    return img


def write_plan():
    px = 13
    a = draw_level(U, px, (0, 0, W - 1, 122), "Sous-sol : zone de confinement léger (haut), lourd (milieu), zone d'entrée (bas)")
    b = draw_level(S, px, (0, 76, W - 1, H - 1), "Surface : enceinte, Porte A, hangar de la Porte B, clôture, lisière de forêt")
    c = draw_level(L, 9, (8, 49, 73, 72), "Niveau inférieur : aile SCP-049, fond de la fosse de SCP-106")
    legend = Image.new("RGB", (b.width, a.height - b.height - c.height), (16, 17, 19))
    d = ImageDraw.Draw(legend)
    f = ImageFont.truetype(FONT, 15)
    items = [((250, 250, 250), "mur"), ((40, 220, 90), "porte à carte (N1 à N5 = niveau de carte)"),
             ((255, 60, 60), "grande porte (4 cases)"), ((240, 200, 40), "ascenseur de la Porte A (cabine dans un puits)"),
             ((90, 150, 255), "portail Tesla"), ((176, 60, 52), "cellule de confinement"),
             ((60, 200, 220), "machine / console"), ((120, 86, 50), "mobilier"),
             ((230, 160, 60), "mur d'enceinte (béton)"), ((70, 72, 76), "1 case = 1 tuile ; couloirs de 2 cases")]
    for i, (col, text) in enumerate(items):
        d.rectangle([14, 20 + i * 26, 34, 36 + i * 26], fill=col)
        d.text((44, 19 + i * 26), text, fill=(230, 230, 230), font=f)
    out = Image.new("RGB", (a.width + b.width, a.height), (16, 17, 19))
    out.paste(a, (0, 0)); out.paste(b, (a.width, 0)); out.paste(c, (a.width, b.height))
    out.paste(legend, (a.width, b.height + c.height))
    out.save(PLAN_OUT)


def build():
    """Checks and dresses both levels (once). Returns (underground, surface)."""
    if not getattr(build, "done", False):
        validate(U)
        validate(S)
        validate(L)
        dress(U)
        dress(S)
        dress(L)
        build.done = True
    return U, S


def main():
    build()
    write_lua()
    write_plan()
    rooms = sum(1 for r in U.regions if r and "x0" in r)
    print(f"rooms: {rooms}, doors: {len(U.doors)} + {len(S.doors)}, lights: {len(U.lights)} + {len(S.lights)}, "
          f"objects: {len(U.objects)} + {len(S.objects)}")


if __name__ == "__main__":
    sys.exit(main())
