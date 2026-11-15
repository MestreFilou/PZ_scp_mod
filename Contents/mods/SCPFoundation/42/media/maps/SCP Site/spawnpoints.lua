-- SCP site region: everyone starts on the road in front of the site gate.
-- The SCP occupations are then moved into their start room inside the site
-- (lua/shared/SCP_Professions.lua). Keep in step with SCP.Facility.FIXED_GATE.
function SpawnPoints()
    local gate = {
        { posX = 12210, posY = 8322, posZ = 0 },
        { posX = 12214, posY = 8323, posZ = 0 },
        { posX = 12218, posY = 8322, posZ = 0 },
    }
    return {
        unemployed = gate,
        scp_classd = gate,
        scp_scientist = gate,
        scp_mtf = gate,
    }
end
