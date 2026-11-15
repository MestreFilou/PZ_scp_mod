--[[
    Builds the SCP site from its plan (shared/SCP_Facility_Data.lua), a bit
    at a time: whenever a square of the surface above the site loads, the
    column under it is built:
      - the underground level: floor, walls, door frames, keycard doors,
        corner posts, furniture, machines, signs, loot, staff and SCPs;
      - on the surface: the access road, then inside the compound the
        ground is cleared and paved, and the two-storey outer wall, the
        inner walls, the main building over the lift, the guard post, the
        garage, the power house, the watchtower and the big gates (main
        gate, inner gate, Gate A, garage) are built;
      - the levels above (D.upper): roofs, the upper course of the outer
        wall, the watchtower and its stairs, barbed wire;
      - the lift shaft on every level between the surface and the site.
    Each surface square remembers it was done, so nothing is built twice.

    The site is placed by an admin ("Build the SCP site here": the click is
    where the access road starts) or by the FacilityX / FacilityY sandbox options.
]]

require "SCP_System"
require "SCP_Doors"
require "SCP_Facility_Layout"
require "SCP_Spawner"

local F = SCP.Facility
local D = F.Data
local TL = D.tiles
local SET = TL.sheet

local function tile(n) return SET .. n end

-- Machines: tileset scp_facility_01 (hand-drawn, see art/scp_facility_01_tilesheet.png).
F.Sprites = {
    terminal = "scp_facility_01_4",                 -- SCP-079: tape reels and CRT
    scp914 = "scp_facility_01_1",                   -- SCP-914: gears and dial (center)
    scp914In = "scp_facility_01_0",                 -- SCP-914: intake booth (west)
    scp914Out = "scp_facility_01_2",                -- SCP-914: output booth (east)
    scp294 = "scp_facility_01_3",                   -- SCP-294: drink machine
    warhead = "scp_facility_01_6",                  -- Alpha Warhead control panel
    femur = "scp_facility_01_6",                    -- Femur Breaker console (same panel tile for now)
    generator = "scp_facility_01_5",                -- generator control panel
    teslaW = "scp_facility_01_7",                   -- Tesla gate on the west edge of a square
    teslaN = "scp_facility_01_8",                   -- Tesla gate on the north edge of a square
}

-- Vanilla stand-ins used when the mod's tile pack is not loaded.
-- Furniture, signs and fittings have none: they are simply left out.
F.Fallback = {
    scp_facility_01_0 = "location_shop_accessories_01_17",
    scp_facility_01_1 = "location_shop_accessories_01_17",
    scp_facility_01_2 = "location_shop_accessories_01_17",
    scp_facility_01_3 = "location_shop_zippee_01_56",
    scp_facility_01_4 = "appliances_com_01_52",
    scp_facility_01_5 = "security_01_0",
    scp_facility_01_6 = "security_01_0",
}
do
    local wallSets = {
        a = "walls_interior_house_02", b = "walls_interior_bathroom_01", c = "walls_commercial_03",
        d = "walls_commercial_03", e = "walls_exterior_house_01", f = "walls_exterior_house_01",
    }
    for key, name in pairs(wallSets) do
        local i0 = TL.walls[key]
        F.Fallback[tile(i0)] = name .. "_0"
        F.Fallback[tile(i0 + 1)] = name .. "_1"
        F.Fallback[tile(i0 + 2)] = name .. "_2"
        if key ~= "f" then
            F.Fallback[tile(i0 + 3)] = name .. "_10"
            F.Fallback[tile(i0 + 4)] = name .. "_11"
        end
        F.Fallback[tile(TL.pillars[key])] = name .. "_3"
    end
    for key, name in pairs({ x = "walls_commercial_03", y = "walls_commercial_03" }) do
        local i0 = TL.walls[key]
        F.Fallback[tile(i0)] = name .. "_0"
        F.Fallback[tile(i0 + 1)] = name .. "_1"
        F.Fallback[tile(i0 + 2)] = name .. "_2"
        if key == "x" then
            F.Fallback[tile(i0 + 3)] = name .. "_10"
            F.Fallback[tile(i0 + 4)] = name .. "_11"
        end
    end
    F.Fallback[tile(TL.pillars.x)] = "walls_commercial_03_3"
    -- wooden stairs of the game (north-facing set: bottom, middle, top)
    for piece = 0, 2 do F.Fallback[tile(TL.stairs.N + piece)] = "carpentry_02_" .. (96 + piece) end
    for piece = 0, 2 do F.Fallback[tile(TL.stairs.W + piece)] = "carpentry_02_" .. (88 + piece) end
    local floors = {
        p = "floors_exterior_street_01_16", r = "floors_exterior_street_01_0", s = "floors_exterior_street_01_0",
        o = "floors_interior_tilesandwood_01_29",
        t = "floors_interior_tilesandwood_01_28", c = "floors_interior_tilesandwood_01_16",
        m = "floors_interior_tilesandwood_01_29", g = "floors_interior_tilesandwood_01_24",
        h = "floors_interior_tilesandwood_01_3", e = "floors_interior_tilesandwood_01_3",
        a = "floors_exterior_street_01_0", k = "floors_interior_tilesandwood_01_16",
        roof = "floors_interior_tilesandwood_01_29",
    }
    for key, name in pairs(floors) do F.Fallback[tile(TL.floors[key])] = name end
    for _, i0 in pairs(TL.doors) do
        F.Fallback[tile(i0)] = "fixtures_doors_01_68"
        F.Fallback[tile(i0 + 1)] = "fixtures_doors_01_69"
    end
