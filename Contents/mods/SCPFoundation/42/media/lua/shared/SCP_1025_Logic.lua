--[[
    SCP-1025 "Encyclopedia of Diseases": every page you read gives you the
    disease it describes.
]]

require "SCP_System"

SCP.SCP1025 = SCP.SCP1025 or {}

local function try(obj, m, ...) if obj and obj[m] then pcall(obj[m], obj, ...) end end

local PAGES = {
    { key = "UI_SCP_1025_Cold", weight = 30, fn = function(p, bd)
        try(bd, "setHasACold", true); try(bd, "setColdStrength", 60) end },
    { key = "UI_SCP_1025_FoodPoisoning", weight = 25, fn = function(p, bd)
        try(bd, "setFoodSicknessLevel", 70) end },
    { key = "UI_SCP_1025_Poison", weight = 15, fn = function(p, bd)
        try(bd, "setPoisonLevel", 40) end },
    { key = "UI_SCP_1025_Fracture", weight = 12, fn = function(p, bd)
        local parts = { BodyPartType.ForeArm_L, BodyPartType.ForeArm_R, BodyPartType.LowerLeg_L, BodyPartType.LowerLeg_R }
        local part = bd:getBodyPart(parts[ZombRand(#parts) + 1])
        try(part, "setFractureTime", 21) end },
    { key = "UI_SCP_1025_Infection", weight = 10, fn = function(p, bd)
        local part = bd:getBodyPart(BodyPartType.Hand_L)
        try(part, "setScratched", true, true); try(part, "setInfectedWound", true); try(part, "setWoundInfectionLevel", 5) end },
    { key = "UI_SCP_1025_Insomnia", weight = 6, fn = function(p, bd)
        SCP.setStat(p, "FATIGUE", 1) end },
    { key = "UI_SCP_1025_Knox", weight = 2, fn = function(p, bd)
        SCP.infect(p) end },
}

function SCP.SCP1025.readPage(player)
    local total = 0
    for _, pg in ipairs(PAGES) do total = total + pg.weight end
    local r = ZombRand(total)
    for _, pg in ipairs(PAGES) do
        r = r - pg.weight
        if r < 0 then
            pg.fn(player, player:getBodyDamage())
            SCP.say(player, pg.key, 230, 120, 120)
            return
        end
    end
end
