from datetime import datetime, timedelta
import sqlite3

def create_order(user_id: str, amount: float):
    """
    Creates an order and calculates payment expiration.
    
    VULNERABILITY:
    Uses naive datetime.now() without timezone specification (UTC).
    Server local time variance will cause inconsistency across distributed environments.
    """
    # BAD: Naive datetime! Server local time is used instead of UTC.
    created_at = datetime.now()
    expires_at = created_at + timedelta(hours=2)
    
    conn = sqlite3.connect("orders.db")
    cursor = conn.cursor()
    
    cursor.execute(
        "INSERT INTO orders (user_id, amount, created_at, expires_at) VALUES (?, ?, ?, ?)",
        (user_id, amount, created_at.isoformat(), expires_at.isoformat())
    )
    conn.commit()
    conn.close()
    
    return {
        "user_id": user_id,
        "amount": amount,
        "created_at": created_at,
        "expires_at": expires_at
    }

def is_order_expired(expires_at_str: str) -> bool:
    """
    Checks if an order has expired.
    
    VULNERABILITY: Comparing naive datetimes can give incorrect results if server timezone changes.
    """
    # BAD: Comparing naive datetimes
    expires_at = datetime.fromisoformat(expires_at_str)
    now = datetime.now()
    return now > expires_at
