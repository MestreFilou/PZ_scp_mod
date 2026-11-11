--[[
    Tesla gates in Heavy Containment: a line across the corridor that
    discharges for 2.5 seconds every 7.5 seconds. Anything standing on it
    while it fires is electrocuted (players badly hurt, zombies destroyed).
]]

require "SCP_System"
require "SCP_Facility_Layout"

SCP.Tesla = SCP.Tesla or {}

local PERIOD_MS, ACTIVE_MS = 7500, 2500

function SCP.Tesla.isFiring()
    return getTimestampMs() % PERIOD_MS < ACTIVE_MS
end

local IMMUNE = {
    [SCP.Types.SCP173] = true, [SCP.Types.SCP106] = true, [SCP.Types.SCP096] = true, [SCP.Types.SCP049] = true,
}

local function onPlayerUpdate(player)
    if not player:isLocalPlayer() or player:getZ() >= 0 then return end
    if not SCP.Tesla.isFiring() then return end
    if not SCP.Facility.isTesla(player:getX(), player:getY(), player:getZ()) then return end
    local md = player:getModData()
    local t = getTimestampMs()
    if md.SCP_TeslaNext and t < md.SCP_TeslaNext then return end
    md.SCP_TeslaNext = t + ACTIVE_MS
    player:playSound("SCP_TeslaZap")
    SCP.damageHealth(player, 30)
    local part = player:getBodyDamage():getBodyPart(BodyPartType.Torso_Upper)
    if part then pcall(part.setBurned, part) end
    SCP.say(player, "UI_SCP_Tesla_Zap", 120, 160, 255)
end

local function onZombieUpdate(zombie)
    if zombie:getZ() >= 0 or not SCP.Tesla.isFiring() then return end
    if IMMUNE[SCP.getEntityType(zombie)] then return end
    if not SCP.Facility.isTesla(zombie:getX(), zombie:getY(), zombie:getZ()) then return end
    zombie:playSound("SCP_TeslaZap")
    if zombie.Kill then pcall(zombie.Kill, zombie, nil) else zombie:setHealth(0) end
end

Events.OnPlayerUpdate.Add(onPlayerUpdate)
Events.OnZombieUpdate.Add(onZombieUpdate)
