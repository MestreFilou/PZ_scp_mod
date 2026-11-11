--[[
    SCP-714 "The Jaded Ring": while worn, protects from SCP-049's touch and
    from SCP-035's possession, but makes the wearer drowsy and slow to
    recover stamina.
]]

require "SCP_System"

local function everyMinute()
    for _, player in ipairs(SCP.localPlayers()) do
        if SCP.isWearing714(player) then
            SCP.setStat(player, "FATIGUE", math.min(1, SCP.getStat(player, "FATIGUE") + 0.004))
            if SCP.getStat(player, "ENDURANCE") > 0.7 then SCP.setStat(player, "ENDURANCE", 0.7) end
            if ZombRand(120) == 0 then SCP.say(player, "UI_SCP_714_Drowsy", 120, 200, 140) end
        end
    end
end

Events.EveryOneMinute.Add(everyMinute)
