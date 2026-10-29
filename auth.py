import hashlib
import sqlite3
from database import connect

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def register(username, password, role, group_id):
    conn = connect()
    cursor = conn.cursor()

    hashed = hash_password(password)

    try:
        cursor.execute("INSERT INTO users (username, password, role, group_id) VALUES (?, ?, ?, ?)",
                       (username, hashed, role, group_id))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()

def login(username, password):
    conn = connect()
    cursor = conn.cursor()

    hashed = hash_password(password)

    cursor.execute("SELECT * FROM users WHERE username=? AND password=?", (username, hashed))
    user = cursor.fetchone()
    conn.close()

    return user
