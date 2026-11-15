--[[
    Lighting of the SCP site (client side, rebuilt every session).
    The site is underground, so without these lights it is pitch black.
      - the lights of the plan (one per room, one every 5 tiles of hallway)
        near the player, coloured by zone:
          normal : white / yellowish      breach : dim red emergency lighting
          SCP-079 blackout / after the Alpha Warhead : off
      - a faint glow around the player while inside the site (emergency
        floor strips), so the site is never completely black, even during
        a blackout.
    After lights change, the chunks around them are flagged so the lighting
    pass recomputes the squares (new underground squares are not lit
    otherwise).
]]

require "SCP_System"
require "SCP_Facility_Layout"

local F = SCP.Facility
local D = F.Data
local RANGE = 26
local lights = {}   -- key -> { light = IsoLightSource, mode = string }
local glow = nil    -- { light, x, y, z, mode }

local function mode()
    local md = ModData.get("SCPFoundation")
    if not md then return "normal" end
    if md.facility and md.facility.destroyed then return "off" end
    local now = getGameTime():getWorldAgeHours()
    if md.scp079 and md.scp079.blackoutUntil and now < md.scp079.blackoutUntil then return "off" end
    if md.breach and md.breach.active then return "red" end
    return "normal"
end

-- r, g, b, radius. Lights stand about 5 tiles apart and walls stop them,
-- so every room and every stretch of hallway has its own.
local COLORS = {
    normal = {
        L = { 0.85, 0.85, 0.8, 7 },      -- Light Containment: white strip lights
        H = { 0.7, 0.6, 0.48, 7 },       -- Heavy Containment: dim, yellowish
        E = { 0.9, 0.9, 0.86, 7 },       -- Entrance Zone: bright offices
        S = { 0.8, 0.75, 0.6, 9 },       -- surface compound: floodlights
    },
    red = {
        L = { 0.75, 0.08, 0.05, 6 }, H = { 0.75, 0.08, 0.05, 6 }, E = { 0.75, 0.08, 0.05, 6 },
        S = { 0.75, 0.08, 0.05, 8 },
    },
}
local GLOW = { normal = { 0.45, 0.45, 0.42, 5 }, red = { 0.5, 0.1, 0.08, 5 }, off = { 0.25, 0.25, 0.3, 3 } }

local function relight(x, y, z)
    local sq = getCell():getGridSquare(x, y, z)
    local chunk = sq and sq.getChunk and sq:getChunk()
    if chunk and chunk.checkLightingLater_AllPlayers_AllLevels then
        pcall(chunk.checkLightingLater_AllPlayers_AllLevels, chunk)
    end
end

local function newLight(x, y, z, c)
    local ok, light = pcall(IsoLightSource.new, x, y, z, c[1], c[2], c[3], c[4])
    if not ok or not light then return nil end
    getCell():addLamppost(light)
    relight(x, y, z)
    return light
end

local function dropLight(light)
    if light then pcall(function() getCell():removeLamppost(light) end) end
end

local function removeLight(key)
    local l = lights[key]
    if l then
        dropLight(l.light)
        relight(l.x, l.y, l.z)
        lights[key] = nil
    end
end

local function clearAll()
    for key in pairs(lights) do removeLight(key) end
    if glow then dropLight(glow.light); glow = nil end
end

local function updateGlow(player, m)
    local x, y, z = math.floor(player:getX()), math.floor(player:getY()), math.floor(player:getZ())
    if glow and glow.x == x and glow.y == y and glow.z == z and glow.mode == m then return end
    if glow then dropLight(glow.light) end
    local light = newLight(x, y, z, GLOW[m])
    glow = light and { light = light, x = x, y = y, z = z, mode = m } or nil
end

local function refresh()
    local player = getSpecificPlayer(0)
    if not player then clearAll() return end
    local lx, ly, o = F.toLocal(player:getX(), player:getY())
    local level = lx and F.planLevel(player:getZ(), o)
    if not level then clearAll() return end
    local surface = level == D.surface
    if surface and F.charAt(level, "floor", lx, ly) == " " then clearAll() return end
    local m = mode()
    if surface then
        if glow then dropLight(glow.light); glow = nil end
    else
        updateGlow(player, m)
    end

    local wanted = {}
    local colors = COLORS[m]
    if colors then
        local z = surface and 0 or o.z
        for _, p in ipairs(level.lights) do
            if math.abs(p.x - lx) < RANGE and math.abs(p.y - ly) < RANGE then
                local zone = surface and "S" or F.charAt(level, "zone", p.x, p.y)
                wanted[p.x .. "," .. p.y .. "," .. z] = { x = o.x + p.x, y = o.y + p.y, z = z, c = colors[zone] or colors.L }
            end
        end
    end
    for key, l in pairs(lights) do
        if not wanted[key] or l.mode ~= m then removeLight(key) end
    end
    for key, p in pairs(wanted) do
        if not lights[key] then
            local light = newLight(p.x, p.y, p.z, p.c)
            if light then lights[key] = { light = light, mode = m, x = p.x, y = p.y, z = p.z } end
        end
    end
end

local nextRefresh = 0
SCP.on("OnTick", function()
    local t = getTimestampMs()
    if t < nextRefresh then return end
    nextRefresh = t + 250
    refresh()
end)
