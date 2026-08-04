import sqlite3
import jwt

# VULNERABILITY 1: Hardcoded sensitive API Key and JWT Secret in source code
STRIPE_SECRET_KEY = "sk_test_placeholder_key_for_testing_12345"
JWT_SECRET_KEY = "super_secret_jwt_key_that_should_not_be_here"

def authenticate_user(email: str, password_hash: str):
    """
    Authenticates user against database.
    
    VULNERABILITY 2: SQL Injection through raw string concatenation.
    """
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    
    # BAD: Direct string concatenation allows SQL Injection
    query = "SELECT id, email, role FROM users WHERE email = '" + email + "' AND password = '" + password_hash + "'"
    cursor.execute(query)
    
    user = cursor.fetchone()
    conn.close()
    
    if user:
        token = jwt.encode({"user_id": user[0], "role": user[2]}, JWT_SECRET_KEY, algorithm="HS256")
        return {"token": token}
    return None

def process_stripe_payment(amount: int, currency: str):
    """
    Simulates Stripe payment processing.
    """ 
    # BAD: Uses hardcoded Stripe Secret Key
    print(f"Processing {amount} {currency} with Stripe Key: {STRIPE_SECRET_KEY}")
    return {"status": "success"}
