import os 
from redis.asyncio import Redis

redis_client: Redis | None = None

async def connect_redis():
    global redis_client
    redis_client = Redis.from_url(
        os.environ["REDIS_URL"],
        decode_responses=True,
    )

    await redis_client.ping()

async def close_redis():
    global redis_client

    if redis_client:
        await redis_client.aclose()
        redis_client = None

def get_redis()-> Redis:
    if redis_client is None:
        raise RuntimeError("Redis connection not initialized")

    return redis_client