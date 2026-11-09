--[[
    Blink meter. While an SCP-173 is near, the player's eyes dry out:
    the meter empties over BlinkInterval seconds, then the player blinks
    (screen goes black for a moment) and SCP-173 is free to move.
    Press the blink key (default B) to blink early and reset the meter.
]]

require "SCP_System"
require "ISUI/ISUIElement"

SCP.Blink = SCP.Blink or {}

local BLINK_MS = 350          -- how long the eyes stay closed
local THREAT_TIMEOUT_MS = 2000 -- meter hides after this long without a 173 nearby

local state = {}              -- playerNum -> { meter, blinkUntil, threatAt }

local function now() return getTimestampMs() end

local function get(playerNum)
    local s = state[playerNum]
    if not s then
        s = { meter = 1, blinkUntil = 0, threatAt = 0 }
        state[playerNum] = s
    end
    return s
end

function SCP.Blink.isBlinking(player)
    return now() < get(player:getPlayerNum()).blinkUntil
end

-- Called by SCP-173 code every update while one is nearby.
function SCP.Blink.setThreat(player)
    get(player:getPlayerNum()).threatAt = now()
end

function SCP.Blink.blink(player)
    local s = get(player:getPlayerNum())
    s.blinkUntil = now() + BLINK_MS
    s.meter = 1
end

function SCP.Blink.isThreatened(player)
    return now() - get(player:getPlayerNum()).threatAt < THREAT_TIMEOUT_MS
end

local lastTick = nil
local function onTick()
    local t = now()
    local dt = lastTick and (t - lastTick) or 0
    lastTick = t
    local interval = math.max(1, SCP.opt("BlinkInterval")) * 1000
    for _, player in ipairs(SCP.localPlayers()) do
        local s = get(player:getPlayerNum())
        if t - s.threatAt < THREAT_TIMEOUT_MS then
            if t >= s.blinkUntil then
                s.meter = s.meter - dt / interval
                if s.meter <= 0 then SCP.Blink.blink(player) end
            end
        else
            s.meter = 1
        end
    end
end

Events.OnTick.Add(onTick)

------------------------------------------------------------------------
-- UI
------------------------------------------------------------------------

-- Small meter at the top of the screen. It never covers the world, so it
-- does not eat mouse clicks.
SCPBlinkUI = ISUIElement:derive("SCPBlinkUI")

local BAR_W, BAR_H = 260, 14

function SCPBlinkUI:new(playerNum)
    local x = (getCore():getScreenWidth() - BAR_W) / 2
    local o = ISUIElement.new(self, x, 40, BAR_W, BAR_H + 22)
    o.playerNum = playerNum
    return o
end

function SCPBlinkUI:render()
    local player = getSpecificPlayer(self.playerNum)
    if not player or player:isDead() then return end
    local s = get(self.playerNum)
    if now() - s.threatAt >= THREAT_TIMEOUT_MS then return end
    local m = math.max(0, math.min(1, s.meter))
    self:drawTextCentre(getText("UI_SCP_BlinkMeter"), BAR_W / 2, 0, 1, 1, 1, 1, UIFont.Small)
    self:drawRect(0, 18, BAR_W, BAR_H + 4, 0.7, 0, 0, 0)
    self:drawRect(2, 20, (BAR_W - 4) * m, BAR_H, 0.9, 1 - m, 0.3 + 0.6 * m, 0.2)
end

-- Full-screen black overlay, only visible during the blink itself.
SCPBlinkOverlay = ISUIElement:derive("SCPBlinkOverlay")

function SCPBlinkOverlay:new(playerNum)
    local o = ISUIElement.new(self, 0, 0, getCore():getScreenWidth(), getCore():getScreenHeight())
    o.playerNum = playerNum
    return o
end

function SCPBlinkOverlay:render()
    self:drawRect(0, 0, self:getWidth(), self:getHeight(), 1, 0, 0, 0)
end

local panels = {}

local function ensurePanel(playerNum)
    if panels[playerNum] then return end
    local bar = SCPBlinkUI:new(playerNum)
    bar:initialise()
    bar:addToUIManager()
    local overlay = SCPBlinkOverlay:new(playerNum)
    overlay:initialise()
    overlay:addToUIManager()
    overlay:setVisible(false)
    panels[playerNum] = { bar = bar, overlay = overlay }
end

Events.OnCreatePlayer.Add(function(playerNum) ensurePanel(playerNum) end)
Events.OnGameStart.Add(function() ensurePanel(0) end)

-- Show the overlay only while blinking.
Events.OnTick.Add(function()
    local t = now()
    for playerNum, p in pairs(panels) do
        local blinking = t < get(playerNum).blinkUntil
        if p.overlay:getIsVisible() ~= blinking then p.overlay:setVisible(blinking) end
    end
end)

------------------------------------------------------------------------
-- Blink key (rebindable in the key options when supported)
------------------------------------------------------------------------

SCP.Blink.KEY_NAME = "SCP_Blink"
if keyBinding then
    table.insert(keyBinding, { value = "[SCPFoundation]" })
    table.insert(keyBinding, { value = SCP.Blink.KEY_NAME, key = Keyboard.KEY_B })
end

local function blinkKey()
    if getCore().getKey then
        local ok, k = pcall(getCore().getKey, getCore(), SCP.Blink.KEY_NAME)
        if ok and k and k > 0 then return k end
    end
    return Keyboard.KEY_B
end

Events.OnKeyPressed.Add(function(key)
    if key ~= blinkKey() then return end
    local player = getSpecificPlayer(0)
    if player and SCP.Blink.isThreatened(player) then SCP.Blink.blink(player) end
end)
