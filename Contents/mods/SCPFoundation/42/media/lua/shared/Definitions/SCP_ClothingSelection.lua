--[[
    Clothes shown on the character creation screen for the SCP occupations
    (the game looks them up by the occupation's name). The same outfit is
    put on again when the game starts, see SCP_Professions.lua.
]]

ClothingSelectionDefinitions = ClothingSelectionDefinitions or {}

local outfits = {
    scp_classd = { Female = {
        Boilersuit = { items = { "Base.SCP_ClassD_Jumpsuit" } },
    } },
    scp_scientist = { Female = {
        Jacket = { items = { "Base.SCP_LabCoat" } },
        Shirt = { items = { "Base.Shirt_FormalWhite" } },
        Pants = { items = { "Base.Trousers_Black" } },
    } },
    scp_mtf = { Female = {
        Boilersuit = { items = { "Base.SCP_MTF_Uniform" } },
        TorsoExtraVest = { items = { "Base.SCP_MTF_Vest" } },
        Hat = { items = { "Base.SCP_MTF_Helmet" } },
    } },
}

-- The key is whatever the occupation's getName() gives: with or without the mod's prefix.
for name, def in pairs(outfits) do
    ClothingSelectionDefinitions[name] = def
    ClothingSelectionDefinitions["scpfoundation:" .. name] = def
end
