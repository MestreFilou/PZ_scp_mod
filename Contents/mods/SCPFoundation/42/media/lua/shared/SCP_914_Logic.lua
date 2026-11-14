--[[
    SCP-914 "The Clockwork Machine".
    Items go in the intake booth, a setting is chosen on the machine, the
    machine runs for a few seconds, and the results come out in the output booth.

      Rough      : smashed to pieces (scrap, rags, planks... or nothing)
      Coarse     : taken apart into its components, or worn down
      1:1        : swapped for a different item of the same kind
      Fine       : repaired, cleaned, refilled, made fresh, or upgraded
      Very Fine  : unpredictable: perfected, duplicated, transmuted, or gone

    Specific recipes (S.RECIPES) win over the generic rules. Every output
    type is checked against the item scripts, so a missing item never errors.
]]

require "SCP_System"

SCP.SCP914 = SCP.SCP914 or {}
local S = SCP.SCP914

S.SETTINGS = { "Rough", "Coarse", "OneToOne", "Fine", "VeryFine" }
S.RUN_MS = 16000          -- length of the refining sound

local function try(obj, m, ...)
    if obj and obj[m] then
        local ok, v = pcall(obj[m], obj, ...)
        if ok then return v end
    end
    return nil
end

local function exists(fullType)
    local sm = getScriptManager()
    return sm and try(sm, "FindItem", fullType) ~= nil
end

local function B(t) return t:find("%.") and t or ("Base." .. t) end

------------------------------------------------------------------------
-- Recipes: input type -> setting -> list of { type, count } (or "self"
-- to keep the improved item, or "nothing").
------------------------------------------------------------------------

