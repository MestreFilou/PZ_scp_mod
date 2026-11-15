--[[
    Starting occupations: Class-D, Foundation Scientist, MTF Guard.
    Each one has its own start scenario (see server/SCP_StartScenario.lua
    and client/SCP_StartScenario_Client.lua):
      Class-D   -> a random Class-D cell (Light Containment), jumpsuit only
      Scientist -> the research lab of the Entrance Zone
      MTF Guard -> the gatehouse on the surface, by the main gate
    In single player, if no site exists yet, one is placed with its main
    gate just north of the spawn point.
]]

require "SCP_System"

SCP.Professions = SCP.Professions or {}
local P = SCP.Professions

-- room = { zone, room kind } from SCP_Facility_Data.lua
P.List = {
    scp_classd = {
        room = { "LCZ", "classd" },
        wear = { "SCP_ClassD_Jumpsuit" },
        give = {},
    },
    scp_scientist = {
        room = { "EZ", "lab" },
        wear = { "SCP_LabCoat" },
        give = { "SCP_Hazmat_Suit", "SCP_Keycard_L2", "SCP_Document_Containment", "SCP_Document_008", "Torch" },
    },
    scp_mtf = {
        room = { "SURFACE", "gatehouse" },
        wear = { "SCP_MTF_Uniform", "SCP_MTF_Vest", "SCP_MTF_Helmet" },
        give = { "SCP_MTF_Baton", "SCP_Keycard_L3", "SCP_GasMask", "SCP_GasFilter", "Torch" },
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
    local id = tostring(prof):lower()   -- e.g. "scpfoundation:scp_classd"
    for key in pairs(P.List) do
        if id:find(key, 1, true) then return key end
    end
    return nil
end
