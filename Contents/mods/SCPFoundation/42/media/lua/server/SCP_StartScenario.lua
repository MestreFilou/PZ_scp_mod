--[[
    Start scenarios of the SCP occupations (server side).

    The client asks for a start room when a new character is created
    (ScenarioRequest), walks the character there once the room is built,
    then reports it arrived (ScenarioArrived). The server then:
      - empties the start room of staff zombies (single player);
      - Class-D: fills the other Class-D cells with zombie Class-D, then
        a few seconds later every Class-D cell door opens;
      - "Total breach" start (sandbox option StartScenario = 2): the first
        character to arrive starts a containment breach, once per world.

    "Escape" start (StartScenario = 1, the default): only the Class-D cells
    open; every keycard door stays locked. Level 1 and 2 keycards no longer
    lie on the floor of the site: a few dead staff (zombie Class-D,
    scientists, guards) carry one, see the drop table below. Level 3 and
    up are still found inside the rooms they open.
]]

require "SCP_System"
require "SCP_Doors"
require "SCP_Facility_Layout"
require "SCP_Spawner"
require "SCP_BreachEvent"
require "SCP_Professions"

SCP.Start = SCP.Start or {}
local S = SCP.Start
local F = SCP.Facility
local P = SCP.Professions

S.ESCAPE, S.BREACH = 1, 2

S.CELL_OPEN_DELAY = 4 / 60        -- in-game hours (4 minutes, about 10 s at the default day length)
S.BREACH_DELAY = 6 / 60

-- Staff zombies that are taken out of a start room.
S.StaffOutfits = {
    SCP_ClassD = true, SCP_Scientist = true, SCP_Hazmat = true, SCP_MTF = true, SCP_ZombieGuard = true,
}

-- Keycard carried by dead staff: { level, chance in % }, highest level rolled first,
-- one card at most. Kept rare on purpose; the sandbox option KeycardDropRate scales it.
S.Drops = {
    SCP_ClassD      = { { 1, 4 } },
    SCP_Scientist   = { { 3, 1 }, { 2, 4 }, { 1, 8 } },
    SCP_Hazmat      = { { 3, 1 }, { 2, 4 }, { 1, 8 } },
    SCP_MTF         = { { 4, 1 }, { 3, 3 }, { 2, 7 } },
    SCP_ZombieGuard = { { 4, 1 }, { 3, 3 }, { 2, 7 } },
}

S.PITY_KILLS = 15

local function now() return getGameTime():getWorldAgeHours() end

function S.mode()
    local m = SCP.opt("StartScenario")
    if m == S.BREACH then return S.BREACH end
    return S.ESCAPE
end

local function state()
    local world = SCP.world()
    world.scenario = world.scenario or { claimed = {}, pending = {} }
    world.scenario.claimed = world.scenario.claimed or {}
    world.scenario.pending = world.scenario.pending or {}
    return world.scenario
end

local function roomKey(r) return r.cx .. "," .. r.cy .. "," .. r.z end

-- Marks a room's staff and SCP as already spawned, so they never appear.
local function suppressSpawns(r)
    local world = SCP.world()
    world.facility = world.facility or {}
    world.facility.spawned = world.facility.spawned or {}
    world.facility.spawned[roomKey(r)] = true
end

------------------------------------------------------------------------
-- Rooms and doors
------------------------------------------------------------------------

