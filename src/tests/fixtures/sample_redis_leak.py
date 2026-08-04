import json
import redis
from fastapi import FastAPI, Header, HTTPException

app = FastAPI()
redis_client = redis.Redis(host="localhost", port=6379, db=0)

def get_user_profile(user_id: str, tenant_id: str):
    """
    Fetch user profile with Redis caching.
    
    SECURITY VULNERABILITY:
    Redis key relies solely on user_id without namespace/isolation for tenant_id.
    In a multi-tenant setup, this allows cross-tenant data leakage.
    """
    # BAD: Cache key does not include tenant_id!
    cache_key = f"user:{user_id}:profile"
    
    cached_data = redis_client.get(cache_key)
    if cached_data:
        return json.loads(cached_data)
    
    # Simulate DB lookup
    user_profile = {
        "user_id": user_id,
        "tenant_id": tenant_id,
        "email": f"user_{user_id}@{tenant_id}.com",
        "role": "admin"
    }
    
    # Cache for 300 seconds
    redis_client.setex(cache_key, 300, json.dumps(user_profile))
    return user_profile

@app.get("/users/{user_id}/profile")
def read_profile(user_id: str, x_tenant_id: str = Header(...)):
    return get_user_profile(user_id=user_id, tenant_id=x_tenant_id)

# NOTE: Eğer asenkron bir FastAPI projesi yazıyorsan, senkron redis paketi yerine
# asenkron çalışan redis-py'ın async arayüzünü (from redis.asyncio import Redis)
# kullanmak uygulamanın I/O performansını katlar.