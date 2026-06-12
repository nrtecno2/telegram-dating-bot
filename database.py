import sqlite3

db = sqlite3.connect(
    "users.db",
    check_same_thread=False
)

cursor = db.cursor()

# Users Table

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
    user_id INTEGER PRIMARY KEY,
    name TEXT,
    gender TEXT,
    age INTEGER,
    location TEXT,
    about TEXT,
    preference TEXT,
    completed INTEGER DEFAULT 0
)
""")

# Media Table

cursor.execute("""
CREATE TABLE IF NOT EXISTS media(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    file_id TEXT,
    media_type TEXT
)
""")

# Likes Table

cursor.execute("""
CREATE TABLE IF NOT EXISTS likes(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_user INTEGER,
    to_user INTEGER
)
""")

# Notifications Table

cursor.execute("""
CREATE TABLE IF NOT EXISTS notifications(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    type TEXT,
    data TEXT,
    status INTEGER DEFAULT 0
)
""")

db.commit()
