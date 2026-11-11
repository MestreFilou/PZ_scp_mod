--[[
    Alpha Warhead. From the control panel in the Entrance Zone (level 5
    keycard), it can be armed: after 30 in-game minutes, everything still
    inside the SCP site dies (players and zombies), SCP-079 goes silent and
    any breach ends. It can be cancelled from the same panel before then.
]]

require "SCP_System"
require "SCP_Facility_Layout"

SCP.Warhead = SCP.Warhead or {}
local W = SCP.Warhead
local F = SCP.Facility

W.MINUTES = 30

function W.state()
    local w = SCP.world()
    w.warhead = w.warhead or { armed = false }
    return w.warhead
end

local function sync() if isServer() then ModData.transmit("SCPFoundation") end end

SCP.ServerCommands.WarheadArm = function(player, args)
    local st = W.state()
    local world = SCP.world()
    if st.armed or (world.facility and world.facility.destroyed) then return end
    if SCP.keycardLevel(player) < 5 then
        SCP.sendToClient(player, "Notify", { key = "UI_SCP_Warhead_NeedL5" })
        return
    end
    st.armed = true
    st.minutesLeft = W.MINUTES
    sync()
    SCP.sendToClients("WarheadCountdown", { minutes = W.MINUTES })
end

SCP.ServerCommands.WarheadCancel = function(player, args)
    local st = W.state()
    if not st.armed then return end
    st.armed = false
    sync()
    SCP.sendToClients("Notify", { key = "UI_SCP_Warhead_Cancelled" })
end

local function detonate()
    local st = W.state()
    st.armed = false
    local world = SCP.world()
    world.facility = world.facility or {}
    world.facility.destroyed = true
    if SCP.SCP079 then SCP.SCP079.state().contained = true end
    if SCP.Breach and SCP.Breach.isActive() then SCP.Breach.stop() end

    -- Every zombie inside the site
    local zombies = getCell():getZombieList()
    for i = zombies:size() - 1, 0, -1 do
        local z = zombies:get(i)
        if F.levelAt(z:getX(), z:getY(), z:getZ()) then
            if z.Kill then pcall(z.Kill, z, nil) else z:setHealth(0) end
        end
    end
    sync()
    -- Players: each client kills its own players that are still inside.
    SCP.sendToClients("WarheadDetonated", {})
    local o = F.origin()
    if o then addSound(nil, o.x, o.y, 0, 300, 300) end
end

Events.EveryOneMinute.Add(function()
    if isClient() then return end
    local st = W.state()
    if not st.armed then return end
    st.minutesLeft = (st.minutesLeft or W.MINUTES) - 1
    if st.minutesLeft <= 0 then
        detonate()
    elseif st.minutesLeft % 5 == 0 or st.minutesLeft <= 3 then
        SCP.sendToClients("WarheadCountdown", { minutes = st.minutesLeft })
    end
end)