S.RECIPES = {
    -- Wood
    Log            = { Rough = { { "Twigs", 3 } }, Coarse = { { "Plank", 3 } }, Fine = { { "Plank", 4 }, { "Nails", 5 } } },
    Plank          = { Rough = { { "Twigs", 2 } }, Coarse = { { "Twigs", 2 } }, Fine = { { "BaseballBat", 1 } }, VeryFine = { { "SCP_MTF_Baton", 1 } } },
    BaseballBat    = { Coarse = { { "Plank", 1 } }, Fine = { { "SCP_MTF_Baton", 1 } } },
    -- Metal
    ScrapMetal     = { Fine = { { "SheetMetal", 1 } }, VeryFine = { { "MetalBar", 2 } } },
    SheetMetal     = { Rough = { { "ScrapMetal", 2 } }, Coarse = { { "ScrapMetal", 3 } }, Fine = { { "MetalPipe", 2 } } },
    MetalPipe      = { Rough = { { "ScrapMetal", 1 } }, Coarse = { { "ScrapMetal", 2 } }, Fine = { { "Crowbar", 1 } } },
    MetalBar       = { Coarse = { { "ScrapMetal", 2 } }, Fine = { { "Crowbar", 1 } } },
    Crowbar        = { Coarse = { { "MetalPipe", 1 } }, Fine = { { "Axe", 1 } }, VeryFine = { { "WoodAxe", 1 } } },
    Nails          = { Coarse = { { "ScrapMetal", 1 } }, Fine = { { "Screws", 1 } } },
    -- Blades
    KitchenKnife   = { Coarse = { { "ScrapMetal", 1 } }, Fine = { { "HuntingKnife", 1 } }, VeryFine = { { "SCP_MTF_Knife", 1 } } },
    HuntingKnife   = { Coarse = { { "KitchenKnife", 1 } }, Fine = { { "SCP_MTF_Knife", 1 } } },
    SCP_MTF_Knife  = { Coarse = { { "HuntingKnife", 1 } } },
    SCP_MTF_Baton  = { Coarse = { { "BaseballBat", 1 } }, Fine = { { "SCP_MTF_Knife", 1 } } },
    Axe            = { Coarse = { { "Crowbar", 1 }, { "Plank", 1 } }, Fine = { { "WoodAxe", 1 } } },
    -- Guns
    Pistol         = { Rough = { { "ScrapMetal", 1 } }, Coarse = { { "ScrapMetal", 2 }, { "Screws", 1 } }, Fine = { { "Pistol2", 1 } }, VeryFine = { { "Pistol3", 1 } } },
    Pistol2        = { Coarse = { { "Pistol", 1 } }, Fine = { { "Pistol3", 1 } } },
    Shotgun        = { Coarse = { { "ScrapMetal", 2 }, { "Plank", 1 } }, Fine = { { "AssaultRifle", 1 } } },
    Bullets9mm     = { Fine = { { "Bullets45", 1 } }, VeryFine = { { "ShotgunShells", 1 } } },
    -- Cloth and medicine
    Sheet          = { Rough = { { "RippedSheets", 2 } }, Coarse = { { "RippedSheets", 4 } }, Fine = { { "SCP_LabCoat", 1 } } },
    RippedSheets   = { Fine = { { "Bandage", 1 } }, VeryFine = { { "AlcoholBandage", 1 } } },
    Bandage        = { Coarse = { { "RippedSheets", 1 } }, Fine = { { "AlcoholBandage", 1 } } },
    Pills          = { Fine = { { "PillsBeta", 1 } } },
    PillsBeta      = { Fine = { { "Antibiotics", 1 } } },
    Antibiotics    = { Coarse = { { "Pills", 1 } } },
    -- Electronics
    Battery        = { Coarse = { { "ElectronicsScrap", 1 } } },
    Torch          = { Coarse = { { "Battery", 1 }, { "ElectronicsScrap", 1 } } },
    ElectronicsScrap = { Fine = { { "Battery", 1 } } },
    -- Foundation gear
    SCP_ClassD_Jumpsuit = { Coarse = { { "RippedSheets", 3 } }, Fine = { { "SCP_MTF_Uniform", 1 } }, VeryFine = { { "SCP_Hazmat_Suit", 1 } } },
    SCP_MTF_Uniform     = { Coarse = { { "SCP_ClassD_Jumpsuit", 1 } }, Fine = { { "SCP_MTF_Vest", 1 } } },
    SCP_LabCoat         = { Coarse = { { "RippedSheets", 3 } }, Fine = { { "SCP_Hazmat_Suit", 1 } } },
    SCP_Hazmat_Suit     = { Coarse = { { "SCP_LabCoat", 1 } } },
    SCP_GasMask         = { Coarse = { { "SCP_GasFilter", 1 } }, VeryFine = { { "SCP_NVG", 1 } } },
    SCP_GasFilter       = { Fine = { { "self" } }, VeryFine = { { "SCP_GasFilter", 3 } } },
    SCP_Document_Containment = { Rough = { { "nothing" } }, VeryFine = { { "SCP_Document_008", 1 } } },
    SCP_500_Pill        = { Rough = { { "nothing" } }, Coarse = { { "Pills", 1 } }, Fine = { { "self" } } },
}

-- Items SCP-914 refuses to change: they come out untouched.
S.RESISTS = { SCP_035_Mask = true, SCP_1025_Book = true, SCP_714_Ring = true }

-- Rare Very Fine miracles: chance in %.
S.MIRACLES = {
    Pills       = { "SCP_500_Pill", 5 },
    PillsBeta   = { "SCP_500_Pill", 8 },
    Antibiotics = { "SCP_500_Pill", 12 },
}

------------------------------------------------------------------------
-- Generic rules
------------------------------------------------------------------------

local function keycardLevel(item)
    local l = item:getType():match("^SCP_Keycard_L(%d)$")
    return l and tonumber(l) or nil
end

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
    try(item, "setWetness", 0)
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
    if instanceof(item, "Food") then
        local off = try(item, "getOffAgeMax")
        if off then try(item, "setAge", off) end
        return true
    end
    return false
end

-- What is left of an item that was smashed or taken apart.
local function scrapOf(item, generous)
    local w = item:getActualWeight()
    local n = math.max(1, math.min(4, math.floor(w + (generous and 1 or 0))))
    if instanceof(item, "Clothing") then return { { "Base.RippedSheets", n } } end
    if instanceof(item, "HandWeapon") or instanceof(item, "Radio") or w >= 1 then
        return { { "Base.ScrapMetal", generous and n or math.max(1, n - 1) } }
    end
    return {}
