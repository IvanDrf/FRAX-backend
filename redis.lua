local result = {}
local cursor = "0"
repeat
    local scan = redis.call('SCAN', cursor, 'MATCH', 'session:*', 'COUNT', 100)
    cursor = scan[1]
    local keys = scan[2]
    for _, k in ipairs(keys) do
        local v = redis.call('GET', k)
        table.insert(result, k)
        table.insert(result, tostring(v))
    end
until cursor == "0"
return result