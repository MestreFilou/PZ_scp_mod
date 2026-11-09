--[[
    SCP-173 "The Sculpture".
    - Frozen while any local player looks at it (and is not blinking).
    - When nobody watches it and a player within range blinks or turns
      their back, it appears right behind that player and snaps their neck.
]]

require "SCP_System"
require "SCPBlinkUI"

SCP.SCP173 = SCP.SCP173 or {}

local VIEW_DIST = 30
local VIEW_FOV = 110
local THREAT_DIST = 25
local BACK_TURNED_DOT = math.cos(math.rad(60))
local ATTACK_COOLDOWN_MS = 1500

local function watchedBy(zombie, players)
    for _, p in ipairs(players) do
        if SCP.canSee(p, zombie, VIEW_DIST, VIEW_FOV) and not SCP.Blink.isBlinking(p) then
            return true
        end
    end
    return false
end

-- Free square right behind the player, or any free neighbour.
local function squareBehind(player)
    local fwd = player:getForwardDirection()
    local px, py, pz = player:getX(), player:getY(), math.floor(player:getZ())
    local candidates = {
        { -fwd:getX(), -fwd:getY() }, { 1, 0 }, { -1, 0 }, { 0, 1 }, { 0, -1 },
    }
    for _, c in ipairs(candidates) do
        local sq = getCell():getGridSquare(math.floor(px + c[1] + 0.5), math.floor(py + c[2] + 0.5), pz)
        if sq and sq:isFree(false) then return sq end
    end
    return player:getSquare()
end

function SCP.SCP173.strike(zombie, player)
    local sq = squareBehind(player)
    zombie:setX(sq:getX() + 0.5)
    zombie:setY(sq:getY() + 0.5)
    zombie:setZ(sq:getZ())
    if zombie.setLx then zombie:setLx(zombie:getX()); zombie:setLy(zombie:getY()) end
    zombie:faceThisObject(player)
    player:playSound("SCP173_NeckSnap")
    SCP.killPlayer(player, zombie, BodyPartType.Neck)
end

local function onZombieUpdate(zombie)
    if not SCP.isEntity(zombie, SCP.Types.SCP173) then return end
    local players = SCP.localPlayers()
    if #players == 0 then return end
    local md = zombie:getModData()

    for _, p in ipairs(players) do
        if SCP.sameLevel(p, zombie) and SCP.dist(p, zombie) < THREAT_DIST then SCP.Blink.setThreat(p) end
    end

    if watchedBy(zombie, players) then
        SCP.freeze(zombie, true)
        md.SCP_Watched = true
        return
    end

    if md.SCP_Watched then
        md.SCP_Watched = false
        zombie:playSound("SCP173_Scrape")
    end
    SCP.freeze(zombie, false)

    local t = getTimestampMs()
    if md.SCP_NextStrike and t < md.SCP_NextStrike then return end
    local range = SCP.opt("SCP173Range")
    for _, p in ipairs(players) do
        if SCP.sameLevel(p, zombie) and SCP.dist(p, zombie) <= range then
            local blinking = SCP.Blink.isBlinking(p)
            local backTurned = SCP.facingDot(p, zombie) < BACK_TURNED_DOT
            local reachable = not zombie.CanSee or zombie:CanSee(p)
            if reachable and (blinking or backTurned) then
                md.SCP_NextStrike = t + ATTACK_COOLDOWN_MS
                SCP.SCP173.strike(zombie, p)
                return
            end
        end
    end
end

Events.OnZombieUpdate.Add(onZombieUpdate)
