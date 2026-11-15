--[[
    SCP-106 "The Old Man".
    - Ignores walls and doors: its vanilla AI is switched off and it is moved
      straight toward the nearest player, through anything.
    - Leaves corrosion patches behind; stepping on one burns the feet
      (a hazmat suit protects).
    - Touching a player sends them to the Pocket Dimension.

    Pocket Dimension: a dark room built deep underground under the victim.
    The player bleeds while inside. Four exits sit on the edges; only one
    leads back to the surface, the others throw the player back to the
    centre and hurt them.
]]

require "SCP_System"

SCP.SCP106 = SCP.SCP106 or {}
SCP.Pocket = SCP.Pocket or {}

-- Placeholder tiles. Replace with custom tiles once they exist.
SCP.SCP106.CorrosionSprite = "floors_burnt_01_0"
-- Pocket dimension tiles (scp_facility_02, made from the pocket dimension rock
-- of SCP - Containment Breach, see tools/make_facility_tiles.py),
-- with vanilla fallbacks if the mod tileset failed to load.
SCP.Pocket.FloorSprites = { "scp_facility_02_35", "scp_facility_02_36" }
SCP.Pocket.ExitSprite = "scp_facility_02_37"
SCP.Pocket.WallW = "scp_facility_02_32"
SCP.Pocket.WallN = "scp_facility_02_33"
SCP.Pocket.WallNW = "scp_facility_02_34"
SCP.Pocket.Fallback = {
    scp_facility_02_35 = "floors_burnt_01_0", scp_facility_02_36 = "floors_burnt_01_0",
    scp_facility_02_37 = "floors_exterior_street_01_0",
    scp_facility_02_32 = "walls_exterior_house_01_0", scp_facility_02_33 = "walls_exterior_house_01_1",
    scp_facility_02_34 = "walls_exterior_house_01_2",
}
-- Dim, sickly green "daylight": the pocket is never pitch black.
SCP.Pocket.Light = { r = 0.42, g = 0.46, b = 0.3, radius = 14 }
SCP.Pocket.ExitLight = { r = 0.5, g = 0.58, b = 0.42, radius = 5 }

local CHASE_DIST = 40
local TOUCH_DIST = 0.9
local CORRODE_EVERY_TILES = 1.5
local CORROSION_HOURS = 12
local POCKET_RADIUS = 7
local LAUGH_EVERY_MS = 15000

------------------------------------------------------------------------
-- Corrosion (server owns the objects)
------------------------------------------------------------------------

local function hasCorrosion(sq)
    local objs = sq:getObjects()
    for i = 0, objs:size() - 1 do
        if objs:get(i):getModData().SCP_Corrosion then return objs:get(i) end
    end
    return nil
end

SCP.ServerCommands.SCP106Corrode = function(player, args)
    local sq = getCell():getGridSquare(args.x, args.y, args.z)
    if not sq or hasCorrosion(sq) then return end
    local ok, obj = pcall(IsoObject.new, getCell(), sq, SCP.SCP106.CorrosionSprite)
    if not ok or not obj then return end
    obj:getModData().SCP_Corrosion = true
    sq:AddTileObject(obj)
    if isServer() then
        obj:transmitCompleteItemToClients()
        obj:transmitModData()
    end
    local world = SCP.world()
    world.corrosion = world.corrosion or {}
    table.insert(world.corrosion, { x = args.x, y = args.y, z = args.z, t = getGameTime():getWorldAgeHours() })
end

