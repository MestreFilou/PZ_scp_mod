--[[
    Starting occupations: Class-D, Foundation Scientist, MTF Guard.
    Each starts with its gear and, if an SCP site exists, inside it:
      Class-D  -> Class-D cells (Light Containment)
      Scientist -> research lab (Entrance Zone)
      MTF Guard -> security room (Entrance Zone)
    In single player, if no site exists yet, one is placed next to the
    spawn point.
]]

require "SCP_System"
require "SCP_Facility_Layout"

SCP.Professions = SCP.Professions or {}
local P = SCP.Professions

P.List = {
    scp_classd = {
        cost = 8,       -- positive = gives points (hard start)
        room = { "LCZ", "D" },
        wear = { "SCP_ClassD_Jumpsuit" },
        give = {},
        traits = {},
    },
    scp_scientist = {
        cost = 0,
        room = { "EZ", "H" },
        wear = { "SCP_Hazmat_Suit" },
        give = { "SCP_Keycard_L2", "SCP_Document_Containment", "SCP_Document_008", "Torch" },
        xp = { Doctor = 2, Electricity = 1 },
    },
    scp_mtf = {
        cost = -4,
        room = { "EZ", "S" },
        wear = { "SCP_MTF_Uniform", "SCP_MTF_Vest", "SCP_MTF_Helmet" },
        give = { "SCP_MTF_Baton", "SCP_Keycard_L3", "SCP_GasMask", "SCP_GasFilter", "Torch" },
        xp = { Aiming = 2, Fitness = 1, Strength = 1 },
    },
}

local function addProfessions()
    if not ProfessionFactory or not ProfessionFactory.addProfession then
        SCP.log("ProfessionFactory not available: SCP occupations disabled")
        return
    end
    for id, def in pairs(P.List) do
        local ok, prof = pcall(ProfessionFactory.addProfession, id, getText("UI_prof_" .. id), "", def.cost)
        if ok and prof then
            pcall(function() prof:setDescription(getText("UI_profdesc_" .. id)) end)
            for perkName, lvl in pairs(def.xp or {}) do
                if Perks and Perks[perkName] then pcall(prof.addXPBoost, prof, Perks[perkName], lvl) end
            end
        end
    end
end

Events.OnGameBoot.Add(addProfessions)
if Events.OnCreateLivingCharacter then
    -- some versions rebuild the profession list later; add ours again if missing
    Events.OnGameStart.Add(function()
        if ProfessionFactory and ProfessionFactory.getProfession and not ProfessionFactory.getProfession("scp_classd") then
            addProfessions()
        end
    end)
end

function P.getId(player)
    local desc = player:getDescriptor()
    local prof = desc and desc:getProfession()
    if not prof then return nil end
    local id = tostring(prof)
    if type(prof) ~= "string" and prof.getType then id = prof:getType() end
    id = tostring(id):lower()
    for key in pairs(P.List) do
        if id:find(key, 1, true) then return key end
    end
    return nil
end

local function wear(player, fullType)
    local item = player:getInventory():AddItem("Base." .. fullType)
    if item then pcall(function() player:setWornItem(item:getBodyLocation(), item) end) end
end

-- New character: gear, then a trip to the site once it is built.
Events.OnNewGame.Add(function(player, square)
    local id = P.getId(player)
    if not id then return end
    local def = P.List[id]
    for _, t in ipairs(def.wear) do wear(player, t) end
    for _, t in ipairs(def.give) do
        local full = t:find("%.") and t or ("Base." .. t)
        pcall(function() player:getInventory():AddItem(full) end)
    end
    player:getModData().SCP_StartRoom = { def.room[1], def.room[2] }
    if not SCP.Facility.origin() and not isClient() then
        local sq = player:getSquare()
        SCP.sendToServer(player, "PlaceFacility", { x = sq:getX() + 15, y = sq:getY() + 15 })
    end
end)

-- Move the new character into the site once its room is built.
local nextCheck = 0
Events.OnTick.Add(function()
    local t = getTimestampMs()
    if t < nextCheck then return end
    nextCheck = t + 500
    for _, player in ipairs(SCP.localPlayers()) do
        local md = player:getModData()
        local start = md.SCP_StartRoom
        if start then
            local x, y, z = SCP.Facility.roomCenter(start[1], start[2])
            if not x then
                md.SCP_StartRoom = nil -- no site: start on the surface
            else
                local sq = getCell():getGridSquare(x, y, z)
                if sq and sq:getFloor() then
                    SCP.teleport(player, x + 0.5, y + 1.5, z)
                    md.SCP_StartRoom = nil
                    SCP.say(player, "UI_SCP_StartInSite", 200, 220, 255)
                    -- Class-D wake up in the middle of a containment breach.
                    if start[2] == "D" then SCP.sendToServer(player, "StartBreach", {}) end
                elseif not md.SCP_StartWarp then
                    -- Load the area above the site so it gets built.
                    md.SCP_StartWarp = true
                    local o = SCP.Facility.origin()
                    SCP.teleport(player, o.x + 2.5, o.y + 2.5, 0)
                end
            end
        end
    end
end)
