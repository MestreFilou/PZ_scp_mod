--[[
    SCP-079 on the client: terminal (talk / overcharge), generators,
    alarms and messages.
]]

require "SCP_System"

local function state()
    local md = ModData.get("SCPFoundation")
    return (md and md.scp079) or { gens = {}, contained = false }
end

local function gensOnline()
    local n = 0
    for _, v in pairs(state().gens or {}) do if v then n = n + 1 end end
    return n
end

SCP.ClientCommands.SCP079Say = function(args)
    for _, p in ipairs(SCP.localPlayers()) do SCP.say(p, args.key, 120, 255, 120) end
end

SCP.ClientCommands.SCP079Alarm = function(args)
    local sq = getCell():getGridSquare(args.x, args.y, args.z)
    if sq then getSoundManager():PlayWorldSound("SCP_BreachAlarm", sq, 0, 60, 1, false) end
    SCP.ClientCommands.SCP079Say({ key = "UI_SCP_079_Alarm" })
end

SCP.ClientCommands.SCP079Generator = function(args)
    local sq = getCell():getGridSquare(args.x or 0, args.y or 0, args.z or 0)
    if sq then getSoundManager():PlayWorldSound("SCP_KeycardAccept", sq, 0, 30, 1, false) end
    for _, p in ipairs(SCP.localPlayers()) do
        SCP.say(p, "UI_SCP_079_GeneratorOn", 255, 220, 120, args.online or 0)
    end
end

local function findTagged(worldobjects, key)
    for _, o in ipairs(worldobjects) do
        local sq = o.getSquare and o:getSquare()
        if sq then
            local objs = sq:getObjects()
            for i = 0, objs:size() - 1 do
                local v = objs:get(i):getModData()[key]
                if v then return objs:get(i), v end
            end
        end
    end
    return nil
end

local function walkTo(player, obj)
    if SCP.dist(player, obj) > 2 then
        luautils.walkAdj(player, obj:getSquare())
        return false
    end
    return true
end

local function onTalk(player, obj)
    if not walkTo(player, obj) then return end
    if state().contained then
        SCP.say(player, "UI_SCP_079_Silent", 160, 160, 160)
    else
        SCP.say(player, "UI_SCP_079_Talk" .. (ZombRand(6) + 1), 120, 255, 120)
    end
end

local function onOvercharge(player, obj)
    if not walkTo(player, obj) then return end
    SCP.sendToServer(player, "SCP079Overcharge", {})
end

local function onGenerator(player, obj, index)
    if not walkTo(player, obj) then return end
    local sq = obj:getSquare()
    SCP.sendToServer(player, "SCP079Generator", { index = index, x = sq:getX(), y = sq:getY(), z = sq:getZ() })
end

local function onFillWorldMenu(playerNum, context, worldobjects, test)
    local player = getSpecificPlayer(playerNum)
    local term = findTagged(worldobjects, "SCP079_Terminal")
    if term then
        if test then return true end
        context:addOption(getText("ContextMenu_SCP_079_Talk"), player, onTalk, term)
        if not state().contained then
            local opt = context:addOption(getText("ContextMenu_SCP_079_Overcharge"), player, onOvercharge, term)
            if gensOnline() < 3 then
                opt.notAvailable = true
                local tip = ISWorldObjectContextMenu.addToolTip and ISWorldObjectContextMenu.addToolTip()
                if tip then
                    tip.description = getText("UI_SCP_079_NeedGenerators", gensOnline())
                    opt.toolTip = tip
                end
            end
        end
    end
    local gen, index = findTagged(worldobjects, "SCP079_Generator")
    if gen then
        if test then return true end
        local on = (state().gens or {})[index]
        local opt = context:addOption(getText("ContextMenu_SCP_079_StartGenerator", index), player, onGenerator, gen, index)
        if on or state().contained then opt.notAvailable = true end
    end
end

Events.OnFillWorldObjectContextMenu.Add(onFillWorldMenu)
