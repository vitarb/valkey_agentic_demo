-- ARGV[1] id
-- ARGV[2] topic
-- ARGV[3] summary_json
-- ARGV[4] max_len
local key   = 'user:topic:'..ARGV[2]
local users = redis.call('ZRANGE', key, 0, -1)   -- all user ids for topic

for _,u in ipairs(users) do
  redis.call('LPUSH', 'feed:'..u, ARGV[3])
  redis.call('LTRIM', 'feed:'..u, 0, tonumber(ARGV[4]) - 1)
end
return #users

