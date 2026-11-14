--[[
    Keycard door context menu:
      - players: "Swipe keycard" on a secured door
      - admins / debug: set the access level of any door
]]

require "SCP_System"
require "SCP_Doors"
require "TimedActions/ISBaseTimedAction"

ISKeycardSwipeAction = ISBaseTimedAction:derive("ISKeycardSwipeAction")

function ISKeycardSwipeAction:isValid()
    return self.door and self.door:getSquare() ~= nil
end

function ISKeycardSwipeAction:waitToStart()
    self.character:faceThisObject(self.door)
    return self.character:shouldBeTurning()
end

function ISKeycardSwipeAction:start()
    self:setActionAnim("Loot")
end

function ISKeycardSwipeAction:perform()
    local sq = self.door:getSquare()
    SCP.sendToServer(self.character, "KeycardUnlock", { x = sq:getX(), y = sq:getY(), z = sq:getZ() })
    ISBaseTimedAction.perform(self)
end

function ISKeycardSwipeAction:complete()
    return true
end

function ISKeycardSwipeAction:getDuration()
    return 25
end

function ISKeycardSwipeAction:new(character, door)
    local o = ISBaseTimedAction.new(self, character)
    o.door = door
    o.maxTime = o:getDuration()
    return o
end

-- Answer from the server: open the door, or refuse.
SCP.ClientCommands.KeycardResult = function(args)
    local player = getPlayer()
    if not player then return end
    if args.ok then
        player:playSound("SCP_KeycardAccept")
        local door = SCP.Doors.find(args.x, args.y, args.z)
        if door and not SCP.Doors.isOpen(door) then door:ToggleDoor(player) end
        SCP.say(player, "UI_SCP_AccessGranted", 120, 255, 120)
    else
        player:playSound("SCP_KeycardDeny")
        SCP.say(player, "UI_SCP_AccessDenied", 255, 80, 80, args.need or 0)
    end
end

local function onSwipe(player, door)
    if luautils.walkAdjWindowOrDoor then
        luautils.walkAdjWindowOrDoor(player, door:getSquare(), door)
    else
        luautils.walkAdj(player, door:getSquare())
    end
    ISTimedActionQueue.add(ISKeycardSwipeAction:new(player, door))
end

local function onSetLevel(player, door, level)
    local sq = door:getSquare()
    SCP.sendToServer(player, "SetDoorLevel", { x = sq:getX(), y = sq:getY(), z = sq:getZ(), level = level })
end

local function findDoor(worldobjects)
    for _, obj in ipairs(worldobjects) do
        if SCP.Doors.isDoor(obj) then return obj end
        local sq = obj.getSquare and obj:getSquare()
        if sq then
            local objs = sq:getObjects()
            for i = 0, objs:size() - 1 do
                if SCP.Doors.isDoor(objs:get(i)) then return objs:get(i) end
            end
        end
    end
    return nil
end

local function onFillWorldMenu(playerNum, context, worldobjects, test)
    local door = findDoor(worldobjects)
    if not door then return end
    if test then return true end
    local player = getSpecificPlayer(playerNum)
    local level = SCP.Doors.getLevel(door)

    if level > 0 then
        local have = SCP.keycardLevel(player)
        local opt = context:addOption(getText("ContextMenu_SCP_SwipeCard", level), player, onSwipe, door)
        local tip = ISWorldObjectContextMenu.addToolTip and ISWorldObjectContextMenu.addToolTip()
        if tip then
            tip.description = getText("UI_SCP_YourCard", have)
            opt.toolTip = tip
        end
        if have == 0 then opt.notAvailable = true end
    end

    if SCP.isAdmin(player) then
        local parent = context:addOption(getText("ContextMenu_SCP_DoorAdmin"))
        local sub = ISContextMenu:getNew(context)
        context:addSubMenu(parent, sub)
        sub:addOption(getText("ContextMenu_SCP_DoorUnsecure"), player, onSetLevel, door, 0)
        for l = 1, SCP.MaxKeyLevel do
            sub:addOption(getText("ContextMenu_SCP_DoorLevel", l), player, onSetLevel, door, l)
        end
    end
end

Events.OnFillWorldObjectContextMenu.Add(onFillWorldMenu)
