--[[
    Alpha Warhead: control panel menu, countdown messages, detonation.
]]

require "SCP_System"
require "SCP_Facility_Layout"

local function state()
    local md = ModData.get("SCPFoundation")
    return (md and md.warhead) or { armed = false }
end

SCP.ClientCommands.WarheadCountdown = function(args)
    for _, p in ipairs(SCP.localPlayers()) do
        SCP.say(p, "UI_SCP_Warhead_Countdown", 255, 60, 60, args.minutes)
        p:playSound("SCP_BreachVoice")
    end
end

SCP.ClientCommands.WarheadDetonated = function(args)
    for _, p in ipairs(SCP.localPlayers()) do
        if SCP.Facility.levelAt(p:getX(), p:getY(), p:getZ()) then
            SCP.killPlayer(p, nil, nil)
        else
            SCP.say(p, "UI_SCP_Warhead_Felt", 255, 200, 120)
        end
    end
end

local function findPanel(worldobjects)
    for _, o in ipairs(worldobjects) do
        local sq = o.getSquare and o:getSquare()
        if sq then
            local objs = sq:getObjects()
            for i = 0, objs:size() - 1 do
                if objs:get(i):getModData().SCP_Warhead then return objs:get(i) end
            end
        end
    end
    return nil
end

Events.OnFillWorldObjectContextMenu.Add(function(playerNum, context, worldobjects, test)
    local panel = findPanel(worldobjects)
    if not panel then return end
    if test then return true end
    local player = getSpecificPlayer(playerNum)
    local md = ModData.get("SCPFoundation")
    if md and md.facility and md.facility.destroyed then return end
    local function act(p, cmd)
        if SCP.dist(p, panel) > 2 then luautils.walkAdj(p, panel:getSquare()) return end
        SCP.sendToServer(p, cmd, {})
    end
    if state().armed then
        context:addOption(getText("ContextMenu_SCP_Warhead_Cancel"), player, act, "WarheadCancel")
    else
        local opt = context:addOption(getText("ContextMenu_SCP_Warhead_Arm"), player, act, "WarheadArm")
        if SCP.keycardLevel(player) < 5 then opt.notAvailable = true end
    end
end)
