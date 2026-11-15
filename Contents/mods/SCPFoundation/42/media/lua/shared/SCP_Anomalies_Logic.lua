--[[
    Small anomalies found around the site (SCP wiki, CC BY-SA 3.0; the
    in-game effects are ours):
      SCP-207  cola: each sip = 1 in-game hour of running without tiring,
               but the body wears out while it lasts (stacks).
      SCP-268  cap: the dead ignore you for 15 seconds, then 2 minutes to recharge.
      SCP-330  candy bowl: take two candies, fine. The third takes your hands.
      SCP-005  skeleton key: counts as the highest keycard (SCP.keycardLevel).
      SCP-109  canteen: drink as much as you want.
      SCP-458  pizza box: a fresh slice every time it is opened.
      SCP-427  locket: heals while it is open, but too long open and the
               flesh starts to change (heavy damage).
      SCP-018  super ball: thrown, it bounces faster and faster for a few
               seconds and hurts whatever it hits, its thrower included.
    The use actions are in client/SCP_Anomalies_Client.lua; SCP.Anomalies.use
    runs on the side that owns the player (single player, or the server).
]]

require "SCP_System"

SCP.Anomalies = SCP.Anomalies or {}
local A = SCP.Anomalies

local CAP_TIME_MS = 15000
local CAP_COOLDOWN_MS = 120000

local function try(obj, method, ...)
    if obj and obj[method] then
        local ok, res = pcall(obj[method], obj, ...)
        if ok then return res end
    end
    return nil
end

local function now() return getGameTime():getWorldAgeHours() end

local function bodyPart(player, name)
    local bd = player:getBodyDamage()
    local t = BodyPartType and BodyPartType[name]
    if not bd or not t then return nil end
    return try(bd, "getBodyPart", t)
end

------------------------------------------------------------------------
-- Effects
------------------------------------------------------------------------

local effects = {}

effects["Base.SCP_207"] = function(player, item)
    local md = player:getModData()
    md.SCP207 = (md.SCP207 or 0) + 1
    md.SCP207_Until = math.max(md.SCP207_Until or 0, now()) + 1
    SCP.setStat(player, "THIRST", math.max(0, SCP.getStat(player, "THIRST") - 0.2))
    if item.UseAndSync then item:UseAndSync() else item:Use() end
    SCP.say(player, "UI_SCP_207_Drink", 255, 120, 90)
end

effects["Base.SCP_268"] = function(player, item)
    local md = player:getModData()
    local t = getTimestampMs()
    if md.SCP268_Ready and t < md.SCP268_Ready then
        SCP.say(player, "UI_SCP_268_Recharging", 200, 200, 200)
        return
    end
    md.SCP268_Until = t + CAP_TIME_MS
    md.SCP268_Ready = t + CAP_TIME_MS + CAP_COOLDOWN_MS
    try(player, "setGhostMode", true)
    SCP.say(player, "UI_SCP_268_On", 160, 200, 255)
end

effects["Base.SCP_330"] = function(player, item)
    local md = player:getModData()
    md.SCP330 = (md.SCP330 or 0) + 1
    if md.SCP330 <= 2 then
        player:getInventory():AddItem("Base.SCP_330_Candy")
        SCP.say(player, md.SCP330 == 1 and "UI_SCP_330_Take1" or "UI_SCP_330_Take2", 255, 200, 230)
        return
    end
    -- the third one: both hands are cut off
    md.SCP330 = 0
    for _, name in ipairs({ "Hand_L", "Hand_R" }) do
        local part = bodyPart(player, name)
        if part then
            try(part, "setDeepWounded", true)
            try(part, "setDeepWoundTime", 30)
            try(part, "setBleeding", true)
            try(part, "setBleedingTime", 30)
            try(part, "setAdditionalPain", 100)
            try(part, "AddDamage", 60)
        end
    end
    try(player, "setPrimaryHandItem", nil)
    try(player, "setSecondaryHandItem", nil)
    SCP.setStat(player, "PANIC", 1)
    SCP.setStat(player, "PAIN", 1)
    player:playSound("SCP_330_Hands")
    SCP.say(player, "UI_SCP_330_Hands", 255, 60, 60)
