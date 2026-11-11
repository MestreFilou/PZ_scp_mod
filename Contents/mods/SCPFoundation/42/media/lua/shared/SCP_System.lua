--[[
    SCP Foundation - core helpers shared by every other file.
    Everything lives in the global SCP table.
]]

SCP = SCP or {}
SCP.MODULE = "SCPFoundation"
SCP.VERSION = "0.1.0"

SCP.Types = {
    SCP173 = "SCP_173",
    SCP096 = "SCP_096",
    SCP106 = "SCP_106",
    SCP035 = "SCP_035_Host",
    SCP049 = "SCP_049",
    SCP049_2 = "SCP_049_2",
    SCP939 = "SCP_939",
    SCP966 = "SCP_966",
    GUARD  = "SCP_ZombieGuard",
}

SCP.MaxKeyLevel = 5

------------------------------------------------------------------------
-- Settings (sandbox options with safe defaults)
------------------------------------------------------------------------

local defaults = {
    EnableLoot = true,
    BlinkInterval = 7.0,
    SCP173Range = 10,
    SCP096TriggerMin = 5,
    SCP096TriggerMax = 10,
    SCP106Speed = 0.035,
    SCP035Drain = 0.4,
    SCP035LockMinutes = 30,
    GasFilterHours = 12,
    PocketDimensionDepth = -12,
    BreachChancePerDay = 5,
    BreachDurationHours = 6,
    BreachGuardCount = 8,
    FacilityX = 0,
    FacilityY = 0,
    FacilityDepth = -2,
}

function SCP.opt(name)
    local sv = SandboxVars and SandboxVars.SCP
    if sv and sv[name] ~= nil then return sv[name] end
    return defaults[name]
end

------------------------------------------------------------------------
-- Logging
------------------------------------------------------------------------