end

------------------------------------------------------------------------
-- refine(item, setting) -> result
--   result.key  : message (translation key)
--   result.keep : true when the (changed) item itself comes out
--   result.out  : list of { fullType, count } to create in the output booth
------------------------------------------------------------------------

local function resolve(list, item)
    local out, keep = {}, false
    for _, e in ipairs(list) do
        if e[1] == "self" then
            keep = true
        elseif e[1] ~= "nothing" then
            local t = B(e[1])
            if exists(t) then out[#out + 1] = { t, e[2] or 1 } end
        end
    end
    return out, keep
end

local function fromRecipe(item, setting)
    local r = S.RECIPES[item:getType()]
    local list = r and r[setting]
    if not list then return nil end
    local out, keep = resolve(list, item)
    local nothing = list[1] and list[1][1] == "nothing"
    if #out == 0 and not keep and not nothing then return nil end -- outputs missing: use the generic rule
    if keep then makeLikeNew(item) end
    local key = ({ Rough = "UI_SCP_914_Destroyed", Coarse = "UI_SCP_914_Dismantled", OneToOne = "UI_SCP_914_Swapped",
        Fine = "UI_SCP_914_Upgraded", VeryFine = "UI_SCP_914_Upgraded" })[setting]
    if keep and #out == 0 then key = "UI_SCP_914_Improved" end
    return { key = key, keep = keep, out = out }
end

function S.refine(item, setting)
    local itype = item:getType()

    if S.RESISTS[itype] then
        return { key = "UI_SCP_914_Resists", keep = true, out = {} }
    end

    local level = keycardLevel(item)
    if level then
        local delta = ({ Rough = -99, Coarse = -1, OneToOne = 0, Fine = 1, VeryFine = 2 })[setting]
        if setting == "VeryFine" and ZombRand(100) < 20 then delta = -99 end -- fried
        local newLevel = level + delta
        if newLevel < 1 then return { key = "UI_SCP_914_Destroyed", out = {} } end
        return { key = "UI_SCP_914_Keycard", out = { { "Base.SCP_Keycard_L" .. math.min(SCP.MaxKeyLevel, newLevel), 1 } } }
    end

    if setting == "VeryFine" then
        local m = S.MIRACLES[itype]
        if m and ZombRand(100) < m[2] and exists(B(m[1])) then
            return { key = "UI_SCP_914_Panacea", out = { { B(m[1]), 1 } } }
        end
    end

    local rec = fromRecipe(item, setting)
    if rec then return rec end

    if setting == "Rough" then
        return { key = "UI_SCP_914_Destroyed", out = scrapOf(item, false) }

    elseif setting == "Coarse" then
        if wearDown(item) then return { key = "UI_SCP_914_Worn", keep = true, out = {} } end
        return { key = "UI_SCP_914_Dismantled", out = scrapOf(item, true) }

    elseif setting == "OneToOne" then
        local other = randomSameKind(item, false)
        if not other then return { key = "UI_SCP_914_Nothing", keep = true, out = {} } end
        return { key = "UI_SCP_914_Swapped", out = { { other, 1 } } }

    elseif setting == "Fine" then
        makeLikeNew(item)
        return { key = "UI_SCP_914_Improved", keep = true, out = {} }

    else -- VeryFine
        local r = ZombRand(100)
        if r < 40 then
            makeLikeNew(item)
            try(item, "setActualWeight", item:getActualWeight() * 0.5)
            return { key = "UI_SCP_914_Perfected", keep = true, out = {} }
        elseif r < 55 then
            makeLikeNew(item)
            return { key = "UI_SCP_914_Duplicated", keep = true, out = { { item:getFullType(), 1 } } }
        elseif r < 80 then
            local other = randomSameKind(item, true)
            return { key = "UI_SCP_914_Unknown", out = other and { { other, 1 } } or {} }
        else
            return { key = "UI_SCP_914_Vanished", out = {} }
        end
    end
end
