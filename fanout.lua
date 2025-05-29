-- KEYS[1] topic stream key
-- ARGV[1] msg_id (stream entry id)
-- ARGV[2] topic
-- ARGV[3] summary_json
-- ARGV[4] feed_len
-- ARGV[5] max_len
local key   = 'user:topic:'..ARGV[2]
local users = redis.call('ZRANGE', key, 0, -1)   -- all user ids for topic

for _,u in ipairs(users) do
  local feed_key = 'feed:'..u
  redis.call('LPUSH', feed_key, ARGV[3])
  redis.call('LTRIM', feed_key, 0, tonumber(ARGV[4]) - 1)
end
redis.call('XTRIM', KEYS[1], 'MAXLEN', tonumber(ARGV[5]))
return #users

