--[[
    Start scenarios of the SCP occupations (client side).
    New character: its gear, then a start room asked to the server, then a
    walk there once the room is built. See server/SCP_StartScenario.lua.
]]

require "SCP_System"
require "SCP_Professions"

local P = SCP.Professions

local RETRY_MS = 15000        -- no answer from the server: ask again
local MAX_TRIES = 4
local WARP_EVERY_MS = 10000   -- stand above the room again so it gets loaded and built
local GIVE_UP_MS = 120000     -- room never built: stay where we are

local function wear(player, fullType)
    local item = player:getInventory():AddItem("Base." .. fullType)
    if item then pcall(function() player:setWornItem(item:getBodyLocation(), item) end) end
end

SCP.on("OnNewGame", function(player, square)
    local id = P.getId(player)
    if not id then return end
    local def = P.List[id]
    for _, t in ipairs(def.wear) do wear(player, t) end
    for _, t in ipairs(def.give) do
        local full = t:find("%.") and t or ("Base." .. t)
        pcall(function() player:getInventory():AddItem(full) end)
    end
    player:getModData().SCP_Start = { prof = id, sent = getTimestampMs(), tries = 1 }
    SCP.sendToServer(player, "ScenarioRequest", { prof = id })
end)

SCP.ClientCommands.ScenarioGo = function(args)
    local player = SCP.playerById(args.pid) or getPlayer()
    if not player then return end
    local md = player:getModData()
    if not md.SCP_Start then return end
    if args.none then
        md.SCP_Start = nil
        SCP.say(player, "UI_SCP_Start_NoSite", 255, 200, 120)
        return
    end
    md.SCP_Start = {
        prof = args.prof, x0 = args.x0, y0 = args.y0, x1 = args.x1, y1 = args.y1,
        cx = args.cx, cy = args.cy, z = args.z, since = getTimestampMs(), warped = 0,
    }
end

-- A free square of the room to stand on (nearest to its centre), or nil.
local function freeSquare(s)
    local best, bestD = nil, 9999
    for x = s.x0, s.x1 do
        for y = s.y0, s.y1 do
            local sq = getCell():getGridSquare(x, y, s.z)
            if sq and sq:getFloor() then
                local ok, free = pcall(sq.isFree, sq, false)
                if ok and free then
                    local d = math.abs(x - s.cx) + math.abs(y - s.cy)
                    if d < bestD then best, bestD = sq, d end
                end
            end
        end
    end
    return best
end

local function arrive(player, s)
    local sq = freeSquare(s)
    local x, y = s.cx, s.cy
    if sq then x, y = sq:getX(), sq:getY() end
    SCP.teleport(player, x + 0.5, y + 0.5, s.z)
    player:getModData().SCP_Start = nil
    SCP.say(player, "UI_SCP_Start_" .. s.prof, 200, 220, 255)
    SCP.say(player, "UI_SCP_Goal_" .. s.prof, 255, 230, 120)
    SCP.sendToServer(player, "ScenarioArrived", {
        prof = s.prof, x0 = s.x0, y0 = s.y0, x1 = s.x1, y1 = s.y1, cx = s.cx, cy = s.cy, z = s.z,
    })
end

local nextCheck = 0
SCP.on("OnTick", function()
    local t = getTimestampMs()
    if t < nextCheck then return end
    nextCheck = t + 500
    for _, player in ipairs(SCP.localPlayers()) do
        local md = player:getModData()
        local s = md.SCP_Start
        if s and not s.x0 then
            -- Still waiting for the server.
            if t - (s.sent or 0) > RETRY_MS then
                if (s.tries or 1) >= MAX_TRIES then
                    md.SCP_Start = nil
                else
                    s.tries = (s.tries or 1) + 1
                    s.sent = t
                    SCP.sendToServer(player, "ScenarioRequest", { prof = s.prof })
                end
            end
        elseif s then
            local sq = getCell():getGridSquare(s.cx, s.cy, s.z)
            if sq and sq:getFloor() then
                arrive(player, s)
            elseif t - (s.since or t) > GIVE_UP_MS then
                md.SCP_Start = nil
                SCP.say(player, "UI_SCP_Start_NoSite", 255, 200, 120)
            elseif t - (s.warped or 0) > WARP_EVERY_MS then
                -- Stand above the room so the server loads and builds it.
                s.warped = t
                SCP.teleport(player, s.cx + 0.5, s.cy + 0.5, 0)
            end
        end
    end
end)