end

local origin = nil       -- cached F.origin()
local spawnQueue = {}

local function refreshOrigin() origin = F.origin() end

------------------------------------------------------------------------
-- What the plan holds at each tile (built once)
------------------------------------------------------------------------

local index = nil

local function key(lx, ly) return lx .. "," .. ly end

local function buildIndex()
    index = {}
    local all = { underground = D.underground, surface = D.surface }
    for i, level in ipairs(D.upper or {}) do all["upper" .. i] = level end
    for name, level in pairs(all) do
        local ix = { doors = {}, objects = {}, tesla = {}, lifts = {}, centers = {}, roof = {} }
        local function push(t, k, v)
            t[k] = t[k] or {}
            table.insert(t[k], v)
        end
        for _, d in ipairs(level.doors) do push(ix.doors, key(d.x, d.y), d) end
        for _, o in ipairs(level.objects) do push(ix.objects, key(o.x, o.y), o) end
        for _, t in ipairs(level.tesla) do ix.tesla[key(t.x, t.y)] = t end
        for _, l in ipairs(level.lifts) do ix.lifts[key(l.x, l.y)] = l end
        for _, r in ipairs(level.rooms) do
            ix.centers[key(r.cx, r.cy)] = r
            if r.roof then
                for rx = r.x0, r.x1 do
                    for ry = r.y0, r.y1 do ix.roof[key(rx, ry)] = true end
                end
            end
        end
        index[name] = ix
    end
end

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
    SCP.log("missing tile sprite:", tostring(name))
end

-- The mod tile if its pack is loaded, else its vanilla stand-in.
local function resolve(sprite)
    if spriteOk(sprite) then return sprite end
    return F.Fallback[sprite] or sprite
end

-- replace = true: the existing floor (grass, road...) is changed to ours.
local function addFloor(sq, sprite, replace)
    if sq:getFloor() and not replace then return end
    sprite = resolve(sprite)
    if not spriteOk(sprite) then warnSprite(sprite) return end
    if sq.addFloor then
        if pcall(sq.addFloor, sq, sprite) then return end
    end
    if sq:getFloor() then return end
    local ok, obj = pcall(IsoObject.new, getCell(), sq, sprite)
    if ok and obj then sq:AddTileObject(obj) end
end

