import sqlite3
import datetime

# HATA 1: Hardcoded Secret
API_SECRET = "sk_test_super_secret_token_123"

def get_user_data(email: str):
    # HATA 2: Naive Datetime kullanımı
    login_time = datetime.datetime.now()
    
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    
    # HATA 3: SQL Injection riski
    query = "SELECT * FROM users WHERE email = '" + email + "'"
    cursor.execute(query)
    
    return cursor.fetchall()
