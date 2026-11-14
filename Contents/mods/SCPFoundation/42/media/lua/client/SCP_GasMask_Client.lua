--[[
    Gas mask: insert / remove filter options and a tooltip line.
]]

require "SCP_System"
require "SCP_GasMask_Logic"

local function firstItem(entry)
    if type(entry) == "table" and entry.items then return entry.items[1] end
    return entry
end

local function onInsert(player, mask, filter)
    SCP.GasMask.insertFilter(player, mask, filter)
end

local function onRemove(player, mask)
    SCP.GasMask.removeFilter(player, mask)
end

local function onFillInventoryMenu(playerNum, context, items)
    local player = getSpecificPlayer(playerNum)
    for _, entry in ipairs(items) do
        local item = firstItem(entry)
        if item and item.getFullType and item:getFullType() == "Base.SCP_GasMask" then
            local filters = player:getInventory():getAllTypeRecurse("Base.SCP_GasFilter")
            if filters and filters:size() > 0 then
                context:addOption(getText("ContextMenu_SCP_InsertFilter"), player, onInsert, item, filters:get(0))
            end
            local charge = item:getModData().SCP_Filter
            if charge then
                local opt = context:addOption(getText("ContextMenu_SCP_RemoveFilter"), player, onRemove, item)
                local tip = ISInventoryPaneContextMenu.addToolTip and ISInventoryPaneContextMenu.addToolTip()
                if tip then
                    tip.description = getText("UI_SCP_FilterCharge", math.floor(charge * 100))
                    opt.toolTip = tip
                end
            else
                context:addOption(getText("UI_SCP_NoFilter"), nil, nil).notAvailable = true
            end
            return
        end
    end
end

Events.OnFillInventoryObjectContextMenu.Add(onFillInventoryMenu)