-- setup(obj), if given, runs before the object is added to the square.
-- optional = true: decoration, silently left out when its tile is missing.
local function addObject(sq, sprite, setup, optional)
    sprite = resolve(sprite)
    if not spriteOk(sprite) then
        if not optional then warnSprite(sprite) end
        return nil
    end
    local ok, obj = pcall(IsoObject.new, getCell(), sq, sprite)
    if ok and obj then
        if setup then setup(obj) end
        sq:AddTileObject(obj)
        return obj
    end
    return nil
end

-- Removes what stands on a surface square (trees, bushes, fences...), keeps the ground.
local function clearSquare(sq)
    local floor = sq:getFloor()
    local objs = sq:getObjects()
    for i = objs:size() - 1, 0, -1 do
        local o = objs:get(i)
        if o ~= floor then
            if isServer() then
                pcall(sq.transmitRemoveItemFromSquare, sq, o)
            else
                pcall(sq.RemoveTileObject, sq, o)
            end
        end
    end
end

local function addDoor(sq, north, d)
    local base = d.gate and TL.doors.gate or (d.heavy and TL.doors.heavy or TL.doors.standard)
    local sprite = resolve(tile(base + (north and 1 or 0)))
    if not spriteOk(sprite) then warnSprite(sprite) return end
    local ok, door = pcall(IsoDoor.new, getCell(), sq, sprite, north)
    if not ok or not door then return end
    sq:AddSpecialObject(door)
    local world = SCP.world()
    if d.gate then
        door:getModData().SCP_Gate = d.gate
        world.gates = world.gates or {}
        world.gates[d.gate] = world.gates[d.gate] or {}
        table.insert(world.gates[d.gate], { x = sq:getX(), y = sq:getY(), z = sq:getZ() })
    end
    if d.level and d.level > 0 then
        door:getModData().SCP_KeyLevel = d.level
        SCP.Doors.setLocked(door, true)
        world.doors = world.doors or {}
        world.doors[SCP.Doors.key(sq)] = d.level
    end
end

-- One piece of a staircase (0 bottom, 1 middle, 2 top). The game knows a
-- staircase by its tile (stairs flags), so AddStairs is tried first and a
-- plain object with the same tile is the fallback.
local function addStairs(sq, dir, piece)
    local north = dir == "N"
    local sprite = resolve(tile(TL.stairs[dir] + piece))
    if not spriteOk(sprite) then warnSprite(sprite) return end
    if sq.AddStairs then
        local ok = pcall(sq.AddStairs, sq, north, piece, sprite, sprite, nil)
        if ok then return end
    end
    addObject(sq, sprite)
end

------------------------------------------------------------------------
-- Things standing on a tile
------------------------------------------------------------------------

local function addContainer(obj, name)
    local ok, c = pcall(ItemContainer.new, name, obj:getSquare(), obj)
    if ok and c then
        pcall(c.setCapacity, c, 50)
        pcall(c.setExplored, c, true)
        pcall(obj.setContainer, obj, c)
    else
        SCP.log("SCP-914: could not create the booth container")
    end
end

