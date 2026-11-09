--[[
    SCP-096 "Shy Guy" - shared state machine.
      idle      : sits still and cries
      triggered : someone saw its face; screams for 5-10 seconds
      enraged   : sprints after that person, breaking doors and windows,
                  until the target dies (then goes back to idle)
    The state lives in the zombie's mod data and is broadcast to every client.
]]

require "SCP_System"

SCP.SCP096 = SCP.SCP096 or {}

local IDLE, TRIGGERED, ENRAGED = "idle", "triggered", "enraged"
SCP.SCP096.IDLE, SCP.SCP096.TRIGGERED, SCP.SCP096.ENRAGED = IDLE, TRIGGERED, ENRAGED

function SCP.SCP096.getState(zombie)
    return zombie:getModData().SCP096_State or IDLE
end

function SCP.SCP096.applyState(zombie, state, targetId, rageAt)
    local md = zombie:getModData()
    md.SCP096_State = state
    md.SCP096_Target = targetId
    md.SCP096_RageAt = rageAt
    md.SCP096_Screamed = nil
    if state == ENRAGED then
        SCP.makeSprinter(zombie)
        zombie:setHealth(math.max(zombie:getHealth(), 20))
    end
end

-- Server: a client reports that `player` saw 096's face.
SCP.ServerCommands.SCP096Trigger = function(player, args)
    local zombie = SCP.findZombie(args.key)
    if not zombie or SCP.SCP096.getState(zombie) ~= IDLE then return end
    local min, max = SCP.opt("SCP096TriggerMin"), SCP.opt("SCP096TriggerMax")
    local delay = (min + ZombRand(math.max(1, max - min + 1))) * 1000
    local rageAt = getTimestampMs() + delay
    local targetId = SCP.playerId(player)
    SCP.SCP096.applyState(zombie, TRIGGERED, targetId, rageAt)
    SCP.sendToClients("SCP096State", { key = args.key, state = TRIGGERED, target = targetId, delay = delay })
end

SCP.ServerCommands.SCP096SetState = function(player, args)
    local zombie = SCP.findZombie(args.key)
    if not zombie then return end
    SCP.SCP096.applyState(zombie, args.state, args.target, nil)
    SCP.sendToClients("SCP096State", { key = args.key, state = args.state, target = args.target })
end

SCP.ServerCommands.SCP096Smash = function(player, args)
    SCP.smashAround(args.x, args.y, args.z, 1)
end

-- Clients: keep a local copy of the state (the server's clock is not ours,
-- so the scream delay is sent as a duration).
SCP.ClientCommands.SCP096State = function(args)
    local zombie = SCP.findZombie(args.key)
    if not zombie then return end
    local rageAt = args.delay and (getTimestampMs() + args.delay) or nil
    SCP.SCP096.applyState(zombie, args.state, args.target, rageAt)
end
