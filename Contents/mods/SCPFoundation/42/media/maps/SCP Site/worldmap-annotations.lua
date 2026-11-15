-- Label of the SCP site on the world map (keep in step with SCP.Facility.FIXED_GATE).
return function(mapUI)
    local ok, mapAPI = pcall(function() return mapUI.javaObject:getAPIv3() end)
    if not ok or not mapAPI then return end
    local symbolsAPI = mapAPI:getSymbolsAPIv2()
    -- the label style names come from the game; the river style is the one known for sure
    for _, style in ipairs({ "text-town", "text-water-nofade" }) do
        local done, symbol = pcall(symbolsAPI.addUntranslatedText, symbolsAPI, "SITE SCP", style, 12222, 8232)
        if done and symbol then
            pcall(function()
                symbol:setRGBA(0.6, 0.05, 0.05, 1.0)
                symbol:setAnchor(0.5, 0.5)
                symbol:setScale(3.0)
                symbol:setRotation(0.0)
                symbol:setMatchPerspective(true)
                symbol:setApplyZoom(true)
                symbol:setMinZoom(0.0)
            end)
            return
        end
    end
end
