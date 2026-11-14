--[[
    SCP-079 "Old AI". No body: it lives in a terminal in Heavy Containment
    and turns the site's electronics against the people inside.

    While active (not re-contained), every minute and for each player in
    the site it may:
      - lock a nearby keycard door, or unlock one (cells included)
      - set off an alarm on the player, drawing every zombie around
      - cut the containment power for a few minutes (dormant SCPs wake up)
    It also broadcasts threats on the radio (107.9 MHz) every few hours.

    Re-containment: start the 3 generators in the generator room, then
    overcharge SCP-079 from its terminal. This also ends a running breach.
    Every new breach brings it back online.
]]

require "SCP_System"
require "SCP_Doors"
require "SCP_Facility_Layout"

SCP.SCP079 = SCP.SCP079 or {}
local S079 = SCP.SCP079
local F = SCP.Facility

S079.RADIO_FREQ = 107900
S079.GENERATORS = 3
local DOOR_RANGE = 12
local BLACKOUT_HOURS = 0.08   -- about 5 in-game minutes

function S079.state()
    local w = SCP.world()
    w.scp079 = w.scp079 or { gens = {}, contained = false, blackoutUntil = 0 }
    return w.scp079
end

local function now() return getGameTime():getWorldAgeHours() end

local function sync()
    if isServer() then ModData.transmit("SCPFoundation") end
end

function S079.isActive()
    return F.origin() ~= nil and not S079.state().contained
end

------------------------------------------------------------------------
-- Actions
------------------------------------------------------------------------

local function hackDoor(player)
    local world = SCP.world()
    local px, py, pz = player:getX(), player:getY(), math.floor(player:getZ())
    local candidates = {}
    for key, level in pairs(world.doors or {}) do
        local x, y, z = key:match("(-?%d+),(-?%d+),(-?%d+)")
        x, y, z = tonumber(x), tonumber(y), tonumber(z)
        if z == pz and math.abs(x - px) <= DOOR_RANGE and math.abs(y - py) <= DOOR_RANGE then
            candidates[#candidates + 1] = { x = x, y = y, z = z, level = level }
        end
    end
    if #candidates == 0 then return false end
    local c = candidates[ZombRand(#candidates) + 1]
    local door = SCP.Doors.find(c.x, c.y, c.z)
    if not door then return false end
    local lock = not door:isLocked()
    SCP.Doors.setLocked(door, lock)
    SCP.sendToClients("DoorState", { x = c.x, y = c.y, z = c.z, level = c.level, locked = lock })
    SCP.sendToClient(player, "SCP079Say", { key = lock and "UI_SCP_079_DoorLocked" or "UI_SCP_079_DoorOpened" })
    return true
end

local function alarm(player)
    local x, y, z = math.floor(player:getX()), math.floor(player:getY()), math.floor(player:getZ())
    addSound(nil, x, y, z, 60, 60)
    SCP.sendToClient(player, "SCP079Alarm", { x = x, y = y, z = z })
end

local function blackout(player)
    local st = S079.state()
    if now() < (st.blackoutUntil or 0) then return end
    st.blackoutUntil = now() + BLACKOUT_HOURS
    sync()
    SCP.sendToClients("SCP079Say", { key = "UI_SCP_079_Blackout" })
end

local function everyMinute()
    if isClient() or not S079.isActive() then return end
    for _, player in ipairs(SCP.allPlayers()) do
        if F.levelAt(player:getX(), player:getY(), player:getZ()) then
            local r = ZombRand(100)
            if r < 10 then
                hackDoor(player)
            elseif r < 16 then
                alarm(player)
            elseif r < 18 then
                blackout(player)
            end
        end
    end
end

Events.EveryOneMinute.Add(everyMinute)

------------------------------------------------------------------------
-- Radio (107.9 MHz)
------------------------------------------------------------------------

local channel = nil
local broadcastId = 0

local function onLoadRadioScripts(scriptManager, isNewGame)
    local ok, ch = pcall(function()
        return DynamicRadioChannel.new("SCP-079", S079.RADIO_FREQ, ChannelCategory.Other, "SCP079-RADIO")
    end)
    if ok and ch then
        pcall(function() scriptManager:AddChannel(ch, false) end)
        channel = ch
    else
        SCP.log("SCP-079 radio channel unavailable")
    end
end

if Events.OnLoadRadioScripts then Events.OnLoadRadioScripts.Add(onLoadRadioScripts) end

function S079.broadcast()
    if not channel then return end
    broadcastId = broadcastId + 1
    pcall(function()
        local bc = RadioBroadCast.new("SCP079-" .. broadcastId, -1, -1)
        local first = ZombRand(8) + 1
        for i = 0, 2 do
            local n = (first + i - 1) % 8 + 1
            bc:AddRadioLine(RadioLine.new(getText("UI_SCP_079_Radio" .. n), 0.55, 1.0, 0.55))
        end
        channel:setAiringBroadcast(bc)
    end)
end

Events.EveryHours.Add(function()
    if isClient() or not S079.isActive() then return end
    if ZombRand(3) == 0 then S079.broadcast() end
end)

------------------------------------------------------------------------
-- Re-containment
------------------------------------------------------------------------

local function gensOnline()
    local n = 0
    for i = 1, S079.GENERATORS do
        if S079.state().gens[i] then n = n + 1 end
    end
    return n
end

SCP.ServerCommands.SCP079Generator = function(player, args)
    local st = S079.state()
    if st.contained or st.gens[args.index] then return end
    st.gens[args.index] = true
    sync()
    SCP.sendToClients("SCP079Generator", { index = args.index, online = gensOnline(), x = args.x, y = args.y, z = args.z })
end

SCP.ServerCommands.SCP079Overcharge = function(player, args)
    local st = S079.state()
    if st.contained or gensOnline() < S079.GENERATORS then return end
    st.contained = true
    st.blackoutUntil = 0
    sync()
    SCP.sendToClients("SCP079Say", { key = "UI_SCP_079_Contained" })
    if SCP.Breach and SCP.Breach.isActive() then SCP.Breach.stop() end
end

-- A new breach brings SCP-079 back online.
function S079.reset()
    local st = S079.state()
    st.contained = false
    st.gens = {}
    sync()
end
