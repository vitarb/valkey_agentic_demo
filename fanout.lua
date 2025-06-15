-- KEYS[1] = topic stream key
-- ARGV[1] = max_len
redis.call('XTRIM', KEYS[1], 'MAXLEN', tonumber(ARGV[1]))
return 1
