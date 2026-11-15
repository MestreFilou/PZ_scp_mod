--[[
    The Gate A lift, between the main building on the surface and the
    Entrance Zone. Step into the cabin (sliding doors), right click the
    call panel on its wall (or the platform) -> pick the floor. The doors
    close, the cabin moves, the doors of the other floor open.

    Ride (sandbox option LiftRide, on by default): the cabin really goes down
    (or up) its shaft. The player stays on the platform while their height
    changes a little every frame, like on the game's stairs, so the walls of
    the shaft scroll past and the other level comes into view. The floor of
    the upper platform is lifted out for the ride (it would hide the player)
    and put back on arrival.

    Nothing here could be tried in game yet. If a ride ever goes wrong (the
    player falls, or ends up in the wrong place), switch LiftRide off: the
    lift then goes back to a quick fade and teleport.
]]

require "SCP_System"
require "SCP_Doors"
require "SCP_Facility_Layout"

local F = SCP.Facility
local D = F.Data

local LEVEL_TEXT = { SURFACE = "UI_SCP_Zone_Surface", EZ = "UI_SCP_Zone_EZ", HCZ = "UI_SCP_Zone_HCZ", LCZ = "UI_SCP_Zone_LCZ" }
local SPEED = 0.45          -- levels per second
local MAX_TIME = 12         -- seconds; a deep site rides faster
local START_DELAY = 0.8     -- seconds before the cabin moves (doors closing)

local ride = nil

local function findElevatorObject(worldobjects)
    for _, o in ipairs(worldobjects) do
        local sq = o.getSquare and o:getSquare()
        if sq then
            local objs = sq:getObjects()
            for i = 0, objs:size() - 1 do
                local md = objs:get(i):getModData()
                if md.SCP_Elevator then return objs:get(i), md.SCP_Elevator end
            end
        end
    end
    return nil
end

-- Lift platform in plan tiles: x0, y0, x1, y1.
local function platform()
    local r = { x0 = 9999, y0 = 9999, x1 = -1, y1 = -1 }
    for _, l in ipairs(D.surface.lifts) do
        r.x0, r.y0 = math.min(r.x0, l.x), math.min(r.y0, l.y)
        r.x1, r.y1 = math.max(r.x1, l.x), math.max(r.y1, l.y)
    end
    return r
end

local function stopFalling(player)
    if player.setFallTime then pcall(player.setFallTime, player, 0) end
    if player.setbFalling then pcall(player.setbFalling, player, false) end
    if player.setFalling then pcall(player.setFalling, player, false) end
    if player.setLastFallSpeed then pcall(player.setLastFallSpeed, player, 0) end
end

local function freeze(player, on)
    if player.setBlockMovement then pcall(player.setBlockMovement, player, on) end
    if player.setIgnoreMovement then pcall(player.setIgnoreMovement, player, on) end
end