function SCP.log(...)
    local parts = {}
    for i = 1, select("#", ...) do parts[#parts + 1] = tostring(select(i, ...)) end
    print("[SCPFoundation] " .. table.concat(parts, " "))
end

------------------------------------------------------------------------
-- Stats: Build 42 moved stats to stats:set(CharacterStat.X, v).
-- These wrappers try the new API first, then the older setters.
------------------------------------------------------------------------

local legacyStat = {
    FATIGUE = "Fatigue", ENDURANCE = "Endurance", PANIC = "Panic", STRESS = "Stress",
    SANITY = "Sanity", HUNGER = "Hunger", THIRST = "Thirst", PAIN = "Pain",
    SICKNESS = "Sickness", BOREDOM = "Boredom", DRUNKENNESS = "Drunkenness",
}

function SCP.setStat(player, stat, value)
    local stats = player and player:getStats()
    if not stats then return end
    if CharacterStat and CharacterStat[stat] and stats.set then
        if pcall(stats.set, stats, CharacterStat[stat], value) then return end
    end
    local name = legacyStat[stat]
    local fn = name and stats["set" .. name]
    if fn then pcall(fn, stats, value) end
end

function SCP.getStat(player, stat)
    local stats = player and player:getStats()
    if not stats then return 0 end
    if CharacterStat and CharacterStat[stat] and stats.get then
        local ok, v = pcall(stats.get, stats, CharacterStat[stat])
        if ok and v then return v end
    end
    local name = legacyStat[stat]
    local fn = name and stats["get" .. name]
    if fn then
        local ok, v = pcall(fn, stats)
        if ok and v then return v end
    end
    return 0
end

------------------------------------------------------------------------
-- Players and geometry
------------------------------------------------------------------------

-- Players controlled on this machine (split-screen included).
function SCP.localPlayers()
    local list = {}
    for i = 0, getNumActivePlayers() - 1 do
        local p = getSpecificPlayer(i)
        if p and not p:isDead() then list[#list + 1] = p end
    end
    return list
end

-- Every living player known to this machine (server: all online players).
function SCP.allPlayers()
    local list = {}
    if isServer() then
        local online = getOnlinePlayers()
        for i = 0, online:size() - 1 do
            local p = online:get(i)
            if p and not p:isDead() then list[#list + 1] = p end
        end
    else
        list = SCP.localPlayers()
        if isClient() then
            local online = getOnlinePlayers()
            if online then
                for i = 0, online:size() - 1 do
                    local p = online:get(i)
                    if p and not p:isDead() and not p:isLocalPlayer() then list[#list + 1] = p end
                end
            end
        end
    end
    return list
end

function SCP.dist(a, b)
    local dx, dy = a:getX() - b:getX(), a:getY() - b:getY()
    return math.sqrt(dx * dx + dy * dy)
end

function SCP.sameLevel(a, b)
    return math.floor(a:getZ()) == math.floor(b:getZ())
end

function SCP.nearestPlayer(obj, maxDist, list)
    local best, bestD = nil, maxDist or 9999
    for _, p in ipairs(list or SCP.allPlayers()) do
        if SCP.sameLevel(p, obj) then
            local d = SCP.dist(p, obj)
            if d < bestD then best, bestD = p, d end
        end
    end
    return best, bestD
end

-- Cosine of the angle between where `viewer` faces and the direction to `target`.
function SCP.facingDot(viewer, target)
    local fwd = viewer:getForwardDirection()
    local fx, fy = fwd:getX(), fwd:getY()
    local dx, dy = target:getX() - viewer:getX(), target:getY() - viewer:getY()
    local len = math.sqrt(dx * dx + dy * dy)
    local flen = math.sqrt(fx * fx + fy * fy)
    if len < 0.001 or flen < 0.001 then return 1 end
    return (fx * dx + fy * dy) / (len * flen)
end

-- True when `viewer` has `target` in its field of view and line of sight.
-- fovDeg is the full cone angle.
function SCP.canSee(viewer, target, maxDist, fovDeg)
    if not viewer or not target then return false end
    if not SCP.sameLevel(viewer, target) then return false end
    if SCP.dist(viewer, target) > (maxDist or 20) then return false end
    local half = math.rad((fovDeg or 120) / 2)
    if SCP.facingDot(viewer, target) < math.cos(half) then return false end
    if viewer.CanSee then
        local ok, seen = pcall(viewer.CanSee, viewer, target)
        if ok and seen == false then return false end
    end
    return true
end

------------------------------------------------------------------------
-- Entities (SCPs are zombies wearing a dedicated outfit; the outfit
-- name is synced in multiplayer so every machine can recognise them)
------------------------------------------------------------------------

function SCP.getEntityType(zombie)
    if not zombie or not instanceof(zombie, "IsoZombie") then return nil end
    local md = zombie:getModData()
    if md.SCP_Type then return md.SCP_Type end
    local outfit = zombie:getOutfitName()
    if not outfit then return nil end
    for _, t in pairs(SCP.Types) do
        if outfit == t then
            md.SCP_Type = t
            return t
        end
    end
    return nil
end

function SCP.isEntity(zombie, scpType)
    return SCP.getEntityType(zombie) == scpType
end

function SCP.zombieKey(zombie)
    if isClient() or isServer() then return zombie:getOnlineID() end
    return zombie:getID()
end

function SCP.findZombie(key)
    local list = getCell():getZombieList()
    for i = 0, list:size() - 1 do
        local z = list:get(i)
        if SCP.zombieKey(z) == key then return z end
    end
    return nil
end

-- Freeze/unfreeze a zombie's own AI movement.
function SCP.freeze(zombie, frozen)
    if zombie:isUseless() ~= frozen then zombie:setUseless(frozen) end
end

------------------------------------------------------------------------
-- Inventory / equipment
------------------------------------------------------------------------

function SCP.keycardLevel(player)
    local inv = player:getInventory()
    for level = SCP.MaxKeyLevel, 1, -1 do
        if inv:containsTypeRecurse("SCP_Keycard_L" .. level) then return level end
    end
    return 0
end

function SCP.getWorn(player, fullType)
    local worn = player:getWornItems()
    for i = 0, worn:size() - 1 do
        local item = worn:get(i):getItem()
        if item and item:getFullType() == fullType then return item end
    end
    return nil
end

function SCP.hasHazmat(player)
    return SCP.getWorn(player, "Base.SCP_Hazmat_Suit") ~= nil
end

-- Gas mask with a working filter, or a hazmat suit.
function SCP.hasAirProtection(player)
    if SCP.hasHazmat(player) then return true end
    local mask = SCP.getWorn(player, "Base.SCP_GasMask")
    if not mask then return false end
    return (mask:getModData().SCP_Filter or 0) > 0
end

------------------------------------------------------------------------
-- Feedback
------------------------------------------------------------------------

function SCP.say(player, textKey, r, g, b, ...)
    if not player then return end
    local text = getText(textKey, ...)
    if HaloTextHelper and HaloTextHelper.addText then
        HaloTextHelper.addText(player, text, r or 255, g or 255, b or 255)
    else
        player:Say(text)
    end
end

function SCP.playSoundAt(obj, sound)
    if not obj then return end
    if obj.playSound then
        pcall(obj.playSound, obj, sound)
    else
        local sq = obj.getSquare and obj:getSquare()
        if sq then getSoundManager():PlayWorldSound(sound, sq, 0, 20, 1, false) end
    end
end

------------------------------------------------------------------------
-- Damage helpers
------------------------------------------------------------------------

function SCP.damageHealth(player, amount)
    local bd = player:getBodyDamage()
    if bd.ReduceGeneralHealth then bd:ReduceGeneralHealth(amount) end
end

function SCP.killPlayer(player, attacker, partType)
    local bd = player:getBodyDamage()
    if partType then
        local part = bd:getBodyPart(partType)
        if part then pcall(part.AddDamage, part, 200) end
    end
    if player.Kill then
        if pcall(player.Kill, player, attacker) then return end
    end
    player:setHealth(0)
end

------------------------------------------------------------------------
-- Persistent world data (doors, containment points, breach state)
------------------------------------------------------------------------

function SCP.world()
    local md = ModData.getOrCreate("SCPFoundation")
    md.points = md.points or {}
    md.breach = md.breach or { active = false }
    return md
end

function SCP.isBreachActive()
    local md = ModData.get("SCPFoundation")
    return md ~= nil and md.breach ~= nil and md.breach.active == true
end

-- SCPs placed in their cell by the facility stay dormant until a breach,
-- unless someone walks right up to them.
function SCP.isDormant(zombie, wakeDist)
    if not zombie:getModData().SCP_Contained or SCP.isBreachActive() then return false end
    -- SCP-079 cut the containment power: everything wakes up.
    local md = ModData.get("SCPFoundation")
    local until079 = md and md.scp079 and md.scp079.blackoutUntil
    if until079 and getGameTime():getWorldAgeHours() < until079 then return false end
    local p, d = SCP.nearestPlayer(zombie, wakeDist or 6)
    return p == nil
end

------------------------------------------------------------------------
-- Commands between client and server. In single player both sides run
-- in the same process, so the handler is called directly.
------------------------------------------------------------------------

SCP.ServerCommands = SCP.ServerCommands or {}
SCP.ClientCommands = SCP.ClientCommands or {}

function SCP.sendToServer(player, command, args)
    args = args or {}
    if isClient() then
        sendClientCommand(player, SCP.MODULE, command, args)
    elseif SCP.ServerCommands[command] then
        SCP.ServerCommands[command](player, args)
    end
end

function SCP.sendToClients(command, args)
    args = args or {}
    if isServer() then
        sendServerCommand(SCP.MODULE, command, args)
    elseif SCP.ClientCommands[command] then
        SCP.ClientCommands[command](args)
    end
end

function SCP.sendToClient(player, command, args)
    args = args or {}
    if isServer() then
        sendServerCommand(player, SCP.MODULE, command, args)
    elseif SCP.ClientCommands[command] then
        SCP.ClientCommands[command](args)
    end
end

Events.OnClientCommand.Add(function(module, command, player, args)
    if module ~= SCP.MODULE then return end
    local fn = SCP.ServerCommands[command]
    if fn then fn(player, args or {}) end
end)

Events.OnServerCommand.Add(function(module, command, args)
    if module ~= SCP.MODULE then return end
    local fn = SCP.ClientCommands[command]
    if fn then fn(args or {}) end
end)

function SCP.isAdmin(player)
    if not isClient() and not isServer() then return true end
    if isDebugEnabled() then return true end
    local level = player and player:getAccessLevel()
    return level ~= nil and level ~= "" and level ~= "None"
end

------------------------------------------------------------------------
-- Player ids that work in single player and multiplayer
------------------------------------------------------------------------

function SCP.playerId(player)
    if isClient() or isServer() then return player:getOnlineID() end
    return player:getPlayerNum()
end

function SCP.playerById(id)
    if id == nil then return nil end
    if isClient() or isServer() then
        if getPlayerByOnlineID then return getPlayerByOnlineID(id) end
        for _, p in ipairs(SCP.allPlayers()) do
            if p:getOnlineID() == id then return p end
        end
        return nil
    end
    return getSpecificPlayer(id)
end

------------------------------------------------------------------------
-- Moving characters
------------------------------------------------------------------------

function SCP.teleport(chr, x, y, z)
    chr:setX(x); chr:setY(y); chr:setZ(z)
    if chr.setLx then pcall(chr.setLx, chr, x); pcall(chr.setLy, chr, y); pcall(chr.setLz, chr, z) end
    if chr.setLastX then pcall(chr.setLastX, chr, x); pcall(chr.setLastY, chr, y); pcall(chr.setLastZ, chr, z) end
    local sq = getCell():getGridSquare(math.floor(x), math.floor(y), math.floor(z))
    if sq and chr.setCurrent then pcall(chr.setCurrent, chr, sq) end
end

function SCP.makeSprinter(zombie)
    if zombie.setWalkType then pcall(zombie.setWalkType, zombie, "sprint" .. ZombRand(1, 6)) end
    if zombie.changeSpeed then pcall(zombie.changeSpeed, zombie, 1) end
end

-- Remove obstacles (doors, windows, barricades, player-built walls) around a
-- point. Server / single player only.
function SCP.smashAround(x, y, z, radius)
    radius = radius or 1
    for dx = -radius, radius do
        for dy = -radius, radius do
            local sq = getCell():getGridSquare(x + dx, y + dy, z)
            if sq then
                local objs = sq:getObjects()
                for i = objs:size() - 1, 0, -1 do
                    local o = objs:get(i)
                    if instanceof(o, "IsoWindow") then
                        if not o:isSmashed() then pcall(o.smashWindow, o) end
                    elseif instanceof(o, "IsoDoor") or instanceof(o, "IsoBarricade")
                        or (instanceof(o, "IsoThumpable") and (o:isDoor() or o:isBlockAllTheSquare() or o:isThumpable())) then
                        sq:transmitRemoveItemFromSquare(o)
                    end
                end
            end
        end
    end
end

------------------------------------------------------------------------
-- Diseases (SCP-008, SCP-1025)
------------------------------------------------------------------------

-- Gives the Knox infection (the zombie plague).
function SCP.infect(player)
    local bd = player:getBodyDamage()
    local part = bd:getBodyPart(BodyPartType.Hand_R)
    if part then pcall(part.SetInfected, part, true) end
    pcall(bd.setInfected, bd, true)
    pcall(bd.setInfectionTime, bd, getGameTime():getWorldAgeHours())
    local duration = 48
    if bd.pickMortalityDuration then
        local ok, v = pcall(bd.pickMortalityDuration, bd)
        if ok and v then duration = v end
    end
    pcall(bd.setInfectionMortalityDuration, bd, duration)
end

function SCP.isWearing714(player)
    return SCP.getWorn(player, "Base.SCP_714_Ring") ~= nil
end
