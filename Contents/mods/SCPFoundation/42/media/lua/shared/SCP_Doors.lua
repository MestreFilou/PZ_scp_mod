--[[
    Keycard security doors.
    A secured door keeps its required level (1 to 5) in its mod data and in
    the world registry (so the breach event can find every secured door).
    Locked doors relock themselves once they are closed again.
]]

require "SCP_System"

SCP.Doors = SCP.Doors or {}

-- Map door sprites to a level here to secure every door of that kind
-- automatically (useful once the facility map exists).
SCP.Doors.SpriteLevels = SCP.Doors.SpriteLevels or {
    -- ["fixtures_doors_01_56"] = 3,
}

function SCP.Doors.isDoor(obj)
    if not obj then return false end
    if instanceof(obj, "IsoDoor") then return true end
    return instanceof(obj, "IsoThumpable") and obj:isDoor()
end

function SCP.Doors.key(sq)
    return sq:getX() .. "," .. sq:getY() .. "," .. sq:getZ()
end

function SCP.Doors.getLevel(door)
    local lvl = door:getModData().SCP_KeyLevel
    if lvl then return lvl end
    local sprite = door:getSprite() and door:getSprite():getName()
    return sprite and SCP.Doors.SpriteLevels[sprite] or 0
end

function SCP.Doors.find(x, y, z)
    local sq = getCell():getGridSquare(x, y, z)
    if not sq then return nil end
    local objs = sq:getObjects()
    for i = 0, objs:size() - 1 do
        local o = objs:get(i)
        if SCP.Doors.isDoor(o) then return o end
    end
    return nil
end

function SCP.Doors.isOpen(door)
    if door.IsOpen then return door:IsOpen() end
    if door.isOpen then return door:isOpen() end
    return false
end

function SCP.Doors.setLocked(door, locked)
    if door.setIsLocked then door:setIsLocked(locked) end
    if door.setLockedByKey then door:setLockedByKey(locked) end
end

-- Opens or closes a door, whoever is (or is not) standing next to it.
function SCP.Doors.setOpen(door, open, player)
    if SCP.Doors.isOpen(door) == open then return end
    if open then SCP.Doors.setLocked(door, false) end
    if door.ToggleDoor then pcall(door.ToggleDoor, door, player) end
    if SCP.Doors.isOpen(door) ~= open and door.ToggleDoorSilent then pcall(door.ToggleDoorSilent, door) end
end

