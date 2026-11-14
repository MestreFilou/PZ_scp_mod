--[[
    Spawns SCP entities and Foundation staff. SCPs are zombies wearing a
    dedicated outfit (see media/clothing/clothing.xml), which is how every
    machine recognises them.
]]

require "SCP_System"

SCP.Spawner = SCP.Spawner or {}

local HEALTH = {
    [SCP.Types.SCP173] = 1000, -- concrete: practically unkillable
    [SCP.Types.SCP096] = 20,
    [SCP.Types.SCP106] = 1000,
    [SCP.Types.SCP035] = 6,
    [SCP.Types.SCP049] = 40,
    [SCP.Types.SCP049_2] = 3,
    [SCP.Types.SCP939] = 5,
    [SCP.Types.SCP966] = 3,
    [SCP.Types.GUARD]  = 2,
}

-- Creature models exist for both skeletons (scp_0xx.x for Bob, kate_scp_0xx.x for Kate).
local function addZombies(x, y, z, count, outfit)
    local female = 50
    local ok, list = pcall(addZombiesInOutfit, x, y, z, count, outfit, female)
    if ok and list then return list end
    ok, list = pcall(addZombiesInOutfit, x, y, z, count, outfit, female, false, false, false, false, 1.0)
    if ok and list then return list end
    SCP.log("could not spawn outfit", outfit)
    return nil
end

function SCP.Spawner.spawn(scpType, x, y, z, count)
    local list = addZombies(x, y, z, count or 1, scpType)
    if not list then return {} end
    local out = {}
    for i = 0, list:size() - 1 do
        local zombie = list:get(i)
        zombie:getModData().SCP_Type = scpType
        if HEALTH[scpType] then zombie:setHealth(HEALTH[scpType]) end
        if scpType == SCP.Types.SCP035 then SCP.makeSprinter(zombie) end
        out[#out + 1] = zombie
    end
    SCP.log("spawned", scpType, "x" .. (count or 1), "at", x, y, z)
    return out
end

-- Living staff (non-zombie) is out of scope: a "Class-D" or "MTF" spawn
-- creates a zombie in that outfit, which is what is left of the staff.
SCP.Spawner.StaffOutfits = { "SCP_ClassD", "SCP_MTF", "SCP_Hazmat" }

function SCP.Spawner.spawnStaff(x, y, z, count)
    local outfit = SCP.Spawner.StaffOutfits[ZombRand(#SCP.Spawner.StaffOutfits) + 1]
    return addZombies(x, y, z, count or 1, outfit)
end

------------------------------------------------------------------------
-- Admin commands
------------------------------------------------------------------------

SCP.ServerCommands.Spawn = function(player, args)
    if not SCP.isAdmin(player) then return end
    SCP.Spawner.spawn(args.type, args.x, args.y, args.z, args.count or 1)
end

-- Containment points: where each SCP is held and released during a breach.
SCP.ServerCommands.AddPoint = function(player, args)
    if not SCP.isAdmin(player) then return end
    local world = SCP.world()
    table.insert(world.points, { type = args.type, x = args.x, y = args.y, z = args.z })
    if isServer() then ModData.transmit("SCPFoundation") end
    SCP.sendToClient(player, "Notify", { key = "UI_SCP_PointAdded" })
end

SCP.ServerCommands.ClearPoints = function(player, args)
    if not SCP.isAdmin(player) then return end
    local world = SCP.world()
    local keep = {}
    for _, p in ipairs(world.points) do
        local dx, dy = p.x - args.x, p.y - args.y
        if p.z ~= args.z or dx * dx + dy * dy > (args.radius or 10) ^ 2 then keep[#keep + 1] = p end
    end
    world.points = keep
    if isServer() then ModData.transmit("SCPFoundation") end
    SCP.sendToClient(player, "Notify", { key = "UI_SCP_PointsCleared" })
end
