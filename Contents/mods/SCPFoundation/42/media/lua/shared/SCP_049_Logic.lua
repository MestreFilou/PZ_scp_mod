--[[
    SCP-049 "The Plague Doctor".
    - Walks toward the living. Its touch kills instantly.
    - Every body it touches rises as an SCP-049-2 instance ("cured").
      It also "cures" corpses lying near it.
    - SCP-049-2 instances stay close to the doctor and attack anyone who
      comes near it.
]]

require "SCP_System"

SCP.SCP049 = SCP.SCP049 or {}

local TOUCH_DIST = 1.0
local TOUCH_COOLDOWN_MS = 2500
local CURE_CORPSE_EVERY_MS = 15000
local CURE_RADIUS = 3
local TALK_EVERY_MS = 20000
local GUARD_RADIUS = 9       -- 049-2 attacks players this close to the doctor
local FOLLOW_DIST = 4        -- 049-2 walks back when farther than this
local REPATH_MS = 2000

-- Doctors seen recently on this machine: key -> zombie
local doctors = {}

------------------------------------------------------------------------
-- Server: raise an SCP-049-2 instance
------------------------------------------------------------------------

local function raise(x, y, z)
    if SCP.Spawner then SCP.Spawner.spawn(SCP.Types.SCP049_2, x, y, z, 1) end
end

SCP.ServerCommands.SCP049Cure = function(player, args)
    raise(args.x, args.y, args.z)
end

SCP.ServerCommands.SCP049CureCorpses = function(player, args)
    for dx = -CURE_RADIUS, CURE_RADIUS do
        for dy = -CURE_RADIUS, CURE_RADIUS do
            local sq = getCell():getGridSquare(args.x + dx, args.y + dy, args.z)
            local bodies = sq and sq:getDeadBodys()
            if bodies and bodies:size() > 0 then
                local body = bodies:get(0)
                local ok = pcall(function() sq:removeCorpse(body, false) end)
                if ok then
                    raise(sq:getX(), sq:getY(), sq:getZ())
                    return -- one at a time, it is a slow surgery
                end
            end
        end
    end
end

------------------------------------------------------------------------
-- SCP-049
------------------------------------------------------------------------

local function updateDoctor(zombie)
    local md = zombie:getModData()
    doctors[SCP.zombieKey(zombie)] = zombie

    if SCP.isDormant(zombie, 6) then
        SCP.freeze(zombie, true)
        return
    end
    SCP.freeze(zombie, false)

    local t = getTimestampMs()
    local players = SCP.localPlayers()

    for _, p in ipairs(players) do
        if SCP.sameLevel(p, zombie) then
            local d = SCP.dist(p, zombie)
            if d < 8 and (not md.SCP049_NextTalk or t > md.SCP049_NextTalk) then
                md.SCP049_NextTalk = t + TALK_EVERY_MS
                SCP.say(p, "UI_SCP_049_Talk" .. (ZombRand(3) + 1), 230, 200, 120)
            end
            if d < TOUCH_DIST and (not md.SCP049_NextTouch or t > md.SCP049_NextTouch) then
                md.SCP049_NextTouch = t + TOUCH_COOLDOWN_MS
                if SCP.isWearing714(p) then
                    -- SCP-714 keeps the "cure" from working.
                    SCP.damageHealth(p, 8)
                    SCP.say(p, "UI_SCP_714_Protects049", 120, 200, 140)
                    return
                end
                local x, y, z = math.floor(p:getX()), math.floor(p:getY()), math.floor(p:getZ())
                SCP.say(p, "UI_SCP_049_Cured", 255, 80, 80)
                SCP.killPlayer(p, zombie, nil)
                SCP.sendToServer(p, "SCP049Cure", { x = x, y = y, z = z })
                return
            end
        end
    end

    -- Look for corpses to cure (asked by whichever local player is near).
    if not md.SCP049_NextCorpse or t > md.SCP049_NextCorpse then
        md.SCP049_NextCorpse = t + CURE_CORPSE_EVERY_MS
        local p = SCP.nearestPlayer(zombie, 40, players)
        if p then
            SCP.sendToServer(p, "SCP049CureCorpses", {
                x = math.floor(zombie:getX()), y = math.floor(zombie:getY()), z = math.floor(zombie:getZ()),
            })
        end
    end
end

------------------------------------------------------------------------
-- SCP-049-2: bodyguards
------------------------------------------------------------------------

local function nearestDoctor(zombie)
    local best, bestD = nil, 60
    for key, doc in pairs(doctors) do
        if doc:isDead() or not doc:getCurrentSquare() then
            doctors[key] = nil
        elseif SCP.sameLevel(doc, zombie) then
            local d = SCP.dist(doc, zombie)
            if d < bestD then best, bestD = doc, d end
        end
    end
    return best, bestD
end

local function updateInstance(zombie)
    local md = zombie:getModData()
    local t = getTimestampMs()
    if md.SCP049_NextThink and t < md.SCP049_NextThink then return end
    md.SCP049_NextThink = t + REPATH_MS

    local doc, docDist = nearestDoctor(zombie)
    if not doc then return end -- no doctor around: behaves like a normal zombie

    -- Protect the doctor.
    local intruder = SCP.nearestPlayer(doc, GUARD_RADIUS)
    if intruder then
        zombie:setTarget(intruder)
        if zombie.pathToCharacter then pcall(zombie.pathToCharacter, zombie, intruder) end
        return
    end

    -- Stay close.
    if docDist > FOLLOW_DIST and zombie.pathToLocationF then
        pcall(zombie.pathToLocationF, zombie, doc:getX() + ZombRand(-2, 3), doc:getY() + ZombRand(-2, 3), doc:getZ())
    end
end

local function onZombieUpdate(zombie)
    local t = SCP.getEntityType(zombie)
    if t == SCP.Types.SCP049 then
        updateDoctor(zombie)
    elseif t == SCP.Types.SCP049_2 then
        updateInstance(zombie)
    end
end

Events.OnZombieUpdate.Add(onZombieUpdate)
