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
SCP.Pocket.FloorSprite = "floors_burnt_01_0"
SCP.Pocket.ExitSprite = "floors_exterior_street_01_0"

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

Events.EveryHours.Add(cleanCorrosion)

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

Events.EveryOneMinute.Add(corrosionDamage)

------------------------------------------------------------------------
-- Pocket Dimension (built locally for the victim)
------------------------------------------------------------------------

local exitsDirs = { { 1, 0 }, { -1, 0 }, { 0, 1 }, { 0, -1 } }

local function placeTile(x, y, z, sprite)
    local sq = getCell():getOrCreateGridSquare(x, y, z)
    if not sq then return nil end
    if not sq:getFloor() then
        local ok, obj = pcall(IsoObject.new, getCell(), sq, sprite)
        if ok and obj then
            obj:getModData().SCP_Pocket = true
            sq:AddTileObject(obj)
        end
    end
    if sq.RecalcAllWithNeighbours then pcall(sq.RecalcAllWithNeighbours, sq, true) end
    return sq
end

local function buildPocket(cx, cy, cz)
    for dx = -POCKET_RADIUS, POCKET_RADIUS do
        for dy = -POCKET_RADIUS, POCKET_RADIUS do
            placeTile(cx + dx, cy + dy, cz, SCP.Pocket.FloorSprite)
        end
    end
    for _, d in ipairs(exitsDirs) do
        placeTile(cx + d[1] * POCKET_RADIUS, cy + d[2] * POCKET_RADIUS, cz, SCP.Pocket.ExitSprite)
    end
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
    player:playSound("SCP106_Laugh")
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
    if not p then return end
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

Events.OnPlayerUpdate.Add(onPlayerUpdate)

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

Events.EveryOneMinute.Add(pocketTick)

-- Died inside: forget the pocket state.
Events.OnPlayerDeath.Add(function(player)
    if player and player:getModData().SCP_Pocket then player:getModData().SCP_Pocket = nil end
end)

------------------------------------------------------------------------
-- Movement: straight line toward the nearest player, through walls.
------------------------------------------------------------------------

local function onZombieUpdate(zombie)
    if not SCP.isEntity(zombie, SCP.Types.SCP106) then return end
    SCP.freeze(zombie, true)
    local md = zombie:getModData()
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
    if not target:isLocalPlayer() and (isClient() or isServer()) then return end

    local step = SCP.opt("SCP106Speed") * getGameTime():getMultiplier()
    step = math.min(step, d)
    local nx, ny = zombie:getX() + dx / d * step, zombie:getY() + dy / d * step
    local nz = zombie:getZ()
    if d < 3 and math.floor(nz) ~= tz then nz = tz end -- sinks/rises through floors
    SCP.teleport(zombie, nx, ny, nz)
    zombie:faceThisObject(target)

    -- Corrosion trail
    local lx, ly = md.SCP106_LastX or nx, md.SCP106_LastY or ny
    if math.abs(nx - lx) + math.abs(ny - ly) >= CORRODE_EVERY_TILES then
        md.SCP106_LastX, md.SCP106_LastY = nx, ny
        SCP.sendToServer(target, "SCP106Corrode", { x = math.floor(nx), y = math.floor(ny), z = math.floor(nz) })
    elseif not md.SCP106_LastX then
        md.SCP106_LastX, md.SCP106_LastY = nx, ny
    end
end

Events.OnZombieUpdate.Add(onZombieUpdate)
