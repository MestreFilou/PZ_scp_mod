--[[
    SCP-008: the zombie plague, the origin of the Knox infection.
    - Its containment room in Heavy Containment leaks: breathing there
      without a gas mask (with a filter) or a hazmat suit can infect you.
    - During a breach the whole Heavy Containment Zone is contaminated.
    - Opening a sample infects you, unless your air is filtered.
]]

require "SCP_System"
require "SCP_Facility_Layout"

SCP.SCP008 = SCP.SCP008 or {}

local ROOM_CHANCE = 25    -- % per minute inside SCP-008's room
local HCZ_CHANCE = 3      -- % per minute in HCZ during a breach

local function everyMinute()
    for _, player in ipairs(SCP.localPlayers()) do
        local room, level = SCP.Facility.roomAt(player:getX(), player:getY(), player:getZ())
        local chance = 0
        if room == "V" then
            chance = ROOM_CHANCE
        elseif level and level.id == "HCZ" and SCP.isBreachActive() then
            chance = HCZ_CHANCE
        end
        if chance > 0 then
            if SCP.hasAirProtection(player) then
                if ZombRand(10) == 0 then SCP.say(player, "UI_SCP_008_Filtered", 160, 220, 160) end
            else
                SCP.setStat(player, "SICKNESS", math.min(1, SCP.getStat(player, "SICKNESS") + 0.02))
                if ZombRand(100) < chance then
                    SCP.infect(player)
                    SCP.say(player, "UI_SCP_008_Infected", 255, 60, 60)
                elseif ZombRand(3) == 0 then
                    SCP.say(player, "UI_SCP_008_Air", 200, 200, 120)
                end
            end
        end
    end
end

Events.EveryOneMinute.Add(everyMinute)

function SCP.SCP008.openSample(player, item)
    item:getContainer():Remove(item)
    if SCP.hasAirProtection(player) then
        SCP.say(player, "UI_SCP_008_Filtered", 160, 220, 160)
    else
        SCP.infect(player)
        SCP.say(player, "UI_SCP_008_Infected", 255, 60, 60)
    end
end
