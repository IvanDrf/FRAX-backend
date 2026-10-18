from redis.asyncio import Redis

from core.config import settings

redis_client = Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB)


def get_redis_client():
    return redis_client
