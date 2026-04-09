import redis
import os
import json
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))

class RedisCache:
    def __init__(self):
        try:
            self.redis = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=REDIS_DB,
                decode_responses=True
            )
            # Test connection
            self.redis.ping()
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Falling back to no-cache.")
            self.redis = None

    def get(self, key: str) -> Optional[Any]:
        if not self.redis:
            return None
        try:
            value = self.redis.get(key)
            return json.loads(value) if value else None
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None

    def set(self, key: str, value: Any, expire: int = 86400): # Default 24h
        if not self.redis:
            return
        try:
            self.redis.set(key, json.dumps(value), ex=expire)
        except Exception as e:
            logger.error(f"Redis set error: {e}")

# Global singleton instance
cache = RedisCache()