-- The big gates are several doors side by side (mod data SCP_Gate = gate id).
-- Returns every loaded door of the gate `door` belongs to, or nil.
function SCP.Doors.gateDoors(door)
    local id = door:getModData().SCP_Gate
    if not id then return nil end
    local md = ModData.get("SCPFoundation")
    local list = md and md.gates and md.gates[id]
    if not list then return nil end
    local doors = {}
    for _, p in ipairs(list) do
        local d = SCP.Doors.find(p.x, p.y, p.z)
        if d then doors[#doors + 1] = d end
    end
    return doors, id
end

-- Applies a level change locally (all machines run this).
function SCP.Doors.apply(x, y, z, level, locked)
    local door = SCP.Doors.find(x, y, z)
    if not door then return nil end
    if level ~= nil then
        door:getModData().SCP_KeyLevel = level > 0 and level or nil
    end
    if locked ~= nil then SCP.Doors.setLocked(door, locked) end
    return door
end

------------------------------------------------------------------------
-- Server side
------------------------------------------------------------------------

local function broadcast(x, y, z, level, locked)
    SCP.sendToClients("DoorState", { x = x, y = y, z = z, level = level, locked = locked })
end

SCP.ServerCommands.SetDoorLevel = function(player, args)
    if not SCP.isAdmin(player) then return end
    local level = math.max(0, math.min(SCP.MaxKeyLevel, args.level or 0))
    local door = SCP.Doors.apply(args.x, args.y, args.z, level, level > 0)
    if not door then return end
    local world = SCP.world()
    world.doors = world.doors or {}
    world.doors[SCP.Doors.key(door:getSquare())] = level > 0 and level or nil
    if isServer() then door:transmitModData() end
    broadcast(args.x, args.y, args.z, level, level > 0)
end

SCP.ServerCommands.KeycardUnlock = function(player, args)
    local door = SCP.Doors.find(args.x, args.y, args.z)
    if not door then return end
    local need = SCP.Doors.getLevel(door)
    if SCP.keycardLevel(player) < need and not SCP.world().breach.active then
        SCP.sendToClient(player, "KeycardResult", { ok = false, need = need })
        return
    end
    SCP.Doors.setLocked(door, false)
    broadcast(args.x, args.y, args.z, nil, false)
    -- A big gate: the card unlocks every leaf (they then follow the one the player opens).
    local leaves = SCP.Doors.gateDoors(door)
    if leaves then
        for _, d in ipairs(leaves) do
            if d ~= door then
                local sq = d:getSquare()
                SCP.Doors.setLocked(d, false)
                broadcast(sq:getX(), sq:getY(), sq:getZ(), nil, false)
            end
        end
    end
    SCP.sendToClient(player, "KeycardResult", { ok = true, x = args.x, y = args.y, z = args.z })
end

-- The leaves of a big gate move together: when one is opened or closed,
-- the others follow.
local gateState = {}     -- gate id -> last known "open" state
local nextGateCheck = 0
local function syncGates()
    if isClient() then return end
    local t = getTimestampMs()
    if t < nextGateCheck then return end
    nextGateCheck = t + 300
    local md = ModData.get("SCPFoundation")
    if not md or not md.gates then return end
    for id, list in pairs(md.gates) do
        local doors = {}
        for _, p in ipairs(list) do
            local d = SCP.Doors.find(p.x, p.y, p.z)
            if d then doors[#doors + 1] = d end
        end
        if #doors > 0 then
            local last = gateState[id]
            if last == nil then last = SCP.Doors.isOpen(doors[1]) end
            local now = last
            for _, d in ipairs(doors) do
                if SCP.Doors.isOpen(d) ~= last then now = not last break end
            end
            for _, d in ipairs(doors) do
                if SCP.Doors.isOpen(d) ~= now then SCP.Doors.setOpen(d, now, nil) end
            end
            gateState[id] = now
        end
    end
end

SCP.on("OnTick", syncGates)

-- Unlock (breach) or relock every registered door.
function SCP.Doors.setAllLocked(locked)
    local world = SCP.world()
    for key, level in pairs(world.doors or {}) do
        local x, y, z = key:match("(-?%d+),(-?%d+),(-?%d+)")
        x, y, z = tonumber(x), tonumber(y), tonumber(z)
        local door = SCP.Doors.find(x, y, z)
        if door then
            SCP.Doors.setLocked(door, locked)
            if not locked then SCP.Doors.setOpen(door, true, nil) end
        end
        broadcast(x, y, z, level, locked)
    end
end

-- Closed secured doors lock themselves again (unless a breach is on).
local function relock()
    if isClient() then return end
    local world = SCP.world()
    if world.breach.active then return end
    for key, level in pairs(world.doors or {}) do
        local x, y, z = key:match("(-?%d+),(-?%d+),(-?%d+)")
        local door = SCP.Doors.find(tonumber(x), tonumber(y), tonumber(z))
        if door and not SCP.Doors.isOpen(door) and not door:isLocked() then
            SCP.Doors.setLocked(door, true)
            broadcast(tonumber(x), tonumber(y), tonumber(z), level, true)
        end
    end
end

SCP.on("EveryOneMinute", relock)

------------------------------------------------------------------------
-- Client side
------------------------------------------------------------------------

SCP.ClientCommands.DoorState = function(args)
    SCP.Doors.apply(args.x, args.y, args.z, args.level, args.locked)
end