-- Takes the floor of the top platform out (kept to put it back).
local function liftTopFloor(o, r)
    local removed = {}
    for x = r.x0, r.x1 do
        for y = r.y0, r.y1 do
            local sq = getCell():getGridSquare(o.x + x, o.y + y, 0)
            local floor = sq and sq:getFloor()
            if floor then
                local sprite = floor:getSprite() and floor:getSprite():getName()
                local md = floor:getModData().SCP_Elevator
                if sprite and pcall(sq.RemoveTileObject, sq, floor) then
                    removed[#removed + 1] = { sq = sq, sprite = sprite, md = md }
                    pcall(sq.RecalcAllWithNeighbours, sq, true)
                end
            end
        end
    end
    return removed
end

local function restoreFloors(removed)
    for _, f in ipairs(removed or {}) do
        local sq = f.sq
        if not sq:getFloor() then
            local ok, floor = pcall(sq.addFloor, sq, f.sprite)
            if not ok or not floor then
                local ok2, obj = pcall(IsoObject.new, getCell(), sq, f.sprite)
                if ok2 and obj then sq:AddTileObject(obj); floor = obj end
            end
            if floor and f.md then floor:getModData().SCP_Elevator = f.md end
        end
        pcall(sq.RecalcProperties, sq)
        pcall(sq.RecalcAllWithNeighbours, sq, true)
    end
end

-- Sliding doors of the lift on one floor (gate ids from the site plan).
local DOOR_GATE = { SURFACE = "LIFT_SURFACE", SITE = "LIFT_EZ" }

local function setLiftDoors(gateId, open)
    local md = ModData.get("SCPFoundation")
    local list = md and md.gates and md.gates[gateId]
    if not list then return end
    for _, p in ipairs(list) do
        local d = SCP.Doors.find(p.x, p.y, p.z)
        if d then SCP.Doors.setOpen(d, open, nil) end
    end
end

local function teleportTravel(player, dest)
    player:playSound("SCP_KeycardAccept")
    getCell():getOrCreateGridSquare(dest.x, dest.y, dest.z)
    SCP.teleport(player, dest.x + 0.5, dest.y + 0.5, dest.z)
    SCP.say(player, LEVEL_TEXT[dest.label] or dest.label, 200, 220, 255)
end

local function finishRide()
    local r = ride
    ride = nil
    if not r then return end
    SCP.teleport(r.player, r.x, r.y, r.z1)
    stopFalling(r.player)
    restoreFloors(r.removed)
    freeze(r.player, false)
    r.player:playSound("SCP_LiftBeep")
    setLiftDoors(r.toGate, true)
    SCP.say(r.player, LEVEL_TEXT[r.dest.label] or r.dest.label, 200, 220, 255)
end

local function startRide(player, dest)
    local o = F.origin()
    if not o then return end
    local r = platform()
    -- stand in the middle of the platform (the corner the four tiles share)
    local x, y = o.x + (r.x0 + r.x1 + 1) / 2, o.y + (r.y0 + r.y1 + 1) / 2
    local z0 = math.floor(player:getZ() + 0.5)
    -- make sure every square of the shaft exists, so the player is drawn on each level
    for z = math.min(z0, dest.z), math.max(z0, dest.z) do
        for px = r.x0, r.x1 do
            for py = r.y0, r.y1 do getCell():getOrCreateGridSquare(o.x + px, o.y + py, z) end
        end
    end
    local dist = math.abs(dest.z - z0)
    ride = {
        player = player, dest = dest, x = x, y = y, z0 = z0, z1 = dest.z, z = z0,
        speed = math.max(SPEED, dist / MAX_TIME), wait = START_DELAY, removed = nil,
        fromGate = DOOR_GATE[dest.label == "SURFACE" and "SITE" or "SURFACE"],
        toGate = DOOR_GATE[dest.label == "SURFACE" and "SURFACE" or "SITE"],
    }
    freeze(player, true)
    SCP.teleport(player, x, y, z0)
    setLiftDoors(ride.fromGate, false)
    player:playSound("SCP_LiftBeep")
end

local function updateRide()
    local r = ride
    if not r then return end
    local p = r.player
    if not p or p:isDead() then
        restoreFloors(r.removed)
        ride = nil
        return
    end
    local dt = 1 / 30
    local gt = getGameTime()
    if gt and gt.getRealworldSecondsSinceLastUpdate then
        local ok, v = pcall(gt.getRealworldSecondsSinceLastUpdate, gt)
        if ok and v and v > 0 and v < 0.5 then dt = v end
    end
    if r.wait > 0 then
        r.wait = r.wait - dt
        SCP.teleport(p, r.x, r.y, r.z0)
        if r.wait <= 0 then
            r.removed = liftTopFloor(F.origin(), platform())
            p:playSound("SCP_LiftMoving")
        end
        return
    end
    local dir = r.z1 < r.z0 and -1 or 1
    r.z = r.z + dir * r.speed * dt
    if (dir < 0 and r.z <= r.z1) or (dir > 0 and r.z >= r.z1) then
        finishRide()
        return
    end
    SCP.teleport(p, r.x, r.y, r.z)
    stopFalling(p)
end

-- Both: the tick moves the cabin, the player update holds the player in it
-- (so the game's own falling never gets a frame to act).
SCP.on("OnTick", updateRide)
SCP.on("OnPlayerUpdate", function(player)
    local r = ride
    if r and r.player == player and r.wait <= 0 then
        SCP.teleport(player, r.x, r.y, r.z)
        stopFalling(player)
    end
end)

local function travel(player, dest)
    if ride then return end
    if SCP.opt("LiftRide") == false then
        teleportTravel(player, dest)
    else
        startRide(player, dest)
    end
end

local function onFillWorldMenu(playerNum, context, worldobjects, test)
    local obj, info = findElevatorObject(worldobjects)
    if not obj then return end
    if test then return true end
    local player = getSpecificPlayer(playerNum)
    local dests = F.liftDestinations(info)
    if #dests == 0 or ride then return end
    local parent = context:addOption(getText("ContextMenu_SCP_Elevator"))
    local sub = ISContextMenu:getNew(context)
    context:addSubMenu(parent, sub)
    for _, d in ipairs(dests) do
        sub:addOption(getText(LEVEL_TEXT[d.label] or d.label), player, function(p)
            if SCP.dist(p, obj) > 2.5 then
                luautils.walkAdj(p, obj:getSquare())
                return
            end
            travel(p, d)
        end)
    end
end

SCP.on("OnFillWorldObjectContextMenu", onFillWorldMenu)
