--[[
    Builds the SCP site underground, a bit at a time: whenever a chunk of
    the surface above the site loads, the matching underground columns are
    built (floors, walls, keycard doors, elevators, loot, staff and SCPs).
    Each surface square remembers it was done, so nothing is built twice.

    The site is placed by an admin ("Build the SCP site here") or by the
    FacilityX / FacilityY sandbox options.
]]

require "SCP_System"
require "SCP_Doors"
require "SCP_Facility_Layout"
require "SCP_Spawner"

local F = SCP.Facility

-- Tiles used by the builder. Each zone has its own look.
-- Wall sprites follow the usual PZ sheet order: west wall, north wall,
-- north-west corner. Doors: west door, north door (closed sprites).
F.Sprites = F.Sprites or {
    EZ  = { floor = "floors_interior_tilesandwood_01_0", wallW = "walls_interior_house_01_0", wallN = "walls_interior_house_01_1", wallNW = "walls_interior_house_01_2" },
    HCZ = { floor = "floors_exterior_street_01_0",       wallW = "walls_interior_house_01_0", wallN = "walls_interior_house_01_1", wallNW = "walls_interior_house_01_2" },
    LCZ = { floor = "floors_interior_tilesandwood_01_0", wallW = "walls_interior_house_01_0", wallN = "walls_interior_house_01_1", wallNW = "walls_interior_house_01_2" },
    doorW = "fixtures_doors_01_0",
    doorN = "fixtures_doors_01_1",
    elevator = "floors_exterior_street_01_0",
    containmentFloor = "floors_exterior_street_01_0",
}

local origin = nil       -- cached F.origin()
local fw, fh = F.footprint()
local spawnQueue = {}

local function refreshOrigin() origin = F.origin() end

------------------------------------------------------------------------
-- Low level placement
------------------------------------------------------------------------

local function spriteOk(name)
    return name and getSprite and getSprite(name) ~= nil
end

local warned = {}
local function warnSprite(name)
    if warned[name] then return end
    warned[name] = true
    SCP.log("missing tile sprite:", tostring(name), "- edit SCP.Facility.Sprites")
end

local function addFloor(sq, sprite)
    if sq:getFloor() then return end
    if not spriteOk(sprite) then warnSprite(sprite) return end
    if sq.addFloor then
        if pcall(sq.addFloor, sq, sprite) then return end
    end
    local ok, obj = pcall(IsoObject.new, getCell(), sq, sprite)
    if ok and obj then sq:AddTileObject(obj) end
end

local function addObject(sq, sprite)
    if not spriteOk(sprite) then warnSprite(sprite) return nil end
    local ok, obj = pcall(IsoObject.new, getCell(), sq, sprite)
    if ok and obj then
        sq:AddTileObject(obj)
        return obj
    end
    return nil
end

local function addDoor(sq, north, level)
    local sprite = north and F.Sprites.doorN or F.Sprites.doorW
    if not spriteOk(sprite) then warnSprite(sprite) return end
    local ok, door = pcall(IsoDoor.new, getCell(), sq, sprite, north)
    if not ok or not door then return end
    sq:AddSpecialObject(door)
    if level and level > 0 then
        door:getModData().SCP_KeyLevel = level
        SCP.Doors.setLocked(door, true)
        local world = SCP.world()
        world.doors = world.doors or {}
        world.doors[SCP.Doors.key(sq)] = level
    end
end

------------------------------------------------------------------------
-- What goes on each edge between two rooms
------------------------------------------------------------------------