end

effects["Base.SCP_109_Canteen"] = function(player, item)
    SCP.setStat(player, "THIRST", 0)
    SCP.say(player, "UI_SCP_109_Drink", 140, 200, 255)
end

effects["Base.SCP_458_PizzaBox"] = function(player, item)
    SCP.setStat(player, "HUNGER", math.max(0, SCP.getStat(player, "HUNGER") - 0.35))
    SCP.setStat(player, "BOREDOM", math.max(0, SCP.getStat(player, "BOREDOM") - 0.2))
    SCP.say(player, "UI_SCP_458_Eat", 255, 210, 120)
end

effects["Base.SCP_427"] = function(player, item)
    local md = player:getModData()
    md.SCP427_Open = not md.SCP427_Open
    SCP.say(player, md.SCP427_Open and "UI_SCP_427_Open" or "UI_SCP_427_Close", 200, 255, 200)
end

-- SCP-018: the ball leaves the inventory and bounces around the thrower.
local balls = {}
effects["Base.SCP_018"] = function(player, item)
    local inv = item:getContainer() or player:getInventory()
    if player:getPrimaryHandItem() == item then player:setPrimaryHandItem(nil) end
    if player:getSecondaryHandItem() == item then player:setSecondaryHandItem(nil) end
    if inv.DoRemoveItem then inv:DoRemoveItem(item) else inv:Remove(item) end
    if isServer() and sendRemoveItemFromContainer then pcall(sendRemoveItemFromContainer, inv, item) end
    table.insert(balls, { player = player, x = player:getX(), y = player:getY(), z = player:getZ(),
                          left = 20, next = 0, speed = 1 })
    SCP.say(player, "UI_SCP_018_Throw", 255, 160, 80)
end

