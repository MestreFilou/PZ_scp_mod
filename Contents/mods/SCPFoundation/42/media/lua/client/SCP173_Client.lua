--[[
    SCP-173 "The Sculpture".
    - A statue: it never walks or plays a zombie animation, and nothing
      hurts it or knocks it over.
    - While nobody looks at it (or the one looking blinks), it moves in
      jumps, a tile at a time, towards the closest player in range.
    - Next to a player who blinks or turns their back: neck snapped.
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

local STEP_MS = 110          -- one tile per step while unseen
local KILL_DIST = 1.6
local NEIGHBOURS = { { 1, 0 }, { -1, 0 }, { 0, 1 }, { 0, -1 }, { 1, 1 }, { 1, -1 }, { -1, 1 }, { -1, -1 } }

-- Concrete: no damage, never on the floor.
local function harden(zombie)
    if zombie.setAvoidDamage then pcall(zombie.setAvoidDamage, zombie, true) end
    if zombie.setNoDamage then pcall(zombie.setNoDamage, zombie, true) end
    if zombie:getHealth() < 1000 then zombie:setHealth(1000) end
    if zombie.isKnockedDown and zombie:isKnockedDown() then pcall(zombie.setKnockedDown, zombie, false) end
    if zombie.isOnFloor and zombie:isOnFloor() then pcall(zombie.setOnFloor, zombie, false) end
    if zombie.setStaggerBack then pcall(zombie.setStaggerBack, zombie, false) end
end

-- One tile closer to the target, around walls when it can (no path finding:
-- the best free neighbour that is not behind a wall or a closed door).
local function step(zombie, target)
    local from = zombie:getCurrentSquare()
    if not from then return false end
    local tx, ty = target:getX(), target:getY()
    local best, bestD = nil, (zombie:getX() - tx) ^ 2 + (zombie:getY() - ty) ^ 2
    for _, n in ipairs(NEIGHBOURS) do
        local sq = getCell():getGridSquare(from:getX() + n[1], from:getY() + n[2], from:getZ())
        if sq and sq:isFree(false) and not from:isBlockedTo(sq) then
            local d = (sq:getX() + 0.5 - tx) ^ 2 + (sq:getY() + 0.5 - ty) ^ 2
            if d < bestD then best, bestD = sq, d end
        end
    end
    if not best then return false end
    SCP.teleport(zombie, best:getX() + 0.5, best:getY() + 0.5, best:getZ())
    zombie:faceThisObject(target)
    return true
end

local function onZombieUpdate(zombie)
    if not SCP.isEntity(zombie, SCP.Types.SCP173) then return end
    harden(zombie)
    -- always a statue: the moves below are jumps, never a walk
    SCP.freeze(zombie, true)
    local players = SCP.localPlayers()
    if #players == 0 then return end
    local md = zombie:getModData()

    for _, p in ipairs(players) do
        if SCP.sameLevel(p, zombie) and SCP.dist(p, zombie) < THREAT_DIST then SCP.Blink.setThreat(p) end
    end
    if SCP.isDormant(zombie, 6) then return end

    if watchedBy(zombie, players) then
        md.SCP_Watched = true
        return
    end
    if md.SCP_Watched then
        md.SCP_Watched = false
        zombie:playSound("SCP173_Scrape")
    end

    local t = getTimestampMs()
    local range = SCP.opt("SCP173Range") or 10
    local target, targetD = nil, math.max(range, THREAT_DIST)
    for _, p in ipairs(players) do
        if SCP.sameLevel(p, zombie) and not p:isDead() then
            local d = SCP.dist(p, zombie)
            if d < targetD then target, targetD = p, d end
        end
    end
    if not target then return end

    -- next to it, the player looks away or blinks: neck snapped
    if targetD <= KILL_DIST and (not md.SCP_NextStrike or t > md.SCP_NextStrike) then
        local blinking = SCP.Blink.isBlinking(target)
        local backTurned = SCP.facingDot(target, zombie) < BACK_TURNED_DOT
        if blinking or backTurned then
            md.SCP_NextStrike = t + ATTACK_COOLDOWN_MS
            SCP.SCP173.strike(zombie, target)
            return
        end
    end

    if targetD > KILL_DIST and (not md.SCP173_NextStep or t > md.SCP173_NextStep) then
        md.SCP173_NextStep = t + STEP_MS
        if step(zombie, target) and (not md.SCP173_NextScrape or t > md.SCP173_NextScrape) then
            md.SCP173_NextScrape = t + 900
            zombie:playSound("SCP173_Scrape")
        end
    end
end

SCP.on("OnZombieUpdate", onZombieUpdate)