local function placeObject(sq, o)
    local k = o.kind
    if k == "prop" then
        addObject(sq, tile(TL.props[o.prop] + (o.face == "w" and 1 or 0)), nil, true)
    elseif k == "sign" then
        local n = (o.north and TL.signN or TL.signW)[o.sign]
        if n then addObject(sq, tile(n), nil, true) end
    elseif k == "ext" then
        local i0 = TL.ext[o.ext]
        if i0 then addObject(sq, tile(i0 + (o.face == "w" and 1 or 0)), nil, true) end
    elseif k == "stairs" then
        addStairs(sq, o.dir, o.piece)
    elseif k == "pipes" or k == "vent" then
        addObject(sq, tile(TL.fittings[k] + (o.north and 1 or 0)), nil, true)
    elseif k == "terminal" then
        local obj = addObject(sq, F.Sprites.terminal)
        if obj then obj:getModData().SCP079_Terminal = true end
    elseif k == "scp914" then
        local obj = addObject(sq, F.Sprites.scp914)
        if obj then obj:getModData().SCP914_Machine = true end
    elseif k == "scp914In" or k == "scp914Out" then
        -- Intake (west) and output (east) booths: containers, like furniture.
        local kind = k == "scp914In" and "in" or "out"
        addObject(sq, F.Sprites[k], function(obj)
            obj:getModData().SCP914_Booth = kind
            addContainer(obj, "scp914_" .. kind)
        end)
    elseif k == "scp294" then
        local obj = addObject(sq, F.Sprites.scp294)
        if obj then obj:getModData().SCP294_Machine = true end
    elseif k == "warhead" then
        local obj = addObject(sq, F.Sprites.warhead)
        if obj then obj:getModData().SCP_Warhead = true end
    elseif k == "femur" then
        local obj = addObject(sq, F.Sprites.femur)
        if obj then obj:getModData().SCP106_Breaker = true end
    elseif k == "generator" then
        local obj = addObject(sq, F.Sprites.generator)
        if obj then obj:getModData().SCP079_Generator = o.n end
    end
end

