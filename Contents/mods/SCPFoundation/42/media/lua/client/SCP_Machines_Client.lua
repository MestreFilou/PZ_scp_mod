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

-- The machine sits between its two booths on the same row:
-- intake booth to the west, output booth to the east.
local function findParts(obj)
    local sq = obj:getSquare()
    local parts = {}
    for dx = -2, 2 do
        local s = getCell():getGridSquare(sq:getX() + dx, sq:getY(), sq:getZ())
        if s then
            local objs = s:getObjects()
            for i = 0, objs:size() - 1 do
                local o = objs:get(i)
                local md = o:getModData()
                if md.SCP914_Machine then parts.machine = o end
                if md.SCP914_Booth == "in" then parts.intake = o:getContainer() end
                if md.SCP914_Booth == "out" then parts.output = o:getContainer() end
            end
        end
    end
    return parts
end

local function removeFrom(container, item)
    container:DoRemoveItem(item)
    if isClient() and sendRemoveItemFromContainer then pcall(sendRemoveItemFromContainer, container, item) end
end

local function addTo(container, itemOrType)
    local ok, item = pcall(container.AddItem, container, itemOrType)
    if ok and item and isClient() and sendAddItemToContainer then pcall(sendAddItemToContainer, container, item) end
    return ok and item or nil
end

local running = {}   -- machine key -> { parts, setting, player, doneAt }

local function machineKey(m)
    local sq = m:getSquare()
    return sq:getX() .. "," .. sq:getY() .. "," .. sq:getZ()
end

local function finish914(job)
    local intake, output = job.parts.intake, job.parts.output
    local items = intake:getItems()
    local list = {}
    for i = 0, items:size() - 1 do list[#list + 1] = items:get(i) end
    local lastKey, count = nil, 0
    for _, item in ipairs(list) do
        local res = SCP.SCP914.refine(item, job.setting)
        removeFrom(intake, item)
        if res.keep then addTo(output, item) end
        for _, o in ipairs(res.out or {}) do
            for _ = 1, o[2] or 1 do addTo(output, o[1]) end
        end
        lastKey, count = res.key, count + 1
    end
    if job.player and not job.player:isDead() then
        if count == 1 then
            SCP.say(job.player, lastKey, 220, 200, 140)
        else
            SCP.say(job.player, "UI_SCP_914_Done", 220, 200, 140, count)
        end
    end
end

SCP.on("OnTick", function()
    local t = getTimestampMs()
    for key, job in pairs(running) do
        if t >= job.doneAt then
            running[key] = nil
            finish914(job)
        end
    end
end)

local function on914(player, machine, setting)
    if not near(player, machine) then return end
    local parts = findParts(machine)
    if not parts.intake or not parts.output then
        SCP.say(player, "UI_SCP_914_NoBooths", 220, 200, 140)
        return
    end
    local key = machineKey(machine)
    if running[key] then
        SCP.say(player, "UI_SCP_914_Busy", 220, 200, 140)
        return
    end
    if parts.intake:getItems():size() == 0 then
        SCP.say(player, "UI_SCP_914_Empty", 220, 200, 140)
        return
    end
    machine:getSquare():playSound("SCP914_Clockwork")
    running[key] = { parts = parts, setting = setting, player = player, doneAt = getTimestampMs() + SCP.SCP914.RUN_MS }
    SCP.say(player, "UI_SCP_914_Running", 220, 200, 140)
end

local function fill914(context, player, obj)
    local parts = findParts(obj)
    local machine = parts.machine or obj
    local root = context:addOption(getText("ContextMenu_SCP_914_Use"))
    local menu = ISContextMenu:getNew(context)
    context:addSubMenu(root, menu)
    for _, setting in ipairs(SCP.SCP914.SETTINGS) do
        local opt = menu:addOption(getText("ContextMenu_SCP_914_" .. setting), player, on914, machine, setting)
        opt.toolTip = ISToolTip:new()
        opt.toolTip:initialise()
        opt.toolTip:setName(getText("ContextMenu_SCP_914_" .. setting))
        opt.toolTip.description = getText("UI_SCP_914_Tip_" .. setting)
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
    local m914 = findTagged(worldobjects, "SCP914_Machine") or findTagged(worldobjects, "SCP914_Booth")
    local m294 = findTagged(worldobjects, "SCP294_Machine")
    if not m914 and not m294 then return end
    if test then return true end
    if m914 then fill914(context, player, m914) end
    if m294 then fill294(context, player, m294) end
end

SCP.on("OnFillWorldObjectContextMenu", onFillWorldMenu)

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

SCP.on("OnFillInventoryObjectContextMenu", onFillInventoryMenu)
