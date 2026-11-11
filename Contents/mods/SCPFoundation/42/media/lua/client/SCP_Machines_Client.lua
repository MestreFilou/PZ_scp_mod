--[[
    Context menus for the site's machines and anomalous items:
      SCP-914 (refining), SCP-294 (drinks), documents, SCP-1025, SCP-008 samples.
]]

require "SCP_System"
require "SCP_914_Logic"
require "SCP_1025_Logic"
require "SCP_008_Logic"

local function findTagged(worldobjects, key)
    for _, o in ipairs(worldobjects) do
        local sq = o.getSquare and o:getSquare()
        if sq then
            local objs = sq:getObjects()
            for i = 0, objs:size() - 1 do
                if objs:get(i):getModData()[key] then return objs:get(i) end
            end
        end
    end
    return nil
end

local function near(player, obj)
    if SCP.dist(player, obj) > 2 then
        luautils.walkAdj(player, obj:getSquare())
        return false
    end
    return true
end

------------------------------------------------------------------------
-- SCP-914
------------------------------------------------------------------------

local function on914(player, machine, item, setting)
    if not near(player, machine) then return end
    if not player:getInventory():contains(item) then return end
    machine:getSquare():playSound("SCP914_Clockwork")
    local key = SCP.SCP914.refine(player, item, setting)
    SCP.say(player, key, 220, 200, 140)
end

local function fill914(context, player, machine)
    local root = context:addOption(getText("ContextMenu_SCP_914_Use"))
    local menu = ISContextMenu:getNew(context)
    context:addSubMenu(root, menu)
    local items = player:getInventory():getItems()
    for _, setting in ipairs(SCP.SCP914.SETTINGS) do
        local opt = menu:addOption(getText("ContextMenu_SCP_914_" .. setting))
        local sub = ISContextMenu:getNew(menu)
        menu:addSubMenu(opt, sub)
        local shown = 0
        for i = 0, items:size() - 1 do
            local item = items:get(i)
            if shown < 25 and not player:isEquipped(item) and not instanceof(item, "InventoryContainer") then
                sub:addOption(item:getDisplayName(), player, on914, machine, item, setting)
                shown = shown + 1
            end
        end
        if shown == 0 then opt.notAvailable = true end
    end
end

------------------------------------------------------------------------
-- SCP-294
------------------------------------------------------------------------

local COOLDOWN_HOURS = 0.5

local DRINKS = {
    Water = function(p) SCP.setStat(p, "THIRST", 0) end,
    Coffee = function(p)
        SCP.setStat(p, "THIRST", math.max(0, SCP.getStat(p, "THIRST") - 0.2))
        SCP.setStat(p, "FATIGUE", math.max(0, SCP.getStat(p, "FATIGUE") - 0.3))
    end,
    Tea = function(p)
        SCP.setStat(p, "THIRST", math.max(0, SCP.getStat(p, "THIRST") - 0.3))
        SCP.setStat(p, "STRESS", math.max(0, SCP.getStat(p, "STRESS") - 0.3))
    end,
    Chocolate = function(p)
        SCP.setStat(p, "BOREDOM", 0)
        SCP.setStat(p, "STRESS", math.max(0, SCP.getStat(p, "STRESS") - 0.2))
        local bd = p:getBodyDamage()
        if bd.setUnhappynessLevel then pcall(bd.setUnhappynessLevel, bd, 0) end
    end,
}

local SURPRISES = {
    { "UI_SCP_294_Surprise1", function(p) SCP.setStat(p, "THIRST", 0); SCP.setStat(p, "FATIGUE", 0) end },
    { "UI_SCP_294_Surprise2", function(p) SCP.setStat(p, "DRUNKENNESS", 60) end },
    { "UI_SCP_294_Surprise3", function(p) local bd = p:getBodyDamage(); pcall(bd.setPoisonLevel, bd, 25) end },
    { "UI_SCP_294_Surprise4", function(p) SCP.setStat(p, "PANIC", 80) end },
    { "UI_SCP_294_Surprise5", function(p) local bd = p:getBodyDamage(); if bd.AddGeneralHealth then pcall(bd.AddGeneralHealth, bd, 15) end end },
}

local function on294(player, machine, drink)
    if not near(player, machine) then return end
    local md = player:getModData()
    local now = getGameTime():getWorldAgeHours()
    if md.SCP294_Next and now < md.SCP294_Next then
        SCP.say(player, "UI_SCP_294_OutOfRange", 200, 200, 200)
        return
    end
    md.SCP294_Next = now + COOLDOWN_HOURS
    player:playSound("SCP_PillSwallow")
    if drink == "Surprise" then
        local s = SURPRISES[ZombRand(#SURPRISES) + 1]
        s[2](player)
        SCP.say(player, s[1], 220, 180, 120)
    else
        DRINKS[drink](player)
        SCP.say(player, "UI_SCP_294_" .. drink, 220, 180, 120)
    end
end

local function fill294(context, player, machine)
    local root = context:addOption(getText("ContextMenu_SCP_294_Use"))
    local menu = ISContextMenu:getNew(context)
    context:addSubMenu(root, menu)
    for _, d in ipairs({ "Water", "Coffee", "Tea", "Chocolate", "Surprise" }) do
        menu:addOption(getText("ContextMenu_SCP_294_" .. d), player, on294, machine, d)
    end
end

local function onFillWorldMenu(playerNum, context, worldobjects, test)
    local player = getSpecificPlayer(playerNum)
    local m914 = findTagged(worldobjects, "SCP914_Machine")
    local m294 = findTagged(worldobjects, "SCP294_Machine")
    if not m914 and not m294 then return end
    if test then return true end
    if m914 then fill914(context, player, m914) end
    if m294 then fill294(context, player, m294) end
end

Events.OnFillWorldObjectContextMenu.Add(onFillWorldMenu)

------------------------------------------------------------------------
-- Readable documents, SCP-1025, SCP-008 samples
------------------------------------------------------------------------

local DOCS = {
    ["Base.SCP_Document_Containment"] = "UI_SCP_Doc_Containment",
    ["Base.SCP_Document_008"] = "UI_SCP_Doc_008",
}

local function readDoc(player, key)
    local w, h = 520, 420
    local x = (getCore():getScreenWidth() - w) / 2
    local y = (getCore():getScreenHeight() - h) / 2
    local modal = ISModalRichText:new(x, y, w, h, getText(key), false, nil, nil, player:getPlayerNum())
    modal:initialise()
    modal:addToUIManager()
end

local function firstItem(entry)
    if type(entry) == "table" and entry.items then return entry.items[1] end
    return entry
end

local function onFillInventoryMenu(playerNum, context, items)
    local player = getSpecificPlayer(playerNum)
    for _, entry in ipairs(items) do
        local item = firstItem(entry)
        if item and item.getFullType then
            local t = item:getFullType()
            if DOCS[t] then
                context:addOption(getText("ContextMenu_SCP_ReadDocument"), player, readDoc, DOCS[t])
            elseif t == "Base.SCP_1025_Book" then
                context:addOption(getText("ContextMenu_SCP_1025_Read"), player, SCP.SCP1025.readPage)
            elseif t == "Base.SCP_008_Sample" then
                context:addOption(getText("ContextMenu_SCP_008_Open"), player, SCP.SCP008.openSample, item)
            end
            return
        end
    end
end

Events.OnFillInventoryObjectContextMenu.Add(onFillInventoryMenu)
