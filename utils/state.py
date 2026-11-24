import json
import secrets

from db.redis import Redis

OAUTH_STATE_TTL = 600

async def create_oauth_state(redis: Redis, telegram_id:int)-> str:
    state = secrets.token_urlsafe(32)
    state_data = {
        "telegram_id": telegram_id,
        "provider": "gmail"
    }

    await redis.set(
        f"oauth:state:{state}",
        json.dumps(state_data),
        ex=OAUTH_STATE_TTL,
    )
    return state

async def consume_oauth_state(redis: Redis, state: str)-> dict|None:
    # GETDEL retrieves and deletes the key atomically.
    value = await redis.getdel(f"oauth:state:{state}")

    if value is None:
        return None

    return json.loads(value)