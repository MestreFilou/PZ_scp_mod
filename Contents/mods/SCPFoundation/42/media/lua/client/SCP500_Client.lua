--[[
    SCP-500: "Take a pill" option and its timed action.
]]

require "SCP_System"
require "SCP_500_Logic"
require "TimedActions/ISBaseTimedAction"

ISTakeSCP500Action = ISBaseTimedAction:derive("ISTakeSCP500Action")

function ISTakeSCP500Action:isValid()
    return self.character:getInventory():contains(self.item)
end

function ISTakeSCP500Action:start()
    self:setActionAnim("TakePills")
    self:setOverrideHandModels(nil, self.item)
end

function ISTakeSCP500Action:update()
    self.item:setJobDelta(self:getJobDelta())
end

function ISTakeSCP500Action:stop()
    self.item:setJobDelta(0)
    ISBaseTimedAction.stop(self)
end

function ISTakeSCP500Action:applyEffect()
    if self.applied then return end
    self.applied = true
    SCP.SCP500.cure(self.character)
    if self.item.UseAndSync then self.item:UseAndSync() else self.item:Use() end
    self.character:playSound("SCP_PillSwallow")
    SCP.say(self.character, "UI_SCP_500_Cured", 120, 255, 120)
end

function ISTakeSCP500Action:perform()
    self.item:setJobDelta(0)
    self:applyEffect()
    ISBaseTimedAction.perform(self)
end

-- Build 42 runs complete() on the authoritative side.
function ISTakeSCP500Action:complete()
    self:applyEffect()
    return true
end

function ISTakeSCP500Action:getDuration()
    return 90
end

function ISTakeSCP500Action:new(character, item)
    local o = ISBaseTimedAction.new(self, character)
    o.item = item
    o.stopOnWalk = false
    o.stopOnRun = true
    o.maxTime = o:getDuration()
    return o
end

local function onTake(item, playerNum)
    local player = getSpecificPlayer(playerNum)
    ISInventoryPaneContextMenu.transferIfNeeded(player, item)
    ISTimedActionQueue.add(ISTakeSCP500Action:new(player, item))
end

local function onFillInventoryMenu(playerNum, context, items)
    local list = ISInventoryPane.getActualItems and ISInventoryPane.getActualItems(items) or items
    for _, entry in ipairs(list) do
        local item = entry
        if type(entry) == "table" and entry.items then item = entry.items[1] end
        if item and item.getFullType and item:getFullType() == "Base.SCP_500_Pill" then
            context:addOption(getText("ContextMenu_SCP_TakePill"), item, onTake, playerNum)
            return
        end
    end
end

Events.OnFillInventoryObjectContextMenu.Add(onFillInventoryMenu)
