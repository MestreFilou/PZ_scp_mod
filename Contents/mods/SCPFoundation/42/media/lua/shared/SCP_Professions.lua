--[[
    Starting occupations: Class-D, Foundation Scientist, MTF Guard.
    Each starts with its gear and, if an SCP site exists, inside it:
      Class-D  -> a Class-D cell (Light Containment)
      Scientist -> researchers' office (Entrance Zone), level 3 card
      MTF Guard -> security room (Entrance Zone), level 4 card
    In single player, if no site exists yet, one is placed on the closest
    open land (no houses) to the spawn point.
]]

require "SCP_System"
require "SCP_Facility_Layout"

SCP.Professions = SCP.Professions or {}
local P = SCP.Professions

P.List = {
    scp_classd = {
        room = { "LCZ", "classd" },
        wear = { "SCP_ClassD_Jumpsuit" },
        give = {},
    },
    scp_scientist = {
        room = { "EZ", "research" },          -- researchers' office (door level 2)
        card = "SCP_Keycard_L3",              -- opens the labs, the Gate A hall and its own office
        wear = { "SCP_LabCoat" },
        give = { "SCP_Hazmat_Suit", "SCP_Document_Containment", "SCP_Document_008", "Torch" },
    },
    scp_mtf = {
        room = { "EZ", "security" },          -- security room (door level 2)
        card = "SCP_Keycard_L4",              -- guards go everywhere but the warhead
        wear = { "SCP_MTF_Uniform", "SCP_MTF_Vest", "SCP_MTF_Helmet" },
        give = { "SCP_MTF_Baton", "SCP_GasMask", "SCP_GasFilter", "Torch" },
    },
}

-- The occupations themselves are declared in media/registries.lua and
-- media/scripts/characters/scp_professions.txt (Build 42.13+ format).
-- P.List above only holds their gear and start room.

function P.getId(player)
    local desc = player:getDescriptor()
    if not desc then return nil end
    local prof = nil
    if desc.getCharacterProfession then prof = desc:getCharacterProfession() end   -- B42.13+
    if not prof and desc.getProfession then prof = desc:getProfession() end         -- older builds
    if not prof then return nil end
    -- e.g. "scpfoundation:scp_classd"; the object may also give it through a getter
    local names = { tostring(prof) }
    for _, getter in ipairs({ "getName", "getType", "getId", "toString" }) do
        if prof[getter] then
            local ok, v = pcall(prof[getter], prof)
            if ok and v then names[#names + 1] = tostring(v) end
        end
    end
    for _, n in ipairs(names) do
        local id = n:lower()
        for key in pairs(P.List) do
            if id:find(key, 1, true) then return key end
        end
    end
    return nil
end

-- What a new character keeps from the clothes picked at creation: underwear, socks, shoes.
local KEEP = { "underwear", "socks", "shoes", "bra", "underpants" }

local function keep(location)
    location = tostring(location or ""):lower()
    for _, k in ipairs(KEEP) do
        if location:find(k, 1, true) then return true end
    end
    return false
end

-- Takes off (and throws away) the clothes the character was created with.
local function undress(player)
    local worn = player:getWornItems()
    if not worn then return end
    local remove = {}
    for i = 0, worn:size() - 1 do
        local w = worn:get(i)
        local item = w and w:getItem()
        local loc = w and w.getLocation and w:getLocation()
        if item and not keep(loc) then remove[#remove + 1] = item end
    end
    for _, item in ipairs(remove) do
        pcall(player.removeWornItem, player, item)
        pcall(function() player:getInventory():Remove(item) end)
    end
end

local function wear(player, fullType)
    local item = player:getInventory():AddItem("Base." .. fullType)
    if not item then return end
    local loc = item.getBodyLocation and item:getBodyLocation()
    local ok = loc and pcall(player.setWornItem, player, loc, item)
    if not ok and item.getCanBeEquipped then
        loc = item:getCanBeEquipped()
        ok = loc and loc ~= "" and pcall(player.setWornItem, player, loc, item)
    end
    -- multiplayer: tell the others what this character now wears
    if ok and sendClothing then pcall(sendClothing, player, loc, item) end
end

-- Puts the occupation's outfit on (also used by the start scenarios).
function P.dress(player, id)
    local def = P.List[id]
    if not def then return end
    undress(player)
    for _, t in ipairs(def.wear) do wear(player, t) end
    pcall(player.resetModelNextFrame, player)
end

-- New character: gear, then a trip to the site once it is built.
SCP.on("OnNewGame", function(player, square)
    local id = P.getId(player)
    if not id then
        local desc = player:getDescriptor()
        local prof = desc and desc.getCharacterProfession and desc:getCharacterProfession()
        SCP.log("new character, not an SCP occupation:", tostring(prof))
        return
    end
    local def = P.List[id]
    P.dress(player, id)
    SCP.log("new character, occupation", id)
    for _, t in ipairs(def.give) do
        local full = t:find("%.") and t or ("Base." .. t)
        pcall(function() player:getInventory():AddItem(full) end)
    end
    if def.card then player:getInventory():AddItem("Base." .. def.card) end
    player:getModData().SCP_StartRoom = { def.room[1], def.room[2] }
    if not SCP.Facility.origin() and not isClient() then
        local sq = player:getSquare()
        -- The main gate goes a little north of the spawn point; the compound and the site extend north of it.
        -- The server looks for open land close to the spawn point.
        SCP.sendToServer(player, "PlaceFacility", { x = sq:getX(), y = sq:getY() - 12, search = true })
    end
    -- Go straight above the start room, so its area loads and gets built.
    local x, y = SCP.Facility.roomCenter(def.room[1], def.room[2])
    if x then
        player:getModData().SCP_StartWarp = true
        SCP.teleport(player, x + 0.5, y + 0.5, 0)
    end
end)

-- Move the new character into the site once its room is built.
local nextCheck = 0
SCP.on("OnTick", function()
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
                    SCP.teleport(player, x + 1.5, y + 0.5, z)   -- one tile beside the room's centre
                    md.SCP_StartRoom = nil
                    -- make sure the keycard is there (it opens the start room's door)
                    local def = P.List[P.getId(player) or ""]
                    if def and def.card and not player:getInventory():containsTypeRecurse(def.card) then
                        player:getInventory():AddItem("Base." .. def.card)
                    end
                    SCP.say(player, "UI_SCP_StartInSite", 200, 220, 255)
                    -- Class-D wake up in the middle of a containment breach.
                    if start[2] == "classd" then SCP.sendToServer(player, "StartBreach", {}) end
                elseif not md.SCP_StartWarp then
                    -- Load the area above the site so it gets built.
                    md.SCP_StartWarp = true
                    SCP.teleport(player, x + 0.5, y + 0.5, 0)
                end
            end
        end
    end
end)
