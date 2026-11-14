--[[
    SCP-106 re-containment: the Femur Breaker (Heavy Containment, level 5).
      FemurBreak : needs a level 5 keycard and a body next to the console
                   (the sacrifice, consumed). Its screams lure every active
                   SCP-106 to the breaker for LURE_HOURS.
      Feeding    : sent by a client when 106 reaches the breaker.
      Recall     : magnetic recall from the console while 106 is feeding:
                   it goes back to its cell and stays asleep until the next breach.
    Movement itself is in shared/SCP_106_Logic.lua.
]]

require "SCP_System"

SCP.SCP106 = SCP.SCP106 or {}

local LURE_HOURS = 0.5          -- 30 in-game minutes
local SACRIFICE_RADIUS = 3

local function now() return getGameTime():getWorldAgeHours() end

local function state()
    local w = SCP.world()
    w.scp106 = w.scp106 or {}
    return w.scp106
end

local function sync()
    if isServer() then ModData.transmit("SCPFoundation") end
end

local function notify(player, key)
    SCP.sendToClient(player, "Notify", { key = key })
end

-- Removes one corpse near (x, y, z). Returns true if one was found.
local function takeSacrifice(x, y, z)
    for dx = -SACRIFICE_RADIUS, SACRIFICE_RADIUS do
        for dy = -SACRIFICE_RADIUS, SACRIFICE_RADIUS do
            local sq = getCell():getGridSquare(x + dx, y + dy, z)
            local bodies = sq and sq:getDeadBodys()
            if bodies and bodies:size() > 0 then
                local body = bodies:get(0)
                if pcall(function() sq:removeCorpse(body, false) end) then return true end
            end
        end
    end
    return false
end

SCP.ServerCommands.SCP106FemurBreak = function(player, args)
    local st = state()
    if st.lure then return notify(player, "UI_SCP_106_AlreadyLured") end
    if SCP.keycardLevel(player) < 5 then return notify(player, "UI_SCP_Warhead_NeedL5") end
    if not takeSacrifice(args.x, args.y, args.z) then return notify(player, "UI_SCP_106_NeedSacrifice") end
    st.lureCount = (st.lureCount or 0) + 1
    st.lure = { id = st.lureCount, x = args.x, y = args.y, z = args.z, untilH = now() + LURE_HOURS }
    st.feeding = nil
    sync()
    addSound(nil, args.x, args.y, args.z, 80, 80)
    SCP.sendToClients("SCP106Breaker", { x = args.x, y = args.y, z = args.z, sound = "SCP106_FemurBreaker", key = "UI_SCP_106_Lured" })
end

SCP.ServerCommands.SCP106Feeding = function(player, args)
    local st = state()
    if not st.lure or st.lure.id ~= args.id or st.feeding == args.id then return end
    st.feeding = args.id
    sync()
    SCP.sendToClients("Notify", { key = "UI_SCP_106_Feeding" })
end

SCP.ServerCommands.SCP106Recall = function(player, args)
    local st = state()
    if not st.lure or st.feeding ~= st.lure.id then return notify(player, "UI_SCP_106_NotLured") end
    st.recalledLure = st.lure.id
    st.recontainedAt = now()
    st.lure = nil
    st.feeding = nil
    sync()
    SCP.sendToClients("SCP106Breaker", { x = args.x, y = args.y, z = args.z, sound = "SCP106_Magnet", key = "UI_SCP_106_Recontained" })
end

-- The lure wears off: 106 goes back to hunting.
SCP.on("EveryOneMinute", function()
    if isClient() then return end
    local st = SCP.world().scp106
    if st and st.lure and now() > st.lure.untilH then
        st.lure = nil
        st.feeding = nil
        sync()
        SCP.sendToClients("Notify", { key = "UI_SCP_106_LureFailed" })
    end
end)