local function zombiesNear(x, y, z, r)
    local out = {}
    local list = getCell():getZombieList()
    for i = 0, list:size() - 1 do
        local zb = list:get(i)
        if math.floor(zb:getZ()) == math.floor(z) and math.abs(zb:getX() - x) < r and math.abs(zb:getY() - y) < r then
            out[#out + 1] = zb
        end
    end
    return out
end

local function updateBalls()
    if #balls == 0 then return end
    local t = getTimestampMs()
    for i = #balls, 1, -1 do
        local b = balls[i]
        if t >= b.next then
            b.left = b.left - 1
            b.speed = b.speed + 0.25
            b.next = t + math.max(90, 350 / b.speed)
            local p = b.player
            if p and not p:isDead() then p:playSound("SCP_018_Bounce") end
            local targets = zombiesNear(b.x, b.y, b.z, 7)
            local hitPlayer = p and not p:isDead() and ZombRand(100) < 8
            if hitPlayer then
                local part = bodyPart(p, ({ "Head", "Torso_Upper", "UpperArm_L", "UpperLeg_R" })[ZombRand(4) + 1])
                if part then
                    try(part, "AddDamage", 8 * b.speed)
                    try(part, "setScratched", true, true)
                end
                SCP.say(p, "UI_SCP_018_Ouch", 255, 90, 90)
            elseif #targets > 0 then
                local zb = targets[ZombRand(#targets) + 1]
                try(zb, "setHealth", zb:getHealth() - 0.15 * b.speed)
                if b.speed > 2 then try(zb, "setKnockedDown", true) end
                if zb:getHealth() <= 0 then try(zb, "Kill", p) end
            end
            if b.left <= 0 then
                -- it stops: drop the ball near where it was thrown
                local sq = getCell():getGridSquare(math.floor(b.x + ZombRand(-2, 3)), math.floor(b.y + ZombRand(-2, 3)), math.floor(b.z))
                    or getCell():getGridSquare(math.floor(b.x), math.floor(b.y), math.floor(b.z))
                if sq then pcall(sq.AddWorldInventoryItem, sq, "Base.SCP_018", 0.5, 0.5, 0) end
                table.remove(balls, i)
            end
        end
    end
end
SCP.on("OnTick", updateBalls)

-- What each anomaly's action is called, its animation and length (ticks).
A.ACTIONS = {
    ["Base.SCP_207"] = { text = "ContextMenu_SCP_207", anim = "Drink", time = 60, sound = "SCP_207_Open" },
    ["Base.SCP_268"] = { text = "ContextMenu_SCP_268", anim = "WearClothing", time = 30 },
    ["Base.SCP_330"] = { text = "ContextMenu_SCP_330", anim = "Loot", time = 40 },
    ["Base.SCP_109_Canteen"] = { text = "ContextMenu_SCP_109", anim = "Drink", time = 80 },
    ["Base.SCP_458_PizzaBox"] = { text = "ContextMenu_SCP_458", anim = "Eat", time = 120 },
    ["Base.SCP_427"] = { text = "ContextMenu_SCP_427", anim = "Loot", time = 20 },
    ["Base.SCP_018"] = { text = "ContextMenu_SCP_018", anim = "Loot", time = 15 },
}

function A.use(player, item)
    if not player or player:isDead() or not item then return end
    local fn = effects[item:getFullType()]
    if fn then fn(player, item) end
end

------------------------------------------------------------------------
-- What lasts: SCP-207 and SCP-268
------------------------------------------------------------------------

local function update207(player)
    local md = player:getModData()
    if not md.SCP207 or md.SCP207 <= 0 then return end
    if now() > (md.SCP207_Until or 0) then
        md.SCP207, md.SCP207_Until = 0, nil
        SCP.say(player, "UI_SCP_207_End", 200, 200, 200)
        return
    end
    -- never out of breath ...
    SCP.setStat(player, "ENDURANCE", 1)
    -- ... but the heart pays for it
    local bd = player:getBodyDamage()
    try(bd, "ReduceGeneralHealth", 0.15 * md.SCP207)
    if md.SCP207 >= 4 and ZombRand(30) == 0 then
        SCP.say(player, "UI_SCP_207_Heart", 255, 90, 90)
    end
end

local function update427(player)
    local md = player:getModData()
    if not md.SCP427_Open then
        md.SCP427_Time = math.max(0, (md.SCP427_Time or 0) - 0.5)   -- the body slowly recovers
        return
    end
    md.SCP427_Time = (md.SCP427_Time or 0) + 1
    local bd = player:getBodyDamage()
    if md.SCP427_Time < 40 then
        try(bd, "AddGeneralHealth", 4)
        local parts = bd:getBodyParts()
        for i = 0, parts:size() - 1 do
            local part = parts:get(i)
            try(part, "setBleedingTime", math.max(0, (try(part, "getBleedingTime") or 0) - 2))
        end
        if md.SCP427_Time == 30 then SCP.say(player, "UI_SCP_427_Warn", 255, 200, 120) end
    else
        try(bd, "ReduceGeneralHealth", 3)
        SCP.setStat(player, "PAIN", 0.8)
        if ZombRand(10) == 0 then SCP.say(player, "UI_SCP_427_Mutate", 255, 80, 80) end
    end
end

local function update268(player)
    local md = player:getModData()
    if md.SCP268_Until and getTimestampMs() > md.SCP268_Until then
        md.SCP268_Until = nil
        try(player, "setGhostMode", false)
        SCP.say(player, "UI_SCP_268_Off", 200, 200, 200)
    end
end

SCP.on("EveryOneMinute", function()
    for _, player in ipairs(isServer() and SCP.allPlayers() or SCP.localPlayers()) do
        update207(player)
        update427(player)
    end
end)

SCP.on("OnPlayerUpdate", function(player)
    if player and not isClient() or (player and player:isLocalPlayer()) then update268(player) end
end)