-- A start room for an occupation: a Class-D cell nobody has yet, else any.
local function pickRoom(def)
    local rooms = F.roomsOf(def.room[1], def.room[2])
    if #rooms == 0 then return nil end
    local st = state()
    local free = {}
    for _, r in ipairs(rooms) do
        if not st.claimed[roomKey(r)] then free[#free + 1] = r end
    end
    local list = #free > 0 and free or rooms
    return list[ZombRand(#list) + 1]
end

-- Doors on the edge of a room (world coordinates).
function S.roomDoors(r)
    local o = F.origin()
    local out = {}
    if not o then return out end
    local level = r.z == 0 and F.Data.surface or F.Data.underground
    local lx0, ly0, lx1, ly1 = r.x0 - o.x, r.y0 - o.y, r.x1 - o.x, r.y1 - o.y
    for _, d in ipairs(level.doors) do
        if d.x >= lx0 - 1 and d.x <= lx1 + 1 and d.y >= ly0 - 1 and d.y <= ly1 + 1 then
            out[#out + 1] = { x = o.x + d.x, y = o.y + d.y, z = r.z }
        end
    end
    return out
end

local function openDoorAt(p)
    local door = SCP.Doors.find(p.x, p.y, p.z)
    if not door then return end
    SCP.Doors.setLocked(door, false)
    SCP.Doors.setOpen(door, true, nil)
    SCP.sendToClients("DoorState", { x = p.x, y = p.y, z = p.z, locked = false })
end

function S.openClassDCells()
    for _, r in ipairs(F.roomsOf("LCZ", "classd")) do
        for _, p in ipairs(S.roomDoors(r)) do openDoorAt(p) end
    end
    for _, player in ipairs(SCP.allPlayers()) do
        if F.levelAt(player:getX(), player:getY(), player:getZ()) then
            SCP.sendToClient(player, "Notify", { key = "UI_SCP_Start_CellsOpen" })
        end
    end
end

-- Takes staff zombies out of a room. Single player only: in multiplayer
-- the start room is kept empty by suppressSpawns() instead.
local function clearRoom(r)
    if isServer() then return end
    local list = getCell():getZombieList()
    for i = list:size() - 1, 0, -1 do
        local z = list:get(i)
        if z and math.floor(z:getZ()) == r.z
            and z:getX() >= r.x0 - 1 and z:getX() <= r.x1 + 2
            and z:getY() >= r.y0 - 1 and z:getY() <= r.y1 + 2
            and S.StaffOutfits[z:getOutfitName() or ""] then
            pcall(z.removeFromWorld, z)
            pcall(z.removeFromSquare, z)
        end
    end
end

-- Staff roaming the Light Containment hallways (once per world, on the
-- first Class-D start), near the cells so their squares are loaded.
S.Roamers = { SCP_Scientist = 4, SCP_ZombieGuard = 3, SCP_ClassD = 3 }
S.ROAM_RADIUS = 40

local function hallwayTiles(near)
    local o = F.origin()
    local D = F.Data
    local level = D.underground
    local tiles = {}
    for ly = 0, D.height - 1 do
        for lx = 0, D.width - 1 do
            if F.charAt(level, "zone", lx, ly) == "L" and F.charAt(level, "floor", lx, ly) ~= " " then
                local inRoom = false
                for _, r in ipairs(level.rooms) do
                    if lx >= r.x0 and lx <= r.x1 and ly >= r.y0 and ly <= r.y1 then inRoom = true break end
                end
                local x, y = o.x + lx, o.y + ly
                if not inRoom and math.abs(x - near.cx) <= S.ROAM_RADIUS and math.abs(y - near.cy) <= S.ROAM_RADIUS then
                    local sq = getCell():getGridSquare(x, y, o.z)
                    if sq and sq:getFloor() then tiles[#tiles + 1] = { x = x, y = y } end
                end
            end
        end
    end
    return tiles
end

local function spawnRoamers(near)
    local tiles = hallwayTiles(near)
    if #tiles == 0 then return end
    for outfit, n in pairs(S.Roamers) do
        for _ = 1, n do
            local t = tiles[ZombRand(#tiles) + 1]
            SCP.Spawner.spawn(outfit, t.x, t.y, near.z, 1)
        end
    end
end

-- The other Class-D: one zombie Class-D in every cell nobody plays in (once per world).
local function fillCells(near)
    local st = state()
    if st.cellsFilled then return end
    st.cellsFilled = true
    spawnRoamers(near)
    for _, r in ipairs(F.roomsOf("LCZ", "classd")) do
        if not st.claimed[roomKey(r)] then
            SCP.Spawner.spawn("SCP_ClassD", r.cx, r.cy, r.z, 1)
        end
    end
end

local function schedule(action, delay)
    table.insert(state().pending, { action = action, at = now() + delay })
end

------------------------------------------------------------------------
-- Commands from the client
------------------------------------------------------------------------

local function reply(player, args)
    args.pid = SCP.playerId(player)
    SCP.sendToClient(player, "ScenarioGo", args)
end

SCP.ServerCommands.ScenarioRequest = function(player, args)
    local def = P.List[args.prof or ""]
    if not def then return end
    if not F.origin() and not isClient() and not isServer() then
        -- Single player and no site yet: its main gate goes a little north of the spawn point.
        SCP.ServerCommands.PlaceFacility(player, { x = math.floor(player:getX()), y = math.floor(player:getY()) - 12 })
    end
    local r = F.origin() and pickRoom(def)
    if not r then
        reply(player, { none = true })
        return
    end
    state().claimed[roomKey(r)] = true
    suppressSpawns(r)
    if isServer() then ModData.transmit("SCPFoundation") end
    reply(player, { prof = args.prof, x0 = r.x0, y0 = r.y0, x1 = r.x1, y1 = r.y1, cx = r.cx, cy = r.cy, z = r.z })
end

SCP.ServerCommands.ScenarioArrived = function(player, args)
    if not args.x0 then return end
    local r = { x0 = args.x0, y0 = args.y0, x1 = args.x1, y1 = args.y1, cx = args.cx, cy = args.cy, z = args.z }
    clearRoom(r)
    local st = state()
    if S.mode() == S.BREACH and not st.breachDone then
        st.breachDone = true
        schedule("breach", S.BREACH_DELAY)
    end
    if args.prof == "scp_classd" then
        fillCells(r)
        schedule("cells", S.CELL_OPEN_DELAY)
    end
end

-- Pending start events.
SCP.on("EveryOneMinute", function()
    if isClient() then return end
    local world = SCP.world()
    local st = world.scenario
    if not st or not st.pending or #st.pending == 0 then return end
    local t = now()
    local keep = {}
    for _, e in ipairs(st.pending) do
        if t >= e.at then
            if e.action == "cells" then
                S.openClassDCells()
            elseif e.action == "breach" then
                SCP.Breach.start()
            end
        else
            keep[#keep + 1] = e
        end
    end
    st.pending = keep
end)

------------------------------------------------------------------------
-- Keycards on dead staff
------------------------------------------------------------------------

SCP.on("OnZombieDead", function(zombie)
    if isClient() then return end
    local md = zombie:getModData()
    if md.SCP_CardRolled then return end
    md.SCP_CardRolled = true
    local drops = S.Drops[zombie:getOutfitName() or ""]
    if not drops then return end
    local st = state()
    local rate = (SCP.opt("KeycardDropRate") or 100) / 100
    local level = nil
    for _, d in ipairs(drops) do
        if ZombRandFloat(0, 100) < d[2] * rate then level = d[1] break end
    end
    -- Rare, but never a dead end: after PITY_KILLS staff killed without a card, the next one has one.
    st.dryKills = (st.dryKills or 0) + 1
    if not level and rate > 0 and st.dryKills >= S.PITY_KILLS then level = drops[#drops][1] end
    if not level then return end
    st.dryKills = 0
    pcall(function() zombie:getInventory():AddItem("Base.SCP_Keycard_L" .. level) end)
end)
