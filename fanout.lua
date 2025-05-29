-- ARGV[1] id
-- ARGV[2] topic
-- ARGV[3] summary_json
-- ARGV[4] max_len
local key   = 'user:topic:'..ARGV[2]
local users = redis.call('ZRANGE', key, 0, -1)   -- all user ids for topic

for _,u in ipairs(users) do
  local feed_key = 'feed:'..u
  redis.call('LPUSH', feed_key, ARGV[3])
  redis.call('LTRIM', feed_key, 0, tonumber(ARGV[4]) - 1)
end
return #users

