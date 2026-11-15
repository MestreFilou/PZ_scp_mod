--[[
    While a new character is on its way to its start room in the site, the
    screen stays black with a short line of text, so the random spawn point
    and the site being built are not seen. Gone after 45 seconds whatever
    happens.
]]

require "SCP_System"
require "ISUI/ISPanel"

local Overlay = ISPanel:derive("SCPStartOverlay")
local panel = nil
local shownAt = 0
local MAX_MS = 45000

function Overlay:prerender()
    self:setWidth(getCore():getScreenWidth())
    self:setHeight(getCore():getScreenHeight())
    self:drawRect(0, 0, self.width, self.height, 1, 0, 0, 0)
    local dots = string.rep(".", math.floor(getTimestampMs() / 400) % 4)
    local text = getText("UI_SCP_StartTransfer") .. dots
    local w = getTextManager():MeasureStringX(UIFont.Medium, text)
    self:drawText(text, (self.width - w) / 2, self.height / 2 - 10, 0.75, 0.82, 0.9, 1, UIFont.Medium)
end

local function show()
    if panel then return end
    panel = Overlay:new(0, 0, getCore():getScreenWidth(), getCore():getScreenHeight())
    panel:initialise()
    panel:addToUIManager()
    panel:setAlwaysOnTop(true)
    panel.moveWithMouse = false
    shownAt = getTimestampMs()
end

local function hide()
    if not panel then return end
    panel:removeFromUIManager()
    panel = nil
end

SCP.on("OnTick", function()
    local waiting = false
    for _, p in ipairs(SCP.localPlayers()) do
        if p:getModData().SCP_StartRoom then waiting = true end
    end
    if waiting and (not panel and shownAt == 0 or panel and getTimestampMs() - shownAt < MAX_MS) then
        show()
    else
        hide()
        if not waiting then shownAt = 0 end
    end
end)
