--[[
    SCP-096 "Shy Guy" - detection and behaviour on the client.
    Looking straight at its face (it faces you and you face it) triggers it.
]]

require "SCP_System"
require "SCP_096_Logic"

local LOOK_DIST = 30
local LOOK_FOV = 40                         -- the player must look right at it
local FACE_DOT = math.cos(math.rad(50))     -- 096 must be facing the player
local CRY_EVERY_MS = 9000
local SMASH_EVERY_MS = 700
local PATH_EVERY_MS = 1000

local function sawFace(player, zombie)
    return SCP.canSee(player, zombie, LOOK_DIST, LOOK_FOV) and SCP.facingDot(zombie, player) > FACE_DOT
end

local function onZombieUpdate(zombie)
    if not SCP.isEntity(zombie, SCP.Types.SCP096) then return end
    local md = zombie:getModData()
    local state = SCP.SCP096.getState(zombie)
    local t = getTimestampMs()

    if state == SCP.SCP096.IDLE then
        SCP.freeze(zombie, true)
        if not md.SCP096_NextCry or t > md.SCP096_NextCry then
            md.SCP096_NextCry = t + CRY_EVERY_MS
            zombie:playSound("SCP096_Cry")
        end
        for _, p in ipairs(SCP.localPlayers()) do
            if sawFace(p, zombie) then
                SCP.say(p, "UI_SCP_096_Seen", 255, 60, 60)
                SCP.sendToServer(p, "SCP096Trigger", { key = SCP.zombieKey(zombie) })
                return
            end
        end

    elseif state == SCP.SCP096.TRIGGERED then
        SCP.freeze(zombie, true)
        if not md.SCP096_Screamed then
            md.SCP096_Screamed = true
            zombie:playSound("SCP096_Scream")
            addSound(zombie, zombie:getX(), zombie:getY(), zombie:getZ(), 60, 60)
        end
        if md.SCP096_RageAt and t >= md.SCP096_RageAt then
            md.SCP096_State = SCP.SCP096.ENRAGED
            SCP.makeSprinter(zombie)
        end

    elseif state == SCP.SCP096.ENRAGED then
        SCP.freeze(zombie, false)
        local target = SCP.playerById(md.SCP096_Target)
        if not target or target:isDead() then
            local p = SCP.localPlayers()[1]
            if p then
                SCP.sendToServer(p, "SCP096SetState", { key = SCP.zombieKey(zombie), state = SCP.SCP096.IDLE })
            else
                SCP.SCP096.applyState(zombie, SCP.SCP096.IDLE, nil, nil)
            end
            return
        end
        if not md.SCP096_NextPath or t > md.SCP096_NextPath then
            md.SCP096_NextPath = t + PATH_EVERY_MS
            zombie:setTarget(target)
            if zombie.pathToCharacter then pcall(zombie.pathToCharacter, zombie, target) end
            SCP.makeSprinter(zombie)
        end
        if target:isLocalPlayer() and (not md.SCP096_NextSmash or t > md.SCP096_NextSmash) then
            md.SCP096_NextSmash = t + SMASH_EVERY_MS
            SCP.sendToServer(target, "SCP096Smash", {
                x = math.floor(zombie:getX()), y = math.floor(zombie:getY()), z = math.floor(zombie:getZ()),
            })
        end
    end
end

Events.OnZombieUpdate.Add(onZombieUpdate)