local function cleanCorrosion()
    if isClient() then return end
    local world = SCP.world()
    if not world.corrosion then return end
    local now = getGameTime():getWorldAgeHours()
    local keep = {}
    for _, c in ipairs(world.corrosion) do
        if now - c.t < CORROSION_HOURS then
            keep[#keep + 1] = c
        else
            local sq = getCell():getGridSquare(c.x, c.y, c.z)
            local obj = sq and hasCorrosion(sq)
            if obj then
                sq:transmitRemoveItemFromSquare(obj)
            elseif not sq then
                keep[#keep + 1] = c -- not loaded right now, try later
            end
        end
    end
    world.corrosion = keep
end

SCP.on("EveryHours", cleanCorrosion)

local function corrosionDamage()
    for _, player in ipairs(SCP.localPlayers()) do
        local sq = player:getSquare()
        if sq and hasCorrosion(sq) and not SCP.hasHazmat(player) then
            local bd = player:getBodyDamage()
            local foot = ZombRand(2) == 0 and BodyPartType.Foot_L or BodyPartType.Foot_R
            local part = bd:getBodyPart(foot)
            if part then pcall(part.AddDamage, part, 4) end
            if part and ZombRand(4) == 0 then pcall(part.setBurned, part) end
            if not SCP.hasAirProtection(player) then
                SCP.setStat(player, "SICKNESS", math.min(1, SCP.getStat(player, "SICKNESS") + 0.02))
            end
            player:playSound("SCP106_Corrosion")
            SCP.say(player, "UI_SCP_106_Corrosion", 160, 120, 60)
        end
    end
end

SCP.on("EveryOneMinute", corrosionDamage)

------------------------------------------------------------------------
-- Pocket Dimension (built locally for the victim)
------------------------------------------------------------------------

local exitsDirs = { { 1, 0 }, { -1, 0 }, { 0, 1 }, { 0, -1 } }

local function pocketSprite(sprite)
    if getSprite and getSprite(sprite) then return sprite end
    return SCP.Pocket.Fallback[sprite] or sprite
end

local function placeTile(x, y, z, sprite, replaceFloor)
    local sq = getCell():getOrCreateGridSquare(x, y, z)
    if not sq then return nil end
    local floor = sq:getFloor()
    if floor and replaceFloor and floor:getModData().SCP_Pocket then
        pcall(sq.transmitRemoveItemFromSquare, sq, floor)
        pcall(sq.RemoveTileObject, sq, floor)
        floor = nil
    end
    if not floor then
        local ok, obj = pcall(IsoObject.new, getCell(), sq, pocketSprite(sprite))
        if ok and obj then
            obj:getModData().SCP_Pocket = true
            sq:AddTileObject(obj)
        end
    end
    return sq
end

local function hasPocketObject(sq, sprite)
    local objs = sq:getObjects()
    for i = 0, objs:size() - 1 do
        local o = objs:get(i)
        if o:getModData().SCP_Pocket and o:getSprite() and o:getSprite():getName() == sprite then return true end
    end
    return false
end

local function placeWall(x, y, z, sprite)
    local sq = getCell():getOrCreateGridSquare(x, y, z)
    if not sq then return end
    sprite = pocketSprite(sprite)
    if hasPocketObject(sq, sprite) then return end
    local ok, obj = pcall(IsoObject.new, getCell(), sq, sprite)
    if ok and obj then
        obj:getModData().SCP_Pocket = true
        sq:AddTileObject(obj)
    end
end

local function buildPocket(cx, cy, cz)
    local R = POCKET_RADIUS
    for dx = -R, R do
        for dy = -R, R do
            local fl = SCP.Pocket.FloorSprites[ZombRand(#SCP.Pocket.FloorSprites) + 1]
            placeTile(cx + dx, cy + dy, cz, fl)
        end
    end
    -- The four exits all look the same: only one of them is the way out.
    for _, d in ipairs(exitsDirs) do
        placeTile(cx + d[1] * R, cy + d[2] * R, cz, SCP.Pocket.ExitSprite, true)
    end
    -- Rotten stone walls all around (west/north faces live on the square itself,
    -- east/south faces are the west/north walls of the next square out).
    for d = -R, R do
        placeWall(cx - R, cy + d, cz, SCP.Pocket.WallW)
        placeWall(cx + R + 1, cy + d, cz, SCP.Pocket.WallW)
        placeWall(cx + d, cy - R, cz, SCP.Pocket.WallN)
        placeWall(cx + d, cy + R + 1, cz, SCP.Pocket.WallN)
    end
    placeWall(cx - R, cy - R, cz, SCP.Pocket.WallNW)
    for dx = -R - 1, R + 1 do
        for dy = -R - 1, R + 1 do
            local sq = getCell():getGridSquare(cx + dx, cy + dy, cz)
            if sq and sq.RecalcAllWithNeighbours then pcall(sq.RecalcAllWithNeighbours, sq, true) end
        end
    end
end

-- Client-side ambient light for the pocket (one per local player).
local pocketLights = {}

local function relightAround(x, y, z)
    local sq = getCell():getGridSquare(x, y, z)
    local chunk = sq and sq:getChunk()
    if chunk and chunk.checkLightingLater_AllPlayers_AllLevels then
        pcall(chunk.checkLightingLater_AllPlayers_AllLevels, chunk)
    end
end

local function dropPocketLights(cur)
    for _, light in ipairs(cur.lights) do pcall(getCell().removeLamppost, getCell(), light) end
end

-- A wide dim light over the whole pocket, plus a paler one over each exit,
-- so the place reads as lit from above rather than by a single lamp.
local function ensurePocketLight(player, p)
    if isServer() then return end
    local key = player:getPlayerNum()
    local cur = pocketLights[key]
    if cur and cur.cx == p.cx and cur.cy == p.cy and cur.cz == p.cz then return end
    if cur then dropPocketLights(cur) end
    local L, E = SCP.Pocket.Light, SCP.Pocket.ExitLight
    local spots = { { 0, 0, L } }
    for _, d in ipairs(exitsDirs) do
        spots[#spots + 1] = { d[1] * (POCKET_RADIUS - 1), d[2] * (POCKET_RADIUS - 1), E }
    end
    local made = {}
    for _, s in ipairs(spots) do
        local c = s[3]
        local ok, light = pcall(IsoLightSource.new, p.cx + s[1], p.cy + s[2], p.cz, c.r, c.g, c.b, c.radius)
        if ok and light then
            getCell():addLamppost(light)
            made[#made + 1] = light
        end
    end
    if #made > 0 then
        pocketLights[key] = { lights = made, cx = p.cx, cy = p.cy, cz = p.cz }
        relightAround(p.cx, p.cy, p.cz)
    end
end

local function clearPocketLight(player)
    local key = player:getPlayerNum()
    local cur = pocketLights[key]
    if not cur then return end
    dropPocketLights(cur)
    pocketLights[key] = nil
    relightAround(cur.cx, cur.cy, cur.cz)
end

function SCP.Pocket.isInside(player)
    return player:getModData().SCP_Pocket ~= nil
end

function SCP.Pocket.send(player)
    if SCP.Pocket.isInside(player) then return end
    local x, y, z = math.floor(player:getX()), math.floor(player:getY()), math.floor(player:getZ())
    local depth = SCP.opt("PocketDimensionDepth")
    local md = player:getModData()
    md.SCP_Pocket = {
        rx = x, ry = y, rz = z,
        cx = x, cy = y, cz = depth,
        exit = ZombRand(#exitsDirs) + 1,
        since = getGameTime():getWorldAgeHours(),
    }
    buildPocket(x, y, depth)
    SCP.teleport(player, x + 0.5, y + 0.5, depth)
    player:playSound("SCP106_PocketEnter")
    SCP.say(player, "UI_SCP_106_Pocket", 160, 120, 60)
end

function SCP.Pocket.leave(player)
    local p = player:getModData().SCP_Pocket
    if not p then return end
    player:getModData().SCP_Pocket = nil
    -- Come out somewhere near where the player was taken.
    for _ = 1, 20 do
        local x = p.rx + ZombRand(-15, 16)
        local y = p.ry + ZombRand(-15, 16)
        local sq = getCell():getGridSquare(x, y, p.rz)
        if sq and sq:isFree(false) then
            SCP.teleport(player, x + 0.5, y + 0.5, p.rz)
            SCP.say(player, "UI_SCP_106_Escaped", 120, 255, 120)
            return
        end
    end
    SCP.teleport(player, p.rx + 0.5, p.ry + 0.5, p.rz)
    SCP.say(player, "UI_SCP_106_Escaped", 120, 255, 120)
end

local function onPlayerUpdate(player)
    if not player:isLocalPlayer() then return end
    local p = player:getModData().SCP_Pocket
    if not p then
        if pocketLights[player:getPlayerNum()] then clearPocketLight(player) end
        return
    end
    ensurePocketLight(player, p)
    local x, y = player:getX(), player:getY()

    -- Fell out or got moved elsewhere: put back in the centre.
    if math.floor(player:getZ()) ~= p.cz then
        SCP.teleport(player, p.cx + 0.5, p.cy + 0.5, p.cz)
        return
    end

    -- Exits
    for i, d in ipairs(exitsDirs) do
        local ex, ey = p.cx + d[1] * POCKET_RADIUS, p.cy + d[2] * POCKET_RADIUS
        if math.floor(x) == ex and math.floor(y) == ey then
            if i == p.exit then
                SCP.Pocket.leave(player)
            else
                SCP.damageHealth(player, 10)
                player:playSound("SCP106_Laugh")
                SCP.say(player, "UI_SCP_106_WrongExit", 255, 80, 80)
                p.exit = ZombRand(#exitsDirs) + 1
                SCP.teleport(player, p.cx + 0.5, p.cy + 0.5, p.cz)
            end
            return
        end
    end

    -- Invisible walls
    local dx, dy = x - (p.cx + 0.5), y - (p.cy + 0.5)
    local lim = POCKET_RADIUS + 0.4
    if math.abs(dx) > lim or math.abs(dy) > lim then
        SCP.teleport(player, p.cx + 0.5 + math.max(-lim, math.min(lim, dx)) * 0.95,
            p.cy + 0.5 + math.max(-lim, math.min(lim, dy)) * 0.95, p.cz)
    end
end

SCP.on("OnPlayerUpdate", onPlayerUpdate)

-- Bleeding and dread while trapped.
local function pocketTick()
    for _, player in ipairs(SCP.localPlayers()) do
        if SCP.Pocket.isInside(player) then
            SCP.damageHealth(player, 1.5)
            SCP.setStat(player, "PANIC", math.min(100, SCP.getStat(player, "PANIC") + 5))
            if ZombRand(5) == 0 then
                local parts = player:getBodyDamage():getBodyParts()
                local part = parts:get(ZombRand(parts:size()))
                pcall(part.setBleeding, part, true)
                pcall(part.setBleedingTime, part, 5)
            end
        end
    end
end

SCP.on("EveryOneMinute", pocketTick)

-- Died inside: forget the pocket state.
SCP.on("OnPlayerDeath", function(player)
    if player and player:getModData().SCP_Pocket then player:getModData().SCP_Pocket = nil end
end)

------------------------------------------------------------------------
-- Re-containment (Femur Breaker, see server/SCP_106_Containment.lua)
--   1. A body is sacrificed in the Femur Breaker: its screams lure every
--      active SCP-106 to the breaker for 30 in-game minutes.
--   2. Once 106 reaches the breaker it stays there, feeding.
--   3. "Magnetic recall" from the console sends it back to its cell, where
--      it stays dormant even during a breach, until the next breach starts.
------------------------------------------------------------------------

local LURE_SPEED_MULT = 3
local FEED_DIST = 1.5

function SCP.SCP106.state()
    local md = ModData.get("SCPFoundation")
    return md and md.scp106 or nil
end

-- Re-contained since the current breach started: stays asleep in its cell.
local function recontainedThisBreach(zombie)
    local md = zombie:getModData()
    if not md.SCP_Contained then return false end
    local st = SCP.SCP106.state()
    local rc = st and st.recontainedAt
    if not rc then return false end
    local w = ModData.get("SCPFoundation")
    local started = w and w.breach and w.breach.startedAt or -1
    return rc > started
end

local function isAsleep(zombie)
    if recontainedThisBreach(zombie) then
        local w = ModData.get("SCPFoundation")
        local until079 = w and w.scp079 and w.scp079.blackoutUntil
        if until079 and getGameTime():getWorldAgeHours() < until079 then return false end
        return SCP.nearestPlayer(zombie, 5) == nil
    end
    return SCP.isDormant(zombie, 5)
end

local function homeOf(zombie)
    local home = zombie:getModData().SCP_Home
    if home then return home end
    local best, bestD = nil, 1e9
    for _, p in ipairs(SCP.world().points) do
        if p.type == SCP.Types.SCP106 then
            local d = math.abs(p.x - zombie:getX()) + math.abs(p.y - zombie:getY())
            if d < bestD then best, bestD = p, d end
        end
    end
    return best
end

-- Called on every machine when the server confirms the magnetic recall.
local function applyRecall(zombie, st)
    local md = zombie:getModData()
    if not st.recalledLure or md.SCP106_Feeding ~= st.recalledLure then return false end
    md.SCP106_Feeding = nil
    md.SCP106_Lured = nil
    md.SCP_Contained = true
    local home = homeOf(zombie)
    if home then SCP.teleport(zombie, home.x + 0.5, home.y + 0.5, home.z) end
    return true
end

-- True when the machine running this code should move `zombie`.
local function ownsMovement(zombie, target)
    if not (isClient() or isServer()) then return true end
    return target ~= nil and target:isLocalPlayer()
end

local function moveToward(zombie, tx, ty, tz, speedMult, owner)
    local dx, dy = tx - zombie:getX(), ty - zombie:getY()
    local d = math.sqrt(dx * dx + dy * dy)
    if d < 0.05 then return d end
    local step = SCP.opt("SCP106Speed") * (speedMult or 1) * getGameTime():getMultiplier()
    step = math.min(step, d)
    local nx, ny = zombie:getX() + dx / d * step, zombie:getY() + dy / d * step
    local nz = zombie:getZ()
    if d < 3 and math.floor(nz) ~= tz then nz = tz end -- sinks/rises through floors
    SCP.teleport(zombie, nx, ny, nz)
    -- Corrosion trail
    local md = zombie:getModData()
    local lx, ly = md.SCP106_LastX or nx, md.SCP106_LastY or ny
    if math.abs(nx - lx) + math.abs(ny - ly) >= CORRODE_EVERY_TILES then
        md.SCP106_LastX, md.SCP106_LastY = nx, ny
        if owner then
            SCP.sendToServer(owner, "SCP106Corrode", { x = math.floor(nx), y = math.floor(ny), z = math.floor(nz) })
        end
    elseif not md.SCP106_LastX then
        md.SCP106_LastX, md.SCP106_LastY = nx, ny
    end
    return d
end

-- Lured by the Femur Breaker: walk to it through everything, then feed.
local function updateLured(zombie, st)
    local md = zombie:getModData()
    local lure = st.lure
    md.SCP106_Lured = lure.id
    local owner = SCP.nearestPlayer(zombie, 9999, SCP.allPlayers())
        or SCP.localPlayers()[1]
    if md.SCP106_Feeding == lure.id then
        return -- feeding: stays put until the recall or the end of the lure
    end
    local dx, dy = lure.x + 0.5 - zombie:getX(), lure.y + 0.5 - zombie:getY()
    local d = math.sqrt(dx * dx + dy * dy)
    if d < FEED_DIST and math.floor(zombie:getZ()) == lure.z then
        md.SCP106_Feeding = lure.id
        if owner then SCP.sendToServer(owner, "SCP106Feeding", { id = lure.id }) end
        return
    end
    if not ownsMovement(zombie, owner) then return end
    moveToward(zombie, lure.x + 0.5, lure.y + 0.5, lure.z, LURE_SPEED_MULT, owner)
end

------------------------------------------------------------------------
-- Movement: straight line toward the nearest player, through walls.
------------------------------------------------------------------------

local function onZombieUpdate(zombie)
    if not SCP.isEntity(zombie, SCP.Types.SCP106) then return end
    SCP.freeze(zombie, true)
    local md = zombie:getModData()
    local st = SCP.SCP106.state()

    if st and st.recontainedAt and (md.SCP106_RecallSeen or -1) < st.recontainedAt then
        md.SCP106_RecallSeen = st.recontainedAt
        if applyRecall(zombie, st) then return end
    end
    if st and st.lure and not isAsleep(zombie) then
        updateLured(zombie, st)
        return
    end
    md.SCP106_Feeding = nil
    if isAsleep(zombie) then return end

    local t = getTimestampMs()
    -- Target: nearest player, any floor.
    local target, best = nil, CHASE_DIST
    for _, p in ipairs(SCP.allPlayers()) do
        if not SCP.Pocket.isInside(p) then
            local d = SCP.dist(p, zombie)
            if d < best then target, best = p, d end
        end
    end
    if not target then return end

    if not md.SCP106_NextLaugh or t > md.SCP106_NextLaugh then
        md.SCP106_NextLaugh = t + LAUGH_EVERY_MS
        zombie:playSound("SCP106_Laugh")
    end

    local dx, dy = target:getX() - zombie:getX(), target:getY() - zombie:getY()
    local d = math.sqrt(dx * dx + dy * dy)
    local tz = math.floor(target:getZ())

    -- Touch
    if d < TOUCH_DIST and math.floor(zombie:getZ()) == tz then
        if target:isLocalPlayer() and (not md.SCP106_NextTouch or t > md.SCP106_NextTouch) then
            md.SCP106_NextTouch = t + 3000
            SCP.Pocket.send(target)
        end
        return
    end

    -- Only the machine that owns the target moves 106 (keeps MP in step).
    if not ownsMovement(zombie, target) then return end
    moveToward(zombie, target:getX(), target:getY(), tz, 1, target)
    zombie:faceThisObject(target)
end

SCP.on("OnZombieUpdate", onZombieUpdate)
