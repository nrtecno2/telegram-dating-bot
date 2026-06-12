import sqlite3
from typing import Optional, List, Dict, Any


class Database:
    def __init__(self, db_name: str = "bot.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.init_tables()

    # =========================
    # TABLES
    # =========================
    def init_tables(self):
        # USERS TABLE
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            name TEXT,
            age INTEGER,
            gender TEXT,
            bio TEXT,
            location TEXT,
            photos TEXT,
            state TEXT DEFAULT 'IDLE',
            is_blocked INTEGER DEFAULT 0
        )
        """)

        # LIKES TABLE
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS likes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_user INTEGER,
            to_user INTEGER
        )
        """)

        # MATCHES TABLE
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user1 INTEGER,
            user2 INTEGER
        )
        """)

        # MESSAGES TABLE
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER,
            receiver_id INTEGER,
            message TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # NOTIFICATIONS TABLE
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            text TEXT,
            is_read INTEGER DEFAULT 0
        )
        """)

        self.conn.commit()

    # =========================
    # USER FUNCTIONS
    # =========================
    def add_user(self, user_id: int, username: str):
        self.cursor.execute("""
        INSERT OR IGNORE INTO users (user_id, username)
        VALUES (?, ?)
        """, (user_id, username))
        self.conn.commit()

    def update_user_field(self, user_id: int, field: str, value: Any):
        query = f"UPDATE users SET {field} = ? WHERE user_id = ?"
        self.cursor.execute(query, (value, user_id))
        self.conn.commit()

    def get_user(self, user_id: int) -> Optional[Dict]:
        self.cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = self.cursor.fetchone()
        if row:
            return self._user_row_to_dict(row)
        return None

    def get_all_users(self) -> List[Dict]:
        self.cursor.execute("SELECT * FROM users")
        rows = self.cursor.fetchall()
        return [self._user_row_to_dict(r) for r in rows]

    def _user_row_to_dict(self, row):
        return {
            "user_id": row[0],
            "username": row[1],
            "name": row[2],
            "age": row[3],
            "gender": row[4],
            "bio": row[5],
            "location": row[6],
            "photos": row[7],
            "state": row[8],
            "is_blocked": row[9],
        }

    # =========================
    # LIKES SYSTEM
    # =========================
    def add_like(self, from_user: int, to_user: int):
        self.cursor.execute("""
        INSERT INTO likes (from_user, to_user)
        VALUES (?, ?)
        """, (from_user, to_user))
        self.conn.commit()

    def check_like(self, from_user: int, to_user: int) -> bool:
        self.cursor.execute("""
        SELECT 1 FROM likes
        WHERE from_user = ? AND to_user = ?
        """, (from_user, to_user))
        return self.cursor.fetchone() is not None

    # =========================
    # MATCH SYSTEM
    # =========================
    def create_match(self, user1: int, user2: int):
        self.cursor.execute("""
        INSERT INTO matches (user1, user2)
        VALUES (?, ?)
        """, (user1, user2))
        self.conn.commit()

    def get_matches(self, user_id: int) -> List[int]:
        self.cursor.execute("""
        SELECT user1, user2 FROM matches
        WHERE user1 = ? OR user2 = ?
        """, (user_id, user_id))

        rows = self.cursor.fetchall()
        matches = []

        for u1, u2 in rows:
            matches.append(u2 if u1 == user_id else u1)

        return matches

    # =========================
    # MESSAGES
    # =========================
    def save_message(self, sender_id: int, receiver_id: int, message: str):
        self.cursor.execute("""
        INSERT INTO messages (sender_id, receiver_id, message)
        VALUES (?, ?, ?)
        """, (sender_id, receiver_id, message))
        self.conn.commit()

    def get_chat(self, user1: int, user2: int) -> List[Dict]:
        self.cursor.execute("""
        SELECT sender_id, receiver_id, message, timestamp
        FROM messages
        WHERE (sender_id = ? AND receiver_id = ?)
        OR (sender_id = ? AND receiver_id = ?)
        ORDER BY timestamp ASC
        """, (user1, user2, user2, user1))

        rows = self.cursor.fetchall()

        return [
            {
                "sender_id": r[0],
                "receiver_id": r[1],
                "message": r[2],
                "timestamp": r[3],
            }
            for r in rows
        ]

    # =========================
    # NOTIFICATIONS
    # =========================
    def add_notification(self, user_id: int, text: str):
        self.cursor.execute("""
        INSERT INTO notifications (user_id, text)
        VALUES (?, ?)
        """, (user_id, text))
        self.conn.commit()

    def get_notifications(self, user_id: int):
        self.cursor.execute("""
        SELECT id, text, is_read FROM notifications
        WHERE user_id = ?
        """, (user_id,))
        return self.cursor.fetchall()

    def mark_notification_read(self, notif_id: int):
        self.cursor.execute("""
        UPDATE notifications SET is_read = 1 WHERE id = ?
        """, (notif_id,))
        self.conn.commit()

    # =========================
    # CLOSE
    # =========================
    def close(self):
        self.conn.close()
