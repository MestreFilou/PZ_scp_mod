--[[
    Keycard doors:
      - press the Interact key (E) in front of a secured door, or right
        click it -> "Swipe keycard": the character takes their best card in
        hand, swipes it on the reader, and the door opens if the level is enough;
      - admins / debug: set the access level of any door (right click).
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

-- The best keycard the character carries (the item), or nil.
local function bestCard(player)
    local inv = player:getInventory()
    local key = inv:getFirstTypeRecurse("SCP_005_Key")
    if key then return key end
    for level = SCP.MaxKeyLevel, 1, -1 do
        local item = inv:getFirstTypeRecurse("SCP_Keycard_L" .. level)
        if item then return item end
    end
    return nil
end

-- Card in the hand for the swipe; what was there comes back afterwards.
function ISKeycardSwipeAction:takeCard()
    local card = bestCard(self.character)
    if not card then return end
    self.previous = self.character:getPrimaryHandItem()
    local inv = self.character:getInventory()
    local from = card:getContainer()
    if from and from ~= inv then
        pcall(function() from:Remove(card); inv:AddItem(card) end)
    end
    pcall(self.character.setPrimaryHandItem, self.character, card)
    self.card = card
end

function ISKeycardSwipeAction:putCardBack()
    if not self.card then return end
    if self.character:getPrimaryHandItem() == self.card then
        pcall(self.character.setPrimaryHandItem, self.character, self.previous)
    end
    self.card = nil
end

function ISKeycardSwipeAction:start()
    self:takeCard()
    self:setActionAnim("Loot")
    self:setAnimVariable("LootPosition", "High")
end

function ISKeycardSwipeAction:stop()
    self:putCardBack()
    ISBaseTimedAction.stop(self)
end

function ISKeycardSwipeAction:perform()
    local sq = self.door:getSquare()
    SCP.sendToServer(self.character, "KeycardUnlock", { x = sq:getX(), y = sq:getY(), z = sq:getZ() })
    self:putCardBack()
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

SCP.on("OnFillWorldObjectContextMenu", onFillWorldMenu)

------------------------------------------------------------------------
-- Interact key (E by default) in front of a secured door
------------------------------------------------------------------------

local function securedDoorOn(sq)
    if not sq then return nil end
    local objs = sq:getSpecialObjects()
    for i = 0, objs:size() - 1 do
        local o = objs:get(i)
        if SCP.Doors.isDoor(o) and SCP.Doors.getLevel(o) > 0 and not SCP.Doors.isOpen(o) then return o end
    end
    return nil
end

-- The secured door the player faces, at most one tile away.
local function doorInFront(player)
    local sq = player:getCurrentSquare() or player:getSquare()
    if not sq then return nil end
    local x, y, z = sq:getX(), sq:getY(), sq:getZ()
    local dir = player:getDir()
    local dx, dy = 0, 0
    if dir and dir.dx and dir.dy then
        local ok1, a = pcall(dir.dx, dir)
        local ok2, b = pcall(dir.dy, dir)
        if ok1 and ok2 and a and b then dx, dy = a, b end
    end
    local cell = getCell()
    local candidates = { sq }
    if dx ~= 0 or dy ~= 0 then
        candidates[#candidates + 1] = cell:getGridSquare(x + dx, y + dy, z)
        candidates[#candidates + 1] = cell:getGridSquare(x + dx, y, z)
        candidates[#candidates + 1] = cell:getGridSquare(x, y + dy, z)
    else
        for _, d in ipairs({ { 1, 0 }, { 0, 1 }, { -1, 0 }, { 0, -1 } }) do
            candidates[#candidates + 1] = cell:getGridSquare(x + d[1], y + d[2], z)
        end
    end
    local best, bestDist = nil, 99
    for _, c in ipairs(candidates) do
        local door = securedDoorOn(c)
        if door then
            local dist = SCP.dist(player, door)
            if dist < bestDist then best, bestDist = door, dist end
        end
    end
    if best and bestDist <= 1.8 then return best end
    return nil
end

-- Events.OnContextKey fires when the Interact key (E) is pressed.
local function onContextKey(player)
    if not player or player:isDead() or player:getVehicle() then return end
    if player.hasTimedActions and player:hasTimedActions() then return end
    local door = doorInFront(player)
    if not door then return end
    if SCP.keycardLevel(player) == 0 then
        player:playSound("SCP_KeycardDeny")
        SCP.say(player, "UI_SCP_AccessDenied", 255, 80, 80, SCP.Doors.getLevel(door))
        return
    end
    ISTimedActionQueue.add(ISKeycardSwipeAction:new(player, door))
end

SCP.on("OnContextKey", onContextKey)