-- Loot, staff and SCP of a room (placed once, when the room's centre tile is built).
local function roomContents(room, x, y, z)
    local loot = room.loot
    if loot then
        for i = 1, #loot, 2 do
            local itemType = loot[i]
            if not itemType:find("%.") then itemType = "Base." .. itemType end
            for _ = 1, loot[i + 1] do
                local lx = origin.x + ZombRand(room.x0, room.x1 + 1)
                local ly = origin.y + ZombRand(room.y0, room.y1 + 1)
                local sq = getCell():getOrCreateGridSquare(lx, ly, z)
                if sq then pcall(sq.AddWorldInventoryItem, sq, itemType, ZombRandFloat(0.1, 0.9), ZombRandFloat(0.1, 0.9), 0) end
            end
        end
    end
    -- Staff and SCPs are spawned a little later (not during chunk loading).
    if room.zombies then
        table.insert(spawnQueue, { outfit = room.zombies[1], count = room.zombies[2], x = x, y = y, z = z })
    end
    if room.scp then
        table.insert(spawnQueue, { scp = room.scp, count = room.count or 1, x = x, y = y, z = z })
    end
end

------------------------------------------------------------------------
-- One tile of one level
------------------------------------------------------------------------

local function wallSprite(ch, offset)
    local i0 = TL.walls[ch:lower()]
    if not i0 then return nil end
    if ch:lower() ~= ch then return tile(i0 + 3 + offset) end     -- capital: door frame
    return tile(i0 + offset)
end

local function buildTile(level, ix, lx, ly, x, y, z, surface)
    local fl = F.charAt(level, "floor", lx, ly)
    local west = F.charAt(level, "west", lx, ly)
    local north = F.charAt(level, "north", lx, ly)
    -- corner post where the north wall of the tile to the west meets the west wall of the tile to the north
    local post = nil
    if west == "." and north == "." then
        local n2, w2 = F.charAt(level, "north", lx - 1, ly), F.charAt(level, "west", lx, ly - 1)
        if n2 ~= "." and n2 ~= " " and w2 ~= "." and w2 ~= " " then post = TL.pillars[n2:lower()] end
    end
    local k = key(lx, ly)
    local doors = ix.doors[k]
    if fl == " " and west == "." and north == "." and not post and not doors and not ix.objects[k] then return end

    local sq = getCell():getOrCreateGridSquare(x, y, z)
    if not sq then return end

    if fl ~= " " then
        if surface then clearSquare(sq) end
        addFloor(sq, tile(TL.floors[fl] or TL.floors.c), surface)
    end

    if west ~= "." and north ~= "." and west == north and west:lower() == west and not TL.lowWalls[west] then
        addObject(sq, tile(TL.walls[west] + 2))
    else
        if west ~= "." then addObject(sq, wallSprite(west, 0)) end
        if north ~= "." then addObject(sq, wallSprite(north, 1)) end
    end
    if post then addObject(sq, tile(post)) end
    if doors then
        for _, d in ipairs(doors) do addDoor(sq, d.north, d) end
    end

    local t = ix.tesla[k]
    if t then addObject(sq, t.north and F.Sprites.teslaN or F.Sprites.teslaW, nil, true) end
    local objects = ix.objects[k]
    if objects then
        for _, o in ipairs(objects) do placeObject(sq, o) end
    end
    local lift = ix.lifts[k]
    if lift then
        local floor = sq:getFloor()
        if floor then floor:getModData().SCP_Elevator = { level = surface and "SURFACE" or "SITE", link = lift.link } end
    end
    local room = ix.centers[k]
    if room then roomContents(room, x, y, z) end

    pcall(sq.RecalcProperties, sq)
    pcall(sq.RecalcAllWithNeighbours, sq, true)
    -- New squares: make the lighting pass look at them again.
    local chunk = sq.getChunk and sq:getChunk()
    if chunk and chunk.checkLightingLater_AllPlayers_AllLevels then
        pcall(chunk.checkLightingLater_AllPlayers_AllLevels, chunk)
    end
end

------------------------------------------------------------------------
-- One surface column -> the site under it, the compound, the roof
------------------------------------------------------------------------

-- The lift platform (plan tiles) and its shaft walls on the levels in between.
local liftRect = nil
local function getLiftRect()
    if liftRect then return liftRect end
    local r = { x0 = 9999, y0 = 9999, x1 = -1, y1 = -1 }
    for _, l in ipairs(D.surface.lifts) do
        r.x0, r.y0 = math.min(r.x0, l.x), math.min(r.y0, l.y)
        r.x1, r.y1 = math.max(r.x1, l.x), math.max(r.y1, l.y)
    end
    liftRect = r
    return r
end
F.liftRect = getLiftRect

local function buildShaft(lx, ly, x, y, z)
    local r = getLiftRect()
    local inY, inX = ly >= r.y0 and ly <= r.y1, lx >= r.x0 and lx <= r.x1
    local westWall = inY and (lx == r.x0 or lx == r.x1 + 1)
    local northWall = inX and (ly == r.y0 or ly == r.y1 + 1)
    if not westWall and not northWall then return end
    local sq = getCell():getOrCreateGridSquare(x, y, z)
    if not sq then return end
    local i0 = TL.walls.e
    if westWall and northWall then
        addObject(sq, tile(i0 + 2))
    elseif westWall then
        addObject(sq, tile(i0))
    else
        addObject(sq, tile(i0 + 1))
    end
    pcall(sq.RecalcAllWithNeighbours, sq, true)
end

local function buildColumn(surfaceSq)
    if not index then buildIndex() end
    local o = origin
    local x, y = surfaceSq:getX(), surfaceSq:getY()
    local lx, ly = x - o.x, y - o.y
    buildTile(D.underground, index.underground, lx, ly, x, y, o.z, false)
    buildTile(D.surface, index.surface, lx, ly, x, y, 0, true)
    for i, level in ipairs(D.upper or {}) do
        buildTile(level, index["upper" .. i], lx, ly, x, y, level.z, false)
    end
    for z = o.z + 1, -1 do buildShaft(lx, ly, x, y, z) end
    if index.surface.roof[key(lx, ly)] then
        local sq = getCell():getOrCreateGridSquare(x, y, 1)
        if sq then
            addFloor(sq, tile(TL.floors.roof), false)
            pcall(sq.RecalcAllWithNeighbours, sq, true)
        end
    end
    surfaceSq:getModData().SCP_FacilityBuilt = F.VERSION
end

local function inFootprint(x, y)
    return origin and x >= origin.x and y >= origin.y and x < origin.x + D.width and y < origin.y + D.height
end

-- Nothing is built while a game is still loading: removing or replacing
-- objects then (the town's grass, trees...) runs the game's own handlers
-- before they exist, which floods the log with errors (seen when a new
-- character placed the site from OnNewGame). Squares that load before the
-- game is ready wait in `pending`.
local ready = false
local readyTicks = 0
local pending = {}
local buildAllLater = false

local function onLoadGridsquare(sq)
    if isClient() or not origin then return end
    if not ready then
        if sq:getZ() == 0 then pending[#pending + 1] = sq end
        return
    end
    if sq:getZ() ~= 0 then return end
    local x, y = sq:getX(), sq:getY()
    if not inFootprint(x, y) then return end
    if sq:getModData().SCP_FacilityBuilt == F.VERSION then return end
    buildColumn(sq)
end

SCP.on("LoadGridsquare", onLoadGridsquare)

-- Build what is already loaded (right after the site was placed).
function F.buildLoaded()
    if not origin then return end
    if not ready then
        buildAllLater = true
        return
    end
    for x = origin.x, origin.x + D.width - 1 do
        for y = origin.y, origin.y + D.height - 1 do
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
        local k = s.x .. "," .. s.y .. "," .. s.z
        if not world.facility.spawned[k] then
            world.facility.spawned[k] = true
            if s.scp then
                local list = SCP.Spawner.spawn(s.scp, s.x, s.y, s.z, s.count or 1)
                for _, z in ipairs(list) do
                    z:getModData().SCP_Contained = true
                    z:getModData().SCP_Home = { x = s.x, y = s.y, z = s.z }
                end
                table.insert(world.points, { type = s.scp, x = s.x, y = s.y, z = s.z, contained = true })
            else
                SCP.Spawner.spawn(s.outfit, s.x, s.y, s.z, s.count)
            end
        end
    end
    if isServer() then ModData.transmit("SCPFoundation") end
end

SCP.on("EveryOneMinute", processSpawns)

------------------------------------------------------------------------
-- Placement: args.x / args.y is where the access road starts
------------------------------------------------------------------------

SCP.ServerCommands.PlaceFacility = function(player, args)
    if not SCP.isAdmin(player) then return end
    local world = SCP.world()
    if world.facility and world.facility.x and world.facility.v == F.VERSION then
        SCP.sendToClient(player, "Notify", { key = "UI_SCP_FacilityExists" })
        return
    end
    if world.facility and world.facility.x then
        -- A site from an older version of the mod: forget its doors and cells (its tiles stay where they are).
        world.doors = {}
        local keep = {}
        for _, p in ipairs(world.points) do
            if not p.contained then keep[#keep + 1] = p end
        end
        world.points = keep
    end
    local o = F.originForGate(args.x, args.y)
    o.spawned = {}
    world.facility = o
    world.gates = {}
    refreshOrigin()
    if isServer() then ModData.transmit("SCPFoundation") end
    F.buildLoaded()
    SCP.sendToClient(player, "Notify", { key = "UI_SCP_FacilityPlaced" })
    SCP.log("SCP site placed, access road at", args.x, args.y, "underground level", o.z)
end

local started = false
local function onStarted()
    refreshOrigin()
    started = true
end

-- A couple of seconds after the game has started, build what waited.
SCP.on("OnTick", function()
    if ready or not started then return end
    readyTicks = readyTicks + 1
    if readyTicks < 120 then return end
    ready = true
    refreshOrigin()
    if not origin then pending = {} return end
    local list = pending
    pending = {}
    for _, sq in ipairs(list) do
        if sq:getModData().SCP_FacilityBuilt ~= F.VERSION and inFootprint(sq:getX(), sq:getY()) then
            buildColumn(sq)
        end
    end
    if buildAllLater then
        buildAllLater = false
        F.buildLoaded()
    end
end)

SCP.on("OnInitGlobalModData", function() refreshOrigin() end)
SCP.on("OnGameStart", onStarted)
SCP.on("EveryOneMinute", function() if not started then onStarted() end end)
if Events.OnServerStarted then SCP.on("OnServerStarted", onStarted) end
