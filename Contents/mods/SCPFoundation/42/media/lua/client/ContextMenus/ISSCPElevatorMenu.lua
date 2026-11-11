--[[
    Elevators between the zones of the SCP site (and Gate A to the surface).
    Right click the elevator tile -> pick a destination.
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

-- Every place this elevator can go: { label, x, y, z }
local function destinations(info)
    local o = F.origin()
    if not o then return {} end
    local list = {}
    local top = F.Levels[1]
    if info.level == "SURFACE" then
        local x, y = F.findElevator(top, "0")
        if x then list[#list + 1] = { label = top.id, x = o.x + x, y = o.y + y, z = o.z + top.depth } end
        return list
    end
    for _, lv in ipairs(F.Levels) do
        if lv.id ~= info.level then
            local x, y = F.findElevator(lv, info.link)
            if x then list[#list + 1] = { label = lv.id, x = o.x + x, y = o.y + y, z = o.z + lv.depth } end
        end
    end
    if info.link == "0" and info.level == top.id then
        list[#list + 1] = { label = "SURFACE", x = o.x, y = o.y, z = 0 }
    end
    return list
end

local function travel(player, dest)
    player:playSound("SCP_KeycardAccept")
    local sq = getCell():getOrCreateGridSquare(dest.x, dest.y, dest.z)
    -- Step off the elevator tile on arrival.
    SCP.teleport(player, dest.x + 1.5, dest.y + 0.5, dest.z)
    SCP.say(player, LEVEL_TEXT[dest.label] or dest.label, 200, 220, 255)
end

local function onFillWorldMenu(playerNum, context, worldobjects, test)
    local obj, info = findElevatorObject(worldobjects)
    if not obj then return end
    if test then return true end
    local player = getSpecificPlayer(playerNum)
    local dests = destinations(info)
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

Events.OnFillWorldObjectContextMenu.Add(onFillWorldMenu)
