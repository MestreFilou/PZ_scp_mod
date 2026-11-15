--[[
    The Gate A lift, between the Entrance Zone and the bunker on the surface.
    Right click the lift platform -> pick the destination.
]]

require "SCP_System"
require "SCP_Facility_Layout"

local F = SCP.Facility

local LEVEL_TEXT = { SURFACE = "UI_SCP_Zone_Surface", EZ = "UI_SCP_Zone_EZ", HCZ = "UI_SCP_Zone_HCZ", LCZ = "UI_SCP_Zone_LCZ" }

local function findElevatorObject(worldobjects)
    for _, o in ipairs(worldobjects) do
        local sq = o.getSquare and o:getSquare()
        if sq then
            local objs = sq:getObjects()
            for i = 0, objs:size() - 1 do
                local md = objs:get(i):getModData()
                if md.SCP_Elevator then return objs:get(i), md.SCP_Elevator end
            end
        end
    end
    return nil
end

local function travel(player, dest)
    player:playSound("SCP_KeycardAccept")
    getCell():getOrCreateGridSquare(dest.x, dest.y, dest.z)
    SCP.teleport(player, dest.x + 0.5, dest.y + 0.5, dest.z)
    SCP.say(player, LEVEL_TEXT[dest.label] or dest.label, 200, 220, 255)
end

local function onFillWorldMenu(playerNum, context, worldobjects, test)
    local obj, info = findElevatorObject(worldobjects)
    if not obj then return end
    if test then return true end
    local player = getSpecificPlayer(playerNum)
    local dests = F.liftDestinations(info)
    if #dests == 0 then return end
    local parent = context:addOption(getText("ContextMenu_SCP_Elevator"))
    local sub = ISContextMenu:getNew(context)
    context:addSubMenu(parent, sub)
    for _, d in ipairs(dests) do
        sub:addOption(getText(LEVEL_TEXT[d.label] or d.label), player, function(p)
            if SCP.dist(p, obj) > 2.5 then
                luautils.walkAdj(p, obj:getSquare())
                return
            end
            travel(p, d)
        end)
    end
end

SCP.on("OnFillWorldObjectContextMenu", onFillWorldMenu)
