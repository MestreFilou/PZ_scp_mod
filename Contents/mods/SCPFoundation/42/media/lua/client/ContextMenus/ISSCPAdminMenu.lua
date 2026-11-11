--[[
    Admin / debug tools (right click on the ground):
      spawn an SCP, place containment points, start or stop a breach.
]]

require "SCP_System"
require "SCP_Facility_Layout"

local SPAWNABLE = {
    { SCP.Types.SCP173, "ContextMenu_SCP_173" },
    { SCP.Types.SCP096, "ContextMenu_SCP_096" },
    { SCP.Types.SCP106, "ContextMenu_SCP_106" },
    { SCP.Types.SCP035, "ContextMenu_SCP_035" },
    { SCP.Types.SCP049, "ContextMenu_SCP_049" },
    { SCP.Types.SCP939, "ContextMenu_SCP_939" },
    { SCP.Types.SCP966, "ContextMenu_SCP_966" },
    { SCP.Types.GUARD,  "ContextMenu_SCP_Guard" },
}

local function clickedSquare(worldobjects)
    for _, o in ipairs(worldobjects) do
        local sq = o.getSquare and o:getSquare()
        if sq then return sq end
    end
    return nil
end

local function send(player, cmd, args) SCP.sendToServer(player, cmd, args) end

local function onFillWorldMenu(playerNum, context, worldobjects, test)
    local player = getSpecificPlayer(playerNum)
    if not SCP.isAdmin(player) then return end
    local sq = clickedSquare(worldobjects)
    if not sq then return end
    if test then return true end
    local pos = { x = sq:getX(), y = sq:getY(), z = sq:getZ() }

    local root = context:addOption(getText("ContextMenu_SCP_Admin"))
    local menu = ISContextMenu:getNew(context)
    context:addSubMenu(root, menu)

    local spawnOpt = menu:addOption(getText("ContextMenu_SCP_SpawnHere"))
    local spawnMenu = ISContextMenu:getNew(menu)
    menu:addSubMenu(spawnOpt, spawnMenu)
    for _, e in ipairs(SPAWNABLE) do
        spawnMenu:addOption(getText(e[2]), player, send, "Spawn", { type = e[1], x = pos.x, y = pos.y, z = pos.z })
    end

    local pointOpt = menu:addOption(getText("ContextMenu_SCP_AddPoint"))
    local pointMenu = ISContextMenu:getNew(menu)
    menu:addSubMenu(pointOpt, pointMenu)
    for _, e in ipairs(SPAWNABLE) do
        pointMenu:addOption(getText(e[2]), player, send, "AddPoint", { type = e[1], x = pos.x, y = pos.y, z = pos.z })
    end
    menu:addOption(getText("ContextMenu_SCP_ClearPoints"), player, send, "ClearPoints",
        { x = pos.x, y = pos.y, z = pos.z, radius = 10 })

    if not SCP.Facility or not SCP.Facility.origin() then
        menu:addOption(getText("ContextMenu_SCP_PlaceFacility"), player, send, "PlaceFacility", { x = pos.x, y = pos.y })
    end

    menu:addOption(getText("ContextMenu_SCP_StartBreach"), player, send, "StartBreach", {})
    menu:addOption(getText("ContextMenu_SCP_StopBreach"), player, send, "StopBreach", {})

    menu:addOption(getText("ContextMenu_SCP_GiveKit"), player, function(p)
        local inv = p:getInventory()
        for l = 1, SCP.MaxKeyLevel do inv:AddItem("Base.SCP_Keycard_L" .. l) end
        for _, t in ipairs({ "SCP_500_Pill", "SCP_GasMask", "SCP_GasFilter", "SCP_Hazmat_Suit",
            "SCP_MTF_Helmet", "SCP_MTF_Vest", "SCP_MTF_Uniform", "SCP_ClassD_Jumpsuit", "SCP_035_Mask",
            "SCP_714_Ring", "SCP_NVG", "SCP_1025_Book", "SCP_008_Sample", "SCP_Document_008" }) do
            inv:AddItem("Base." .. t)
        end
    end)
end

Events.OnFillWorldObjectContextMenu.Add(onFillWorldMenu)
