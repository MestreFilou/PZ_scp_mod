--[[
    Makes SCP entities stop behaving like ordinary zombies.

    Voices: a zombie's moans, bites and hurt sounds are looked up from its
    descriptor's voice prefix (IsoZombie.getVoiceSoundName: prefix ..
    "Voice" A/B/C, prefix .. "SprinterVoice" A/B/C, prefix .. "Bite" A/B/C,
    prefix .. "Hurt"). The game resets any prefix that does not contain
    "Zombie", so SCPs get the prefix "SCPSilentZombie", whose sounds are all
    defined as silence in scripts/sounds/scp_sounds.txt. The SCPs' own sounds
    (096 crying, 049 talking, 939 voices, 106 laugh, 173 scraping) are played
    by their logic files and are not affected.

    Gait: each SCP gets a walk type of its own (vanilla zombie gaits only:
    a real custom animation needs new animation clips, see TODO.md).

    Runs on every machine: vocals are played client side.
]]

require "SCP_System"

SCP.Behaviour = SCP.Behaviour or {}

SCP.Behaviour.SilentPrefix = "SCPSilentZombie"

local T = SCP.Types

-- walk: vanilla walk type ("slowN" shambles, "N" walks, "sprintN" runs), speed: 1 sprint, 2 fast, 3 slow.
-- silent: no zombie vocals. noTeeth: cannot bite (kills through its own logic instead).
SCP.Behaviour.Profiles = {
    [T.SCP173]   = { silent = true, noTeeth = true },              -- moves through its own logic
    [T.SCP096]   = { silent = true, walk = "slow1", speed = 3, onlyIf = function(z)
                        return SCP.SCP096 == nil or SCP.SCP096.getState(z) == SCP.SCP096.IDLE end },
    [T.SCP106]   = { silent = true, walk = "slow3", speed = 3 },  -- slow, heavy, inevitable
    [T.SCP049]   = { silent = true, walk = "1", speed = 2 },      -- walks, never runs
    [T.SCP049_2] = { silent = true, walk = "slow2", speed = 3 },
    [T.SCP035]   = { silent = true, walk = "2", speed = 2 },      -- the host walks, never runs
    [T.SCP939]   = { silent = true },                             -- sprinter, see SCP_966_939_Logic
    [T.SCP966]   = { silent = true },
}

-- Note: zombies the game recycles get a fresh descriptor, so the silent
-- prefix does not leak onto ordinary zombies.
local applied = setmetatable({}, { __mode = "k" })

local function silence(zombie)
    local desc = zombie.getDescriptor and zombie:getDescriptor()
    if desc and desc.setVoicePrefix then
        if desc:getVoicePrefix() ~= SCP.Behaviour.SilentPrefix then
            pcall(desc.setVoicePrefix, desc, SCP.Behaviour.SilentPrefix)
        end
    end
    if zombie.setHurtSound then pcall(zombie.setHurtSound, zombie, SCP.Behaviour.SilentPrefix .. "Hurt") end
end

function SCP.Behaviour.apply(zombie, scpType)
    local prof = SCP.Behaviour.Profiles[scpType]
    if not prof then return end
    if prof.silent then silence(zombie) end
    if prof.noTeeth and zombie.setNoTeeth then pcall(zombie.setNoTeeth, zombie, true) end
    if prof.walk and (not prof.onlyIf or prof.onlyIf(zombie)) then
        if zombie.setWalkType then pcall(zombie.setWalkType, zombie, prof.walk) end
        if prof.speed and zombie.changeSpeed then pcall(zombie.changeSpeed, zombie, prof.speed) end
    end
end

SCP.on("OnZombieUpdate", function(zombie)
    local t = SCP.getEntityType(zombie)
    -- Zombie objects are recycled by the game: remember the type it was set up for.
    if not t or applied[zombie] == t then return end
    applied[zombie] = t
    SCP.Behaviour.apply(zombie, t)
end, "SCP_Behaviour")
