--[[
    Gas mask filters. The mask stores its filter charge (0 to 1) in its
    mod data. The charge drains while the mask is worn.
]]

require "SCP_System"

SCP.GasMask = SCP.GasMask or {}

function SCP.GasMask.getDrainableLevel(item)
    if item.getCurrentUsesFloat then
        local ok, v = pcall(item.getCurrentUsesFloat, item)
        if ok and v then return v end
    end
    if item.getUsedDelta then return item:getUsedDelta() end
    return 1
end

function SCP.GasMask.setDrainableLevel(item, value)
    if item.setCurrentUsesFloat then
        if pcall(item.setCurrentUsesFloat, item, value) then return end
    end
    if item.setUsedDelta then item:setUsedDelta(value) end
end

function SCP.GasMask.insertFilter(player, mask, filter)
    local level = SCP.GasMask.getDrainableLevel(filter)
    SCP.GasMask.removeFilter(player, mask)
    mask:getModData().SCP_Filter = level
    filter:getContainer():Remove(filter)
    player:playSound("PutItemInBag")
end

function SCP.GasMask.removeFilter(player, mask)
    local md = mask:getModData()
    local level = md.SCP_Filter
    if not level then return end
    md.SCP_Filter = nil
    if level > 0.01 then
        local filter = player:getInventory():AddItem("Base.SCP_GasFilter")
        if filter then SCP.GasMask.setDrainableLevel(filter, level) end
    end
end

local function drain()
    local perMinute = 1 / (math.max(1, SCP.opt("GasFilterHours")) * 60)
    for _, player in ipairs(SCP.localPlayers()) do
        local mask = SCP.getWorn(player, "Base.SCP_GasMask")
        if mask then
            local md = mask:getModData()
            if md.SCP_Filter and md.SCP_Filter > 0 then
                md.SCP_Filter = math.max(0, md.SCP_Filter - perMinute)
                if md.SCP_Filter == 0 then
                    SCP.say(player, "UI_SCP_FilterEmpty", 255, 180, 60)
                end
            end
        end
    end
end

Events.EveryOneMinute.Add(drain)
