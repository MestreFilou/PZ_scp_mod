--[[
    Femur Breaker console (SCP-106 re-containment): context menu and feedback.
]]

require "SCP_System"

local function findConsole(worldobjects)
    for _, o in ipairs(worldobjects) do
        local sq = o.getSquare and o:getSquare()
        if sq then
            local objs = sq:getObjects()
            for i = 0, objs:size() - 1 do
                if objs:get(i):getModData().SCP106_Breaker then return objs:get(i) end
            end
        end
    end
    return nil
end

local function act(player, console, cmd)
    if SCP.dist(player, console) > 2 then
        luautils.walkAdj(player, console:getSquare())
        return
    end
    local sq = console:getSquare()
    SCP.sendToServer(player, cmd, { x = sq:getX(), y = sq:getY(), z = sq:getZ() })
end

SCP.on("OnFillWorldObjectContextMenu", function(playerNum, context, worldobjects, test)
    local console = findConsole(worldobjects)
    if not console then return end
    if test then return true end
    local player = getSpecificPlayer(playerNum)
    local st = SCP.SCP106 and SCP.SCP106.state and SCP.SCP106.state()
    local root = context:addOption(getText("ContextMenu_SCP_106_Console"))
    local menu = ISContextMenu:getNew(context)
    context:addSubMenu(root, menu)
    local opt = menu:addOption(getText("ContextMenu_SCP_106_FemurBreaker"), player, act, console, "SCP106FemurBreak")
    if SCP.keycardLevel(player) < 5 or (st and st.lure) then opt.notAvailable = true end
    local recall = menu:addOption(getText("ContextMenu_SCP_106_Recall"), player, act, console, "SCP106Recall")
    if not (st and st.lure and st.feeding == st.lure.id) then recall.notAvailable = true end
end)

SCP.ClientCommands.SCP106Breaker = function(args)
    local sq = getCell():getGridSquare(args.x, args.y, args.z)
    local played = sq and args.sound and pcall(sq.playSound, sq, args.sound)
    if args.sound and not played then
        local p = getPlayer()
        if p then p:playSound(args.sound) end
    end
    for _, p in ipairs(SCP.localPlayers()) do
        if args.key then SCP.say(p, args.key, 200, 160, 255) end
    end
end
