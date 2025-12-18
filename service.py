import redis

class CacheService:
    def __init__(self, redis_client=None):
        self.redis = redis_client or redis.Redis(host='localhost', port=6379, db=0)

    def get_or_compute(self, key: str, compute_func):
        cached = self.redis.get(key)
        if cached is not None:
            return cached.decode()
        value = compute_func()
        self.redis.setex(key, 60, value)
        return value