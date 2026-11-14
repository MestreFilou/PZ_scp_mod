--[[
    Lighting of the SCP site (client side, rebuilt every session).
    One ceiling light per room near the player:
      normal         : white
      breach         : dim red emergency lighting
      SCP-079 cut    : off
      after the Alpha Warhead : off
]]

require "SCP_System"
require "SCP_Facility_Layout"

local F = SCP.Facility
local RANGE = 36
local lights = {}   -- key -> { light = IsoLightSource, mode = string }

local function mode()
    local md = ModData.get("SCPFoundation")
    if not md then return "normal" end
    if md.facility and md.facility.destroyed then return "off" end
    local now = getGameTime():getWorldAgeHours()
    if md.scp079 and md.scp079.blackoutUntil and now < md.scp079.blackoutUntil then return "off" end
    if md.breach and md.breach.active then return "red" end
    return "normal"
end

local COLORS = { normal = { 0.9, 0.9, 0.85, 9 }, red = { 0.7, 0.05, 0.05, 6 } }

local function removeLight(key)
    local l = lights[key]
    if l then
        pcall(function() getCell():removeLamppost(l.light) end)
        lights[key] = nil
    end
end

local function clearAll()
    for key in pairs(lights) do removeLight(key) end
end

local function refresh()
    local player = getSpecificPlayer(0)
    local o = F.origin()
    if not player or not o then clearAll() return end
    local level = F.levelAt(player:getX(), player:getY(), player:getZ())
    if not level then clearAll() return end
    local m = mode()
    local wanted = {}
    if m ~= "off" then
        local mid = math.floor(F.ROOM / 2)
        local z = o.z + level.depth
        for cy = 0, #level.rows - 1 do
            for cx = 0, #level.rows[1] - 1 do
                if F.solid(F.charAt(level, cx, cy)) then
                    local x, y = o.x + cx * F.ROOM + mid, o.y + cy * F.ROOM + mid
                    if math.abs(x - player:getX()) < RANGE and math.abs(y - player:getY()) < RANGE then
                        wanted[x .. "," .. y .. "," .. z] = { x = x, y = y, z = z }
                    end
                end
            end
        end
    end
    for key, l in pairs(lights) do
        if not wanted[key] or l.mode ~= m then removeLight(key) end
    end
    local c = COLORS[m]
    for key, p in pairs(wanted) do
        if not lights[key] and c then
            local ok, light = pcall(IsoLightSource.new, p.x, p.y, p.z, c[1], c[2], c[3], c[4])
            if ok and light then
                getCell():addLamppost(light)
                lights[key] = { light = light, mode = m }
            end
        end
    end
end

local nextRefresh = 0
Events.OnTick.Add(function()
    local t = getTimestampMs()
    if t < nextRefresh then return end
    nextRefresh = t + 1000
    refresh()
end)
