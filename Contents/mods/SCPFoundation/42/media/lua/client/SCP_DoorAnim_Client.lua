--[[
    Site doors slide instead of popping open: when a door of the site near
    a local player opens or closes, it shows three in-between frames
    (tiles made by tools/make_facility_tiles.py, ANIM0) before its real
    open or closed tile. Purely visual, on this machine only.
]]

require "SCP_System"

local SHEET = "scp_facility_02_"
-- first tile of each door kind on the sheet: +0 W closed, +1 N closed, +2 W open, +3 N open
local KINDS = { { base = 24, ms = 60 }, { base = 28, ms = 80 }, { base = 80, ms = 140 }, { base = 200, ms = 90 } }   -- standard, heavy, gate, lift
local ANIM0 = 272
local SCAN_MS = 400
local RADIUS = 12

local byIndex = {}
for k, kind in ipairs(KINDS) do
    for i = 0, 3 do
        byIndex[kind.base + i] = { kind = k, side = i % 2, open = i >= 2 }
    end
end

local doors = {}          -- door object -> { info, open }
local anims = {}          -- door object -> { info, opening, start }
local nextScan = 0

local function spriteIndex(obj)
    local sp = obj:getSprite()
    local name = sp and sp:getName()
    if not name or name:sub(1, #SHEET) ~= SHEET then return nil end
    return tonumber(name:sub(#SHEET + 1))
end

local function isOpen(door)
    if door.IsOpen then return door:IsOpen() end
    if door.isOpen then return door:isOpen() end
    return false
end

local function setTile(door, index)
    local sp = getSprite(SHEET .. index)
    if sp then pcall(door.setSprite, door, sp) end
end

local function finalIndex(info, open)
    return KINDS[info.kind].base + info.side + (open and 2 or 0)
end

local function scan()
    local seen = {}
    for _, p in ipairs(SCP.localPlayers()) do
        local px, py, pz = math.floor(p:getX()), math.floor(p:getY()), math.floor(p:getZ())
        for x = px - RADIUS, px + RADIUS do
            for y = py - RADIUS, py + RADIUS do
                local sq = getCell():getGridSquare(x, y, pz)
                if sq then
                    local objs = sq:getObjects()
                    for i = 0, objs:size() - 1 do
                        local o = objs:get(i)
                        if instanceof(o, "IsoDoor") or (instanceof(o, "IsoThumpable") and o:isDoor()) then
                            if anims[o] then
                                seen[o] = true
                            else
                                local info = byIndex[spriteIndex(o) or -1]
                                if info then
                                    seen[o] = true
                                    if not doors[o] then doors[o] = { info = info, open = isOpen(o) } end
                                end
                            end
                        end
                    end
                end
            end
        end
    end
    for o in pairs(doors) do
        if not seen[o] then doors[o] = nil end
    end
end

SCP.on("OnTick", function()
    local t = getTimestampMs()
    if t >= nextScan then
        nextScan = t + SCAN_MS
        scan()
    end
    for door, d in pairs(doors) do
        local open = isOpen(door)
        if open ~= d.open then
            d.open = open
            anims[door] = { info = d.info, opening = open, start = t }
        end
    end
    for door, a in pairs(anims) do
        local step = math.floor((t - a.start) / KINDS[a.info.kind].ms) + 1      -- 1, 2, 3, then done
        if step > 3 then
            setTile(door, finalIndex(a.info, isOpen(door)))
            anims[door] = nil
        else
            local frame = a.opening and step or (4 - step)
            setTile(door, ANIM0 + 6 * (a.info.kind - 1) + 3 * a.info.side + frame - 1)
        end
    end
end)
