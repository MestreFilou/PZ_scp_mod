--[[
    Containment shock maul: each hit with charge left uses one charge and
    sends a discharge into the target (extra damage, knocked down) and arcs
    to one more zombie close by. A blue flash lights the spot for a moment.
    Empty, it is only a heavy maul. Recharge: right click > recharge with a
    battery (SCP_Anomalies_Logic.lua).
]]

require "SCP_System"
require "SCP_Anomalies_Logic"

local MAUL = "Base.SCP_ShockMaul"
local ARC_RANGE = 2.5
local flashes = {}

local function try(obj, method, ...)
    if obj and obj[method] then
        local ok, res = pcall(obj[method], obj, ...)
        if ok then return res end
    end
    return nil
end

local function flash(x, y, z)
    if not IsoLightSource or not getCell() then return end
    local ok, light = pcall(IsoLightSource.new, math.floor(x), math.floor(y), math.floor(z), 0.45, 0.7, 1.0, 5)
    if ok and light then
        pcall(getCell().addLamppost, getCell(), light)
        table.insert(flashes, { light = light, off = getTimestampMs() + 180 })
    end
end

local function shock(target, power, attacker)
    if not target or target:isDead() then return end
    try(target, "setHealth", target:getHealth() - power)
    try(target, "setStaggerBack", true)
    try(target, "setKnockedDown", true)
    if target:getHealth() <= 0 then try(target, "Kill", attacker) end
end

local function onHit(attacker, target, weapon, damage)
    if not weapon or not attacker or weapon:getFullType() ~= MAUL then return end
    if not attacker:isLocalPlayer() then return end
    local md = weapon:getModData()
    local charge = SCP.Anomalies.maulCharge(weapon)
    if charge <= 0 then
        attacker:playSound("SCP_ShockMaul_Empty")
        if ZombRand(3) == 0 then SCP.say(attacker, "UI_SCP_ShockMaul_Empty", 200, 200, 200) end
        return
    end
    md.SCP_Charge = charge - 1
    attacker:playSound("SCP_ShockMaul_Hit")
    flash(target:getX(), target:getY(), target:getZ())
    if instanceof(target, "IsoZombie") then
        shock(target, 0.6, attacker)
        -- the arc jumps to the closest other zombie
        local best, bestD = nil, ARC_RANGE
        local list = getCell():getZombieList()
        for i = 0, list:size() - 1 do
            local zb = list:get(i)
            if zb ~= target and not zb:isDead() and math.floor(zb:getZ()) == math.floor(target:getZ()) then
                local d = zb:DistTo(target)
                if d < bestD then best, bestD = zb, d end
            end
        end
        if best then shock(best, 0.35, attacker) end
    else
        -- another player (PvP) or survivor: knocked down, no extra damage
        try(target, "setKnockedDown", true)
    end
    if md.SCP_Charge == 3 then SCP.say(attacker, "UI_SCP_ShockMaul_Low", 255, 200, 120) end
    if md.SCP_Charge == 0 then SCP.say(attacker, "UI_SCP_ShockMaul_Empty", 200, 200, 200) end
end

local function updateFlashes()
    if #flashes == 0 then return end
    local t = getTimestampMs()
    for i = #flashes, 1, -1 do
        if t >= flashes[i].off then
            pcall(getCell().removeLamppost, getCell(), flashes[i].light)
            table.remove(flashes, i)
        end
    end
end

SCP.on("OnWeaponHitCharacter", onHit)
SCP.on("OnTick", updateFlashes)
