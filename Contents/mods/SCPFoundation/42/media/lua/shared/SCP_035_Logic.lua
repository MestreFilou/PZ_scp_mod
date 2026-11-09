--[[
    SCP-035 "Possessive Mask".
    - Worn: drains health and sanity every minute, but keeps the wearer
      rested, full of stamina and able to carry more.
    - After SCP035LockMinutes worn, it cannot be taken off any more.
    - Carried (not worn) for too long, it puts itself on.
    - If the wearer dies, a "Possessed Host" rises where they fell.
]]

require "SCP_System"

SCP.SCP035 = SCP.SCP035 or {}

local MASK = "Base.SCP_035_Mask"
local CARRY_LIMIT_MINUTES = 60
local WEIGHT_BONUS = 8

local function findCarried(player)
    return player:getInventory():getFirstTypeRecurse(MASK)
end

local function wear(player, item)
    if item:getContainer() ~= player:getInventory() then
        item:getContainer():Remove(item)
        player:getInventory():AddItem(item)
    end
    player:setWornItem(item:getBodyLocation(), item)
    if triggerEvent then pcall(triggerEvent, "OnClothingUpdated", player) end
end

local function setWeightBonus(player, on)
    local md = player:getModData()
    if on and not md.SCP035_BaseWeight then
        md.SCP035_BaseWeight = player:getMaxWeightBase()
        player:setMaxWeightBase(md.SCP035_BaseWeight + WEIGHT_BONUS)
    elseif not on and md.SCP035_BaseWeight then
        player:setMaxWeightBase(md.SCP035_BaseWeight)
        md.SCP035_BaseWeight = nil
    end
end

function SCP.SCP035.isLocked(player)
    local md = player:getModData()
    return (md.SCP035_WornMinutes or 0) >= SCP.opt("SCP035LockMinutes")
end

local function everyMinute()
    for _, player in ipairs(SCP.localPlayers()) do
        local md = player:getModData()
        local worn = SCP.getWorn(player, MASK)
        if worn then
            md.SCP035_WornMinutes = (md.SCP035_WornMinutes or 0) + 1
            md.SCP035_CarriedMinutes = 0
            md.SCP035_Wearing = true

            SCP.damageHealth(player, SCP.opt("SCP035Drain"))
            SCP.setStat(player, "STRESS", math.min(1, SCP.getStat(player, "STRESS") + 0.01))
            SCP.setStat(player, "SANITY", math.max(0, SCP.getStat(player, "SANITY") - 0.005))
            SCP.setStat(player, "ENDURANCE", 1)
            SCP.setStat(player, "FATIGUE", 0)
            setWeightBonus(player, true)

            if md.SCP035_WornMinutes == SCP.opt("SCP035LockMinutes") then
                SCP.say(player, "UI_SCP_035_Locked", 200, 60, 200)
            elseif ZombRand(60) == 0 then
                SCP.say(player, "UI_SCP_035_Whisper", 200, 120, 200)
            end
        else
            md.SCP035_Wearing = false
            setWeightBonus(player, false)
            local carried = findCarried(player)
            if carried then
                md.SCP035_CarriedMinutes = (md.SCP035_CarriedMinutes or 0) + 1
                if md.SCP035_CarriedMinutes >= CARRY_LIMIT_MINUTES then
                    md.SCP035_CarriedMinutes = 0
                    wear(player, carried)
                    SCP.say(player, "UI_SCP_035_Attach", 200, 60, 200)
                end
            else
                md.SCP035_CarriedMinutes = 0
                md.SCP035_WornMinutes = 0
            end
        end
    end
end

Events.EveryOneMinute.Add(everyMinute)

-- Locked mask: put it straight back on if the player removes it.
local function onClothingUpdated(player)
    if not player or not instanceof(player, "IsoPlayer") or not player:isLocalPlayer() then return end
    local md = player:getModData()
    if not md.SCP035_Wearing or not SCP.SCP035.isLocked(player) then return end
    if SCP.getWorn(player, MASK) then return end
    local carried = findCarried(player)
    if carried then
        wear(player, carried)
        SCP.say(player, "UI_SCP_035_CannotRemove", 200, 60, 200)
    end
end

Events.OnClothingUpdated.Add(onClothingUpdated)

-- The wearer died: ask the server to raise a Possessed Host.
local function onPlayerDeath(player)
    if not player or not player:isLocalPlayer() then return end
    local mask = SCP.getWorn(player, MASK)
    if not mask then return end
    pcall(player.removeWornItem, player, mask)
    pcall(function() mask:getContainer():Remove(mask) end)
    player:getModData().SCP035_Wearing = false
    SCP.sendToServer(player, "SCP035Host", {
        x = math.floor(player:getX()), y = math.floor(player:getY()), z = math.floor(player:getZ()),
    })
end

Events.OnPlayerDeath.Add(onPlayerDeath)

SCP.ServerCommands.SCP035Host = function(player, args)
    if SCP.Spawner then SCP.Spawner.spawn(SCP.Types.SCP035, args.x, args.y, args.z) end
end

------------------------------------------------------------------------
-- Possessed Host behaviour: fast, tough and unsettles everyone nearby.
------------------------------------------------------------------------

local function onZombieUpdate(zombie)
    if not SCP.isEntity(zombie, SCP.Types.SCP035) then return end
    local md = zombie:getModData()
    if not md.SCP035_Init then
        md.SCP035_Init = true
        SCP.makeSprinter(zombie)
        zombie:setHealth(math.max(zombie:getHealth(), 6))
    end
    local t = getTimestampMs()
    if md.SCP035_NextAura and t < md.SCP035_NextAura then return end
    md.SCP035_NextAura = t + 2000
    for _, p in ipairs(SCP.localPlayers()) do
        if SCP.sameLevel(p, zombie) and SCP.dist(p, zombie) < 8 then
            SCP.setStat(p, "PANIC", math.min(100, SCP.getStat(p, "PANIC") + 10))
            SCP.setStat(p, "STRESS", math.min(1, SCP.getStat(p, "STRESS") + 0.02))
        end
    end
end

Events.OnZombieUpdate.Add(onZombieUpdate)

-- The host wears the mask as part of its outfit, so it can be looted from the corpse.
