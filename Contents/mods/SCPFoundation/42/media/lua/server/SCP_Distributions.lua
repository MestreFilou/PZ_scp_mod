--[[
    Adds SCP Foundation gear to vanilla loot tables (if the option is on).
    Lists that do not exist in the current game version are skipped.
]]

require "Items/ProceduralDistributions"
require "SCP_System"

local loot = {
    PoliceStorageOutfit   = { "SCP_MTF_Helmet", 0.5, "SCP_MTF_Vest", 0.5, "SCP_MTF_Uniform", 0.8, "SCP_MTF_Baton", 1 },
    ArmyStorageOutfit     = { "SCP_MTF_Helmet", 1, "SCP_MTF_Vest", 1, "SCP_MTF_Uniform", 1.5, "SCP_GasMask", 1, "SCP_GasFilter", 2, "SCP_MTF_Knife", 1 },
    ArmyStorageMedical    = { "SCP_GasFilter", 2, "SCP_Hazmat_Suit", 0.5 },
    LaboratoryLockers     = { "SCP_LabCoat", 2, "SCP_Hazmat_Suit", 1, "SCP_GasMask", 1, "SCP_GasFilter", 3, "SCP_Keycard_L1", 2, "SCP_Keycard_L2", 1 },
    MedicalStorageDrugs   = { "SCP_500_Pill", 0.02 },
    MedicalClinicDrugs    = { "SCP_500_Pill", 0.01 },
    PrisonCellRandom      = { "SCP_ClassD_Jumpsuit", 2 },
    SecurityLockers       = { "SCP_Keycard_L1", 2, "SCP_Keycard_L2", 1, "SCP_Keycard_L3", 0.5, "SCP_Keycard_L4", 0.1, "SCP_Keycard_L5", 0.02 },
    OfficeDeskHome        = { "SCP_Document_Containment", 0.2 },
    MuseumBasement        = { "SCP_035_Mask", 0.05 },
}

local function addLoot()
    if not SCP.opt("EnableLoot") then return end
    if not ProceduralDistributions or not ProceduralDistributions.list then return end
    for listName, entries in pairs(loot) do
        local dist = ProceduralDistributions.list[listName]
        if dist and dist.items then
            for i = 1, #entries, 2 do
                table.insert(dist.items, entries[i])
                table.insert(dist.items, entries[i + 1])
            end
        end
    end
end

Events.OnPreDistributionMerge.Add(addLoot)