-- Returns nil (nothing), "wall" or "door", plus the door's keycard level.
local function edgeKind(level, ax, ay, bx, by, pos)
    local a, b = F.charAt(level, ax, ay), F.charAt(level, bx, by)
    local sa, sb = F.solid(a), F.solid(b)
    if not sa and not sb then return nil end
    if not (sa and sb) then return "wall" end
    local ra, rb = F.Rooms[a], F.Rooms[b]
    local mid = math.floor(F.ROOM / 2)
    if ra.corridor and rb.corridor then
        local lvl = math.max(ra.level or 0, rb.level or 0)
        if lvl == 0 then return nil end
        if pos == mid then return "door", lvl end
        return "wall"
    end
    if ra.corridor or rb.corridor then
        -- Room next to a corridor: one door, on the side the room picked.
        local rx, ry, cx, cy, room = ax, ay, bx, by, ra
        if ra.corridor then rx, ry, cx, cy, room = bx, by, ax, ay, rb end
        local dx, dy = F.doorSide(level, rx, ry)
        if dx and rx + dx == cx and ry + dy == cy and pos == mid then
            return "door", room.level or 0
        end
        return "wall"
    end
    return "wall"
end

------------------------------------------------------------------------
-- Room contents (placed once, from the room's center tile)
------------------------------------------------------------------------

local function roomContents(level, cx, cy, ch, x, y, z)
    local room = F.Rooms[ch]
    local function rand(a, b) return ZombRand(a, b + 1) end
    local half = math.floor(F.ROOM / 2) - 2

    -- Loot on the floor
    local loot = room.loot
    if loot then
        for i = 1, #loot, 2 do
            local itemType = loot[i]
            if not itemType:find("%.") then itemType = "Base." .. itemType end
            for _ = 1, loot[i + 1] do
                local sq = getCell():getOrCreateGridSquare(x + rand(-half, half), y + rand(-half, half), z)
                if sq then pcall(sq.AddWorldInventoryItem, sq, itemType, ZombRandFloat(0.1, 0.9), ZombRandFloat(0.1, 0.9), 0) end
            end
        end
    end

    -- Staff and SCPs are spawned a little later (not during chunk loading).
    if room.zombies then
        table.insert(spawnQueue, { outfit = room.zombies[1], count = room.zombies[2], x = x, y = y, z = z })
    end
    if room.scp then
        table.insert(spawnQueue, { scp = room.scp, x = x, y = y, z = z })
    end

    -- Elevator marker
    if room.elevator then
        local obj = addObject(getCell():getOrCreateGridSquare(x, y, z), F.Sprites.elevator)
        if obj then
            obj:getModData().SCP_Elevator = { level = level.id, link = room.elevator }
        end
    end
end

------------------------------------------------------------------------
-- One tile of one level
------------------------------------------------------------------------

local function buildTile(level, lx, ly, x, y, z)
    local S = F.ROOM
    local cx, cy = math.floor(lx / S), math.floor(ly / S)
    local ix, iy = lx - cx * S, ly - cy * S
    local here = F.charAt(level, cx, cy)
    local west, north, westDoorLevel, northDoorLevel
    if ix == 0 then west, westDoorLevel = edgeKind(level, cx, cy, cx - 1, cy, iy) end
    if iy == 0 then north, northDoorLevel = edgeKind(level, cx, cy, cx, cy - 1, ix) end
    if not F.solid(here) and not west and not north then return end

    local sq = getCell():getOrCreateGridSquare(x, y, z)
    if not sq then return end
    local sprites = F.Sprites[level.id] or F.Sprites.EZ

    if F.solid(here) then
        local room = F.Rooms[here]
        addFloor(sq, room.scp and F.Sprites.containmentFloor or sprites.floor)
    end

    if west == "wall" and north == "wall" then
        addObject(sq, sprites.wallNW)
    else
        if west == "wall" then addObject(sq, sprites.wallW) end
        if north == "wall" then addObject(sq, sprites.wallN) end
    end
    if west == "door" then addDoor(sq, false, westDoorLevel) end
    if north == "door" then addDoor(sq, true, northDoorLevel) end

    local mid = math.floor(S / 2)
    if F.solid(here) and ix == mid and iy == mid then
        roomContents(level, cx, cy, here, x, y, z)
    end

    pcall(sq.RecalcProperties, sq)
    pcall(sq.RecalcAllWithNeighbours, sq, true)
end

------------------------------------------------------------------------
-- One surface column -> every level under it
------------------------------------------------------------------------

local function buildColumn(surfaceSq)
    local o = origin
    local x, y = surfaceSq:getX(), surfaceSq:getY()
    local lx, ly = x - o.x, y - o.y
    for _, level in ipairs(F.Levels) do
        local cols, rows = F.size(level)
        if lx <= cols * F.ROOM and ly <= rows * F.ROOM then
            buildTile(level, lx, ly, x, y, o.z + level.depth)
        end
    end
    -- Gate A on the surface, right above the site's corner.
    if lx == 0 and ly == 0 then
        local obj = addObject(surfaceSq, F.Sprites.elevator)
        if obj then obj:getModData().SCP_Elevator = { level = "SURFACE", link = "0" } end
    end
    surfaceSq:getModData().SCP_FacilityBuilt = F.VERSION
end

local function inFootprint(x, y)
    return origin and x >= origin.x and y >= origin.y and x <= origin.x + fw and y <= origin.y + fh
end

local function onLoadGridsquare(sq)
    if isClient() or not origin then return end
    if sq:getZ() ~= 0 then return end
    local x, y = sq:getX(), sq:getY()
    if not inFootprint(x, y) then return end
    if sq:getModData().SCP_FacilityBuilt == F.VERSION then return end
    buildColumn(sq)
end

Events.LoadGridsquare.Add(onLoadGridsquare)

-- Build what is already loaded (right after the site was placed).
function F.buildLoaded()
    if not origin then return end
    for x = origin.x, origin.x + fw do
        for y = origin.y, origin.y + fh do
            local sq = getCell():getGridSquare(x, y, 0)
            if sq and sq:getModData().SCP_FacilityBuilt ~= F.VERSION then buildColumn(sq) end
        end
    end
end

------------------------------------------------------------------------
-- Delayed spawns
------------------------------------------------------------------------

local function processSpawns()
    if #spawnQueue == 0 then return end
    local queue = spawnQueue
    spawnQueue = {}
    local world = SCP.world()
    world.facility = world.facility or {}
    world.facility.spawned = world.facility.spawned or {}
    for _, s in ipairs(queue) do
        local key = s.x .. "," .. s.y .. "," .. s.z
        if not world.facility.spawned[key] then
            world.facility.spawned[key] = true
            if s.scp then
                local list = SCP.Spawner.spawn(s.scp, s.x, s.y, s.z, 1)
                for _, z in ipairs(list) do z:getModData().SCP_Contained = true end
                table.insert(world.points, { type = s.scp, x = s.x, y = s.y, z = s.z, contained = true })
            else
                SCP.Spawner.spawn(s.outfit, s.x, s.y, s.z, s.count)
            end
        end
    end
    if isServer() then ModData.transmit("SCPFoundation") end
end

Events.EveryOneMinute.Add(processSpawns)

------------------------------------------------------------------------
-- Placement
------------------------------------------------------------------------

SCP.ServerCommands.PlaceFacility = function(player, args)
    if not SCP.isAdmin(player) then return end
    local world = SCP.world()
    if world.facility and world.facility.x then
        SCP.sendToClient(player, "Notify", { key = "UI_SCP_FacilityExists" })
        return
    end
    world.facility = { x = args.x, y = args.y, z = SCP.opt("FacilityDepth"), spawned = {} }
    refreshOrigin()
    if isServer() then ModData.transmit("SCPFoundation") end
    F.buildLoaded()
    SCP.sendToClient(player, "Notify", { key = "UI_SCP_FacilityPlaced" })
    SCP.log("SCP site placed at", args.x, args.y, "depth", world.facility.z)
end

Events.OnInitGlobalModData.Add(function() refreshOrigin() end)
Events.OnGameStart.Add(function() refreshOrigin() end)
if Events.OnServerStarted then Events.OnServerStarted.Add(function() refreshOrigin() end) end
