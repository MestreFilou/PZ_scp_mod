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
    SCP.sendToClient(player, "KeycardResult", { ok = true, x = args.x, y = args.y, z = args.z })
end

-- Unlock (breach) or relock every registered door.
function SCP.Doors.setAllLocked(locked)
    local world = SCP.world()
    for key, level in pairs(world.doors or {}) do
        local x, y, z = key:match("(-?%d+),(-?%d+),(-?%d+)")
        x, y, z = tonumber(x), tonumber(y), tonumber(z)
        local door = SCP.Doors.find(x, y, z)
        if door then
            SCP.Doors.setLocked(door, locked)
            if not locked and not SCP.Doors.isOpen(door) and door.ToggleDoor then
                pcall(door.ToggleDoor, door, nil)
            end
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

Events.EveryOneMinute.Add(relock)

------------------------------------------------------------------------
-- Client side
------------------------------------------------------------------------

SCP.ClientCommands.DoorState = function(args)
    SCP.Doors.apply(args.x, args.y, args.z, args.level, args.locked)
end
