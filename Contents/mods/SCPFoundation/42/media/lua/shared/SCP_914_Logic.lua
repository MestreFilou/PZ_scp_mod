--[[
    SCP-914 "The Clockwork Machine". Put an item in, pick a setting:
      Rough      : destroyed, sometimes leaves scrap
      Coarse     : worn down (half condition / half content), keycards -1 level
      1:1        : swapped for a different item of the same kind
      Fine       : like new (full condition, full, fresh), keycards +1 level
      Very Fine  : unpredictable (better, random, or gone), keycards +2 levels
]]

require "SCP_System"

SCP.SCP914 = SCP.SCP914 or {}
local S = SCP.SCP914

S.SETTINGS = { "Rough", "Coarse", "OneToOne", "Fine", "VeryFine" }

local function try(obj, m, ...)
    if obj and obj[m] then
        local ok, v = pcall(obj[m], obj, ...)
        if ok then return v end
    end
    return nil
end

local function give(player, fullType)
    local ok, item = pcall(function() return player:getInventory():AddItem(fullType) end)
    if ok and item then return item end
    return nil
end

local function remove(item)
    local c = item:getContainer()
    if c then c:Remove(item) end
end

local function keycardLevel(item)
    local l = item:getType():match("^SCP_Keycard_L(%d)$")
    return l and tonumber(l) or nil
end

-- Random item script of the same display category.
local function randomSameKind(item, anyKind)
    local all = try(getScriptManager(), "getAllItems")
    if not all then return nil end
    local cat = item:getDisplayCategory()
    local pool = {}
    for i = 0, all:size() - 1 do
        local s = all:get(i)
        local fullName = try(s, "getFullName")
        local obsolete = try(s, "getObsolete") or try(s, "isObsolete")
        local hidden = try(s, "isHidden")
        if fullName and not obsolete and not hidden and fullName ~= item:getFullType() then
            if anyKind or try(s, "getDisplayCategory") == cat then pool[#pool + 1] = fullName end
        end
    end
    if #pool == 0 then return nil end
    return pool[ZombRand(#pool) + 1]
end

local function makeLikeNew(item)
    if item.getConditionMax and item:getConditionMax() > 0 then item:setCondition(item:getConditionMax()) end
    try(item, "setBroken", false)
    try(item, "setHaveBeenRepaired", 0)
    if instanceof(item, "Food") then
        try(item, "setAge", 0)
        try(item, "setRotten", false)
        try(item, "setBurnt", false)
    end
    if instanceof(item, "DrainableComboItem") and SCP.GasMask then
        SCP.GasMask.setDrainableLevel(item, 1)
    end
    try(item, "setBloodLevel", 0)
    try(item, "setDirtyness", 0)
end

local function wearDown(item)
    if item.getConditionMax and item:getConditionMax() > 0 then
        item:setCondition(math.max(1, math.floor(item:getCondition() / 2)))
        return true
    end
    if instanceof(item, "DrainableComboItem") and SCP.GasMask then
        SCP.GasMask.setDrainableLevel(item, SCP.GasMask.getDrainableLevel(item) / 2)
        return true
    end
    return false
end

-- Returns the translation key describing what happened.
function S.refine(player, item, setting)
    local level = keycardLevel(item)
    if level then
        local delta = ({ Rough = -99, Coarse = -1, OneToOne = 0, Fine = 1, VeryFine = 2 })[setting]
        local newLevel = level + delta
        remove(item)
        if newLevel < 1 then return "UI_SCP_914_Destroyed" end
        give(player, "Base.SCP_Keycard_L" .. math.min(SCP.MaxKeyLevel, newLevel))
        return "UI_SCP_914_Keycard"
    end

    if setting == "Rough" then
        local heavy = item:getActualWeight() >= 1
        remove(item)
        if heavy then give(player, "Base.ScrapMetal") end
        return "UI_SCP_914_Destroyed"

    elseif setting == "Coarse" then
        if wearDown(item) then return "UI_SCP_914_Worn" end
        remove(item)
        return "UI_SCP_914_Destroyed"

    elseif setting == "OneToOne" then
        local other = randomSameKind(item, false)
        if not other then return "UI_SCP_914_Nothing" end
        remove(item)
        give(player, other)
        return "UI_SCP_914_Swapped"

    elseif setting == "Fine" then
        makeLikeNew(item)
        return "UI_SCP_914_Improved"

    else -- VeryFine
        local r = ZombRand(100)
        if r < 3 and item:getType():find("Pills") then
            remove(item)
            give(player, "Base.SCP_500_Pill")
            return "UI_SCP_914_Panacea"
        elseif r < 50 then
            makeLikeNew(item)
            try(item, "setActualWeight", item:getActualWeight() * 0.5)
            return "UI_SCP_914_Perfected"
        elseif r < 75 then
            local other = randomSameKind(item, true)
            remove(item)
            if other then give(player, other) end
            return "UI_SCP_914_Unknown"
        else
            remove(item)
            return "UI_SCP_914_Vanished"
        end
    end
end
