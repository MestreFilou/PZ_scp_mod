--[[
    Containment breach.
    Start: power cut, every keycard door unlocks and opens, sirens and red
    lights at every containment point, SCPs and zombified guards spawn.
    End (after BreachDurationHours): power and door locks come back.

    Triggered at random (BreachChancePerDay) once containment points exist,
    or by an admin from the context menu.
]]

require "SCP_System"
require "SCP_Doors"
require "SCP_Spawner"

SCP.Breach = SCP.Breach or {}

local function now() return getGameTime():getWorldAgeHours() end

local function pointsForClients()
    local list = {}
    for _, p in ipairs(SCP.world().points) do list[#list + 1] = { x = p.x, y = p.y, z = p.z } end
    return list
end

local function setPower(on)
    local world = getWorld()
    if world and world.setHydroPowerOn then pcall(world.setHydroPowerOn, world, on) end
end

function SCP.Breach.isActive()
    return SCP.world().breach.active == true
end

function SCP.Breach.start()
    local world = SCP.world()
    if world.breach.active then return false end
    local w = getWorld()
    world.breach = {
        active = true,
        endsAt = now() + SCP.opt("BreachDurationHours"),
        hadPower = w and w.isHydroPowerOn and w:isHydroPowerOn() or false,
    }
    SCP.log("containment breach started")

    setPower(false)
    SCP.Doors.setAllLocked(false)

    local guards = SCP.opt("BreachGuardCount")
    local guardPoints = {}
    for _, p in ipairs(world.points) do
        if p.type == SCP.Types.GUARD then
            guardPoints[#guardPoints + 1] = p
        else
            SCP.Spawner.spawn(p.type, p.x, p.y, p.z, 1)
        end
    end
    if #guardPoints == 0 then guardPoints = world.points end
    if #guardPoints > 0 and guards > 0 then
        for i = 1, guards do
            local p = guardPoints[(i - 1) % #guardPoints + 1]
            SCP.Spawner.spawn(SCP.Types.GUARD, p.x + ZombRand(-3, 4), p.y + ZombRand(-3, 4), p.z, 1)
        end
    end

    -- Wake every zombie in earshot of each siren.
    for _, p in ipairs(world.points) do addSound(nil, p.x, p.y, p.z, 120, 120) end

    if isServer() then ModData.transmit("SCPFoundation") end
    SCP.sendToClients("BreachStart", { points = pointsForClients() })
    return true
end

function SCP.Breach.stop()
    local world = SCP.world()
    if not world.breach.active then return false end
    local hadPower = world.breach.hadPower
    world.breach = { active = false }
    if hadPower then setPower(true) end
    SCP.Doors.setAllLocked(true)
    if isServer() then ModData.transmit("SCPFoundation") end
    SCP.sendToClients("BreachEnd", {})
    SCP.log("containment breach ended")
    return true
end

local function everyTenMinutes()
    if isClient() then return end
    local world = SCP.world()
    if world.breach.active then
        if now() >= (world.breach.endsAt or 0) then
            SCP.Breach.stop()
        else
            -- Keep the sirens drawing the dead in.
            for _, p in ipairs(world.points) do addSound(nil, p.x, p.y, p.z, 100, 100) end
            SCP.sendToClients("BreachPulse", { points = pointsForClients() })
        end
    end
end

local function everyDay()
    if isClient() then return end
    if #SCP.world().points == 0 then return end
    if ZombRand(100) < SCP.opt("BreachChancePerDay") then SCP.Breach.start() end
end

Events.EveryTenMinutes.Add(everyTenMinutes)
Events.EveryDays.Add(everyDay)

SCP.ServerCommands.StartBreach = function(player, args)
    if not SCP.isAdmin(player) then return end
    SCP.Breach.start()
end

SCP.ServerCommands.StopBreach = function(player, args)
    if not SCP.isAdmin(player) then return end
    SCP.Breach.stop()
end
