--[[
    SCP-966 "Sleep Killer": invisible to the naked eye (night vision goggles
    reveal it). It stalks nearby people and keeps them awake, and only
    attacks once they are exhausted.

    SCP-939 "With Many Voices": blind predators that lure prey by imitating
    human voices. They hunt by sound: a sneaking player is hard to find.
]]

require "SCP_System"

------------------------------------------------------------------------
-- SCP-966
------------------------------------------------------------------------

local function seesWithNVG(player)
    return SCP.getWorn(player, "Base.SCP_NVG") ~= nil
end

local function setVisible(zombie, playerNum, visible)
    local a = visible and 1 or 0
    if zombie.setAlphaAndTarget then
        pcall(zombie.setAlphaAndTarget, zombie, playerNum, a)
    elseif zombie.setAlpha then
        pcall(zombie.setAlpha, zombie, playerNum, a)
        if zombie.setTargetAlpha then pcall(zombie.setTargetAlpha, zombie, playerNum, a) end
    end
end

local function update966(zombie)
    local md = zombie:getModData()
    for _, p in ipairs(SCP.localPlayers()) do
        setVisible(zombie, p:getPlayerNum(), seesWithNVG(p))
    end
    if SCP.isDormant(zombie, 4) then
        SCP.freeze(zombie, true)
        return
    end

    local t = getTimestampMs()
    local target, d = SCP.nearestPlayer(zombie, 8, SCP.localPlayers())
    if not target then
        SCP.freeze(zombie, false)
        return
    end
    -- Keeps its prey awake.
    if not md.SCP966_Next or t > md.SCP966_Next then
        md.SCP966_Next = t + 2000
        SCP.setStat(target, "FATIGUE", math.min(1, SCP.getStat(target, "FATIGUE") + 0.01))
        if ZombRand(15) == 0 then SCP.say(target, "UI_SCP_966_Feel", 170, 170, 200) end
    end
    -- Only strikes the exhausted.
    SCP.freeze(zombie, SCP.getStat(target, "FATIGUE") < 0.7 and d < 3)
end

------------------------------------------------------------------------
-- SCP-939
------------------------------------------------------------------------

local function update939(zombie)
    local md = zombie:getModData()
    if SCP.isDormant(zombie, 5) then
        SCP.freeze(zombie, true)
        return
    end
    local t = getTimestampMs()
    if not md.SCP939_Init then
        md.SCP939_Init = true
        SCP.makeSprinter(zombie)
    end

    -- Voice lure
    if not md.SCP939_NextVoice or t > md.SCP939_NextVoice then
        md.SCP939_NextVoice = t + 25000 + ZombRand(20000)
        zombie:playSound("SCP939_Voice")
        for _, p in ipairs(SCP.localPlayers()) do
            if SCP.sameLevel(p, zombie) and SCP.dist(p, zombie) < 25 then
                SCP.say(p, "UI_SCP_939_Voice" .. (ZombRand(4) + 1), 200, 200, 200)
            end
        end
    end

    -- Blind: loses a sneaking target that is not right next to it.
    local p, d = SCP.nearestPlayer(zombie, 30, SCP.localPlayers())
    if p and p:isSneaking() and d > 2 then
        SCP.freeze(zombie, true)
    else
        SCP.freeze(zombie, false)
    end
end

Events.OnZombieUpdate.Add(function(zombie)
    local t = SCP.getEntityType(zombie)
    if t == SCP.Types.SCP966 then
        update966(zombie)
    elseif t == SCP.Types.SCP939 then
        update939(zombie)
    end
end)
