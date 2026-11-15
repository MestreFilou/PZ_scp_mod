--[[
    Right click on a small anomaly in the inventory: drink SCP-207, put on
    SCP-268, take a candy from SCP-330, drink from SCP-109, open SCP-458.
    One timed action for all of them; the effect is in SCP_Anomalies_Logic.lua.
]]

require "SCP_System"
require "SCP_Anomalies_Logic"
require "TimedActions/ISBaseTimedAction"

ISUseSCPAnomalyAction = ISBaseTimedAction:derive("ISUseSCPAnomalyAction")

function ISUseSCPAnomalyAction:isValid()
    return self.character:getInventory():contains(self.item)
end

function ISUseSCPAnomalyAction:start()
    local a = self.info
    if a.anim then
        -- Drink / Eat are enum values in 42 (CharacterActionAnims), the others plain names
        local anim = CharacterActionAnims and CharacterActionAnims[a.anim] or a.anim
        pcall(self.setActionAnim, self, anim)
    end
    if a.anim == "Eat" or a.anim == "Drink" then
        pcall(self.setOverrideHandModels, self, nil, self.item)
    end
    if a.sound then self.character:playSound(a.sound) end
end

function ISUseSCPAnomalyAction:update()
    self.item:setJobDelta(self:getJobDelta())
end

function ISUseSCPAnomalyAction:stop()
    self.item:setJobDelta(0)
    ISBaseTimedAction.stop(self)
end

function ISUseSCPAnomalyAction:applyEffect()
    if self.applied then return end
    self.applied = true
    SCP.Anomalies.use(self.character, self.item)
end

function ISUseSCPAnomalyAction:perform()
    self.item:setJobDelta(0)
    if not isClient() then self:applyEffect() end
    ISBaseTimedAction.perform(self)
end

-- Build 42 runs complete() on the authoritative side.
function ISUseSCPAnomalyAction:complete()
    self:applyEffect()
    return true
end

function ISUseSCPAnomalyAction:getDuration()
    return self.info.time or 60
end

function ISUseSCPAnomalyAction:new(character, item, info)
    local o = ISBaseTimedAction.new(self, character)
    o.item = item
    o.info = info
    o.stopOnWalk = false
    o.stopOnRun = true
    o.maxTime = o:getDuration()
    return o
end

local function onUse(item, playerNum, info)
    local player = getSpecificPlayer(playerNum)
    ISInventoryPaneContextMenu.transferIfNeeded(player, item)
    ISTimedActionQueue.add(ISUseSCPAnomalyAction:new(player, item, info))
end

local function onFillInventoryMenu(playerNum, context, items)
    local list = ISInventoryPane.getActualItems and ISInventoryPane.getActualItems(items) or items
    for _, entry in ipairs(list) do
        local item = entry
        if type(entry) == "table" and entry.items then item = entry.items[1] end
        local info = item and item.getFullType and SCP.Anomalies.ACTIONS[item:getFullType()]
        if info then
            local option = context:addOption(getText(info.text), item, onUse, playerNum, info)
            if info.needsBattery then
                local player = getSpecificPlayer(playerNum)
                local charge = SCP.Anomalies.maulCharge(item)
                local tip = ISToolTip:new()
                tip:initialise()
                tip.description = getText("UI_SCP_ShockMaul_Charge", charge, SCP.Anomalies.MAUL_MAX)
                option.toolTip = tip
                if charge >= SCP.Anomalies.MAUL_MAX or not SCP.Anomalies.batteryWithPower(player) then
                    option.notAvailable = true
                end
            end
            return
        end
    end
end

SCP.on("OnFillInventoryObjectContextMenu", onFillInventoryMenu)
