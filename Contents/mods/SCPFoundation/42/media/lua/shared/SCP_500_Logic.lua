--[[
    SCP-500 (Panacea): one pill cures the Knox infection and every injury,
    then resets health and fatigue.
]]

require "SCP_System"

SCP.SCP500 = SCP.SCP500 or {}

-- Call obj:method(...) only if the method exists, and never throw.
local function try(obj, method, ...)
    if obj and obj[method] then
        local ok, res = pcall(obj[method], obj, ...)
        if ok then return res end
    end
    return nil
end

local function healPart(part)
    try(part, "SetInfected", false)
    try(part, "SetFakeInfected", false)
    try(part, "SetBitten", false)
    try(part, "setScratched", false, true)
    try(part, "setCut", false)
    try(part, "setDeepWounded", false)
    try(part, "setDeepWoundTime", 0)
    try(part, "setBleeding", false)
    try(part, "setBleedingTime", 0)
    try(part, "setFractureTime", 0)
    try(part, "setSplint", false, 0)
    try(part, "setHaveGlass", false)
    try(part, "setHaveBullet", false, 0)
    try(part, "setBurnTime", 0)
    try(part, "setNeedBurnWash", false)
    try(part, "setWoundInfectionLevel", 0)
    try(part, "setInfectedWound", false)
    try(part, "setStitched", false)
    try(part, "setBandaged", false, 0)
    try(part, "setAdditionalPain", 0)
    try(part, "RestoreToFullHealth")
end

function SCP.SCP500.cure(player)
    if not player or player:isDead() then return end
    local bd = player:getBodyDamage()

    -- Knox infection
    try(bd, "setInfected", false)
    try(bd, "setInfectionLevel", 0)
    try(bd, "setInfectionTime", -1)
    try(bd, "setInfectionMortalityDuration", -1)
    try(bd, "setIsFakeInfected", false)
    try(bd, "setFakeInfectionLevel", 0)

    -- Poison, food sickness, cold
    try(bd, "setPoisonLevel", 0)
    try(bd, "setFoodSicknessLevel", 0)
    try(bd, "setColdStrength", 0)
    try(bd, "setHasACold", false)

    -- Every body part
    local parts = bd:getBodyParts()
    for i = 0, parts:size() - 1 do healPart(parts:get(i)) end

    try(bd, "RestoreToFullHealth")
    try(bd, "setOverallBodyHealth", 100)

    SCP.setStat(player, "FATIGUE", 0)
    SCP.setStat(player, "ENDURANCE", 1)
    SCP.setStat(player, "PAIN", 0)
    SCP.setStat(player, "PANIC", 0)
    SCP.setStat(player, "STRESS", 0)
    SCP.setStat(player, "SICKNESS", 0)

    local md = player:getModData()
    md.SCP_LastPanacea = getGameTime():getWorldAgeHours()
end
