--[[
    Containment breach on the client: alarm, red lights at every
    containment point, warning messages.
]]

require "SCP_System"

SCP.BreachClient = SCP.BreachClient or { lights = {}, active = false }
local B = SCP.BreachClient

local ALARM_EVERY_MS = 4000
local LIGHT_RADIUS = 12

local function clearLights()
    for _, l in ipairs(B.lights) do
        pcall(function() getCell():removeLamppost(l) end)
    end
    B.lights = {}
end

local function addLights(points)
    clearLights()
    for _, p in ipairs(points or {}) do
        local ok, light = pcall(IsoLightSource.new, p.x, p.y, p.z, 1.0, 0.05, 0.05, LIGHT_RADIUS)
        if ok and light then
            getCell():addLamppost(light)
            B.lights[#B.lights + 1] = light
        end
    end
end

SCP.ClientCommands.BreachStart = function(args)
    B.active = true
    B.points = args.points
    B.nextAlarm = 0
    addLights(args.points)
    for _, p in ipairs(SCP.localPlayers()) do
        SCP.say(p, "UI_SCP_BreachStart", 255, 40, 40)
        p:playSound("SCP_BreachVoice")
    end
end

SCP.ClientCommands.BreachPulse = function(args)
    if not B.active then SCP.ClientCommands.BreachStart(args) end
end

SCP.ClientCommands.BreachEnd = function(args)
    B.active = false
    clearLights()
    for _, p in ipairs(SCP.localPlayers()) do SCP.say(p, "UI_SCP_BreachEnd", 120, 255, 120) end
end

SCP.ClientCommands.Notify = function(args)
    local p = getPlayer()
    if p and args.key then SCP.say(p, args.key, 255, 255, 255) end
end

-- Siren near containment points; red lights blink.
Events.OnTick.Add(function()
    if not B.active then return end
    local t = getTimestampMs()
    if t < (B.nextAlarm or 0) then return end
    B.nextAlarm = t + ALARM_EVERY_MS
    for _, player in ipairs(SCP.localPlayers()) do
        for _, p in ipairs(B.points or {}) do
            local dx, dy = player:getX() - p.x, player:getY() - p.y
            if dx * dx + dy * dy < 60 * 60 then
                getSoundManager():PlayWorldSound("SCP_BreachAlarm", getCell():getGridSquare(p.x, p.y, p.z), 0, 120, 1, false)
                break
            end
        end
    end
    for _, l in ipairs(B.lights) do
        pcall(function() l:setActive(not l:isActive()) end)
    end
end)

-- Restore the effects after loading a save during a breach.
Events.OnGameStart.Add(function()
    local md = ModData.get("SCPFoundation")
    if md and md.breach and md.breach.active then
        SCP.ClientCommands.BreachStart({ points = md.points })
    end
end)

Events.OnReceiveGlobalModData.Add(function(key, data)
    if key ~= "SCPFoundation" or type(data) ~= "table" then return end
    ModData.add("SCPFoundation", data)
end)

if isClient() then
    Events.OnConnected.Add(function() ModData.request("SCPFoundation") end)
end
