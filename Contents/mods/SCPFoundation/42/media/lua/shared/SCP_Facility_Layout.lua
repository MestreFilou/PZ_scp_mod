--[[
    SCP site layout, inspired by the classic SCP games:
      Entrance Zone (EZ)            : offices, security, Gate A to the surface
      Heavy Containment Zone (HCZ)  : SCP-096, SCP-106, SCP-049, armory
      Light Containment Zone (LCZ)  : Class-D cells, SCP-173, SCP-500, SCP-035

    Each level is a grid of rooms (ROOM x ROOM tiles). One character = one room:

      .  solid rock (nothing)          C  corridor
      K  checkpoint (keycard doors)    0-9 elevator (same digit = linked;
                                           0 on the top level goes to the surface)
      O  office          S  security room      A  armory
      D  Class-D cells   L  storage / lockers  M  medical bay
      H  research lab    R  generator room     G  reception / lobby
      T  SCP-173         P  SCP-500 vault      X  SCP-035
      Y  SCP-096         Z  SCP-106            N  SCP-049
      Q  SCP-079 (AI)

    Rooms open onto corridors through one door. Two rooms side by side do
    not connect. Corridors next to each other form one open hallway.
]]

require "SCP_System"

SCP.Facility = SCP.Facility or {}
local F = SCP.Facility

F.ROOM = 12
F.VERSION = 1

-- Levels from top to bottom. depth = offset below the site's top level.
F.Levels = {
    {
        id = "EZ", depth = 0,
        rows = {
            "OOS0SOO",
            "CCCCCCC",
            "OCGMGCO",
            "CCCKCCC",
            "OHC2CHO",
        },
    },
    {
        id = "HCZ", depth = -1,
        rows = {
            "ZCYCNCAR",
            "CCCCCCCC",
            "HC.LC.HM",
            "C1CCCK2K",
            "LQC.C.SH",
            "..CCC...",
        },
    },
    {
        id = "LCZ", depth = -2,
        rows = {
            "DDDCTCPL",
            "CCCCCCCC",
            "OMCXCOCL",
            "CCCCCCCC",
            "LOK.K.OD",
            "..C1C...",
        },
    },
}

local T = SCP.Types

-- level = keycard needed on the room's door (0 = no lock)
F.Rooms = {
    C = { corridor = true },
    K = { corridor = true, level = 3, name = "Checkpoint" },
    O = { level = 1, name = "Office",
          loot = { "SCP_Keycard_L1", 2, "SCP_Keycard_L2", 1, "SCP_Document_Containment", 2, "Torch", 1 } },
    S = { level = 2, name = "Security",
          loot = { "SCP_MTF_Baton", 1, "SCP_MTF_Helmet", 1, "SCP_Keycard_L3", 1, "Torch", 1 },
          zombies = { T.GUARD, 2 } },
    A = { level = 4, name = "Armory",
          loot = { "SCP_MTF_Vest", 2, "SCP_MTF_Helmet", 2, "SCP_MTF_Uniform", 2, "SCP_MTF_Knife", 2, "SCP_Keycard_L5", 1 },
          zombies = { T.GUARD, 3 } },
    D = { level = 1, name = "Class-D cells",
          loot = { "SCP_ClassD_Jumpsuit", 2 },
          zombies = { "SCP_ClassD", 3 } },
    L = { level = 2, name = "Storage",
          loot = { "SCP_GasMask", 1, "SCP_GasFilter", 3, "SCP_Hazmat_Suit", 1, "SCP_Keycard_L2", 1, "Torch", 1 } },
    M = { level = 2, name = "Medical bay",
          loot = { "Bandage", 4, "Pills", 2, "SCP_Keycard_L3", 1 } },
    H = { level = 2, name = "Research lab",
          loot = { "SCP_Hazmat_Suit", 1, "SCP_Document_Containment", 2, "SCP_Keycard_L3", 1 },
          zombies = { "SCP_Hazmat", 2 } },
    R = { level = 3, name = "Generator room", special = "generators",
          loot = { "SCP_Keycard_L4", 1, "Torch", 1 } },
    G = { level = 0, name = "Lobby",
          loot = { "SCP_Keycard_L1", 1 },
          zombies = { T.GUARD, 1 } },
    T = { level = 3, name = "SCP-173", scp = T.SCP173 },
    P = { level = 3, name = "SCP-500", loot = { "SCP_500_Pill", 1 } },
    X = { level = 3, name = "SCP-035", loot = { "SCP_035_Mask", 1 } },
    Y = { level = 4, name = "SCP-096", scp = T.SCP096 },
    Z = { level = 5, name = "SCP-106", scp = T.SCP106 },
    Q = { level = 4, name = "SCP-079", special = "scp079" },
    N = { level = 4, name = "SCP-049", scp = T.SCP049, loot = { "SCP_Keycard_L5", 1 } },
}
for d = 0, 9 do
    F.Rooms[tostring(d)] = { corridor = true, elevator = tostring(d), name = "Elevator" }
end

function F.size(level)
    return #level.rows[1], #level.rows
end

-- Largest footprint of all levels, in tiles.
function F.footprint()
    local w, h = 0, 0
    for _, lv in ipairs(F.Levels) do
        local c, r = F.size(lv)
        w, h = math.max(w, c * F.ROOM + 1), math.max(h, r * F.ROOM + 1)
    end
    return w, h
end

function F.charAt(level, cx, cy)
    local row = level.rows[cy + 1]
    if not row or cx < 0 or cx >= #row then return "." end
    return row:sub(cx + 1, cx + 1)
end

function F.solid(c) return c ~= "." and F.Rooms[c] ~= nil end

local DIRS = { { 0, -1 }, { 0, 1 }, { -1, 0 }, { 1, 0 } } -- N, S, W, E

-- A room has a single door: toward a plain corridor if it has one,
-- otherwise toward any corridor (checkpoint, elevator).
function F.doorSide(level, cx, cy)
    local fallback = nil
    for _, d in ipairs(DIRS) do
        local c = F.charAt(level, cx + d[1], cy + d[2])
        local r = F.Rooms[c]
        if r and r.corridor then
            if c == "C" then return d[1], d[2] end
            fallback = fallback or d
        end
    end
    if fallback then return fallback[1], fallback[2] end
    return nil
end

-- Center tile (local coordinates) of the room holding elevator `digit` on `level`.
function F.findElevator(level, digit)
    for cy = 0, #level.rows - 1 do
        local row = level.rows[cy + 1]
        for cx = 0, #row - 1 do
            if row:sub(cx + 1, cx + 1) == digit then
                local mid = math.floor(F.ROOM / 2)
                return cx * F.ROOM + mid, cy * F.ROOM + mid
            end
        end
    end
    return nil
end

-- Which level of the site (if any) a character is on.
function F.levelAt(x, y, z)
    local o = F.origin()
    if not o then return nil end
    local lx, ly = x - o.x, y - o.y
    for _, lv in ipairs(F.Levels) do
        local c, r = F.size(lv)
        if math.floor(z) == o.z + lv.depth and lx >= 0 and ly >= 0 and lx <= c * F.ROOM and ly <= r * F.ROOM then
            return lv
        end
    end
    return nil
end

-- Where the site is: { x, y, z } of the top level's north-west corner.
function F.origin()
    local md = ModData.get("SCPFoundation")
    if md and md.facility and md.facility.x then return md.facility end
    local x, y = SCP.opt("FacilityX"), SCP.opt("FacilityY")
    if x and y and x > 0 and y > 0 then
        return { x = x, y = y, z = SCP.opt("FacilityDepth") }
    end
    return nil
end
