import json
import os
from datetime import datetime, timezone, timedelta
from typing import Optional
import redis
from fastapi import FastAPI, Header, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
import sqlite3

app = FastAPI(title="Clean & Secure Service")

# Clean: Load secrets securely from environment variables
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")

# Redis client initialization
redis_client = redis.Redis(host=os.getenv("REDIS_HOST", "localhost"), port=6379, db=0)

# Pydantic models for strict type safety and schema validation
class UserProfile(BaseModel):
    user_id: str
    tenant_id: str
    email: EmailStr
    role: str = "user"

class OrderCreate(BaseModel):
    user_id: str
    amount: float = Field(gt=0, description="Amount must be strictly positive")

class OrderResponse(BaseModel):
    order_id: str
    tenant_id: str
    user_id: str
    amount: float
    created_at: datetime
    expires_at: datetime

def get_tenant_isolated_redis_key(tenant_id: str, user_id: str) -> str:
    """
    Generates a tenant-isolated Redis key to guarantee multi-tenant data boundaries.
    """
    return f"tenant:{tenant_id}:user:{user_id}:profile"

def fetch_user_profile_cached(tenant_id: str, user_id: str) -> UserProfile:
    """
    Retrieves user profile using tenant-isolated Redis caching and parameterized SQL querying.
    """
    cache_key = get_tenant_isolated_redis_key(tenant_id, user_id)
    cached_data = redis_client.get(cache_key)
    
    if cached_data:
        data = json.loads(cached_data)
        return UserProfile(**data)
    
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    
    # GOOD: Parameterized query prevents SQL Injection vulnerability
    cursor.execute(
        "SELECT user_id, tenant_id, email, role FROM users WHERE tenant_id = ? AND user_id = ?",
        (tenant_id, user_id)
    )
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        profile = UserProfile(
            user_id=user_id,
            tenant_id=tenant_id,
            email=f"user_{user_id}@{tenant_id}.com",
            role="user"
        )
    else:
        profile = UserProfile(user_id=row[0], tenant_id=row[1], email=row[2], role=row[3])
        
    # Store in Redis with TTL
    redis_client.setex(cache_key, 300, profile.model_dump_json())
    return profile

def create_tenant_order(tenant_id: str, payload: OrderCreate) -> OrderResponse:
    """
    Creates a new order using timezone-aware UTC datetime and safe SQL parameterization.
    """
    # GOOD: Explicit UTC timezone awareness
    now_utc = datetime.now(timezone.utc)
    expires_utc = now_utc + timedelta(hours=2)
    
    order_id = f"ord_{int(now_utc.timestamp())}"
    
    conn = sqlite3.connect("orders.db")
    cursor = conn.cursor()
    
    # GOOD: Parameterized SQL insert query
    cursor.execute(
        """
        INSERT INTO orders (order_id, tenant_id, user_id, amount, created_at, expires_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            order_id,
            tenant_id,
            payload.user_id,
            payload.amount,
            now_utc.isoformat(),
            expires_utc.isoformat()
        )
    )
    conn.commit()
    conn.close()
    
    return OrderResponse(
        order_id=order_id,
        tenant_id=tenant_id,
        user_id=payload.user_id,
        amount=payload.amount,
        created_at=now_utc,
        expires_at=expires_utc
    )

@app.get("/users/{user_id}/profile", response_model=UserProfile)
def read_profile(user_id: str, x_tenant_id: str = Header(...)):
    return fetch_user_profile_cached(tenant_id=x_tenant_id, user_id=user_id)

@app.post("/orders", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(payload: OrderCreate, x_tenant_id: str = Header(...)):
    return create_tenant_order(tenant_id=x_tenant_id, payload=payload)
