import sqlite3

db = sqlite3.connect(
    "users.db",
    check_same_thread=False
)

cursor = db.cursor()


# ==========================
# USERS TABLE
# ==========================

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



# ==========================
# MEDIA TABLE
# ==========================

cursor.execute("""

CREATE TABLE IF NOT EXISTS media(

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    user_id INTEGER,

    file_id TEXT,

    media_type TEXT

)

""")



# ==========================
# LIKES TABLE
# ==========================

cursor.execute("""

CREATE TABLE IF NOT EXISTS likes(

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    from_user INTEGER,

    to_user INTEGER

)

""")



# ==========================
# NOTIFICATIONS TABLE
# ==========================

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


# ==========================
# USER FUNCTIONS
# ==========================

def user_exists(user_id):

    cursor.execute(

        "SELECT user_id FROM users WHERE user_id=?",

        (user_id,)

    )

    return cursor.fetchone()



def add_user(user_id):

    if not user_exists(user_id):

        cursor.execute(

            "INSERT INTO users(user_id) VALUES(?)",

            (user_id,)

        )

        db.commit()



def get_user(user_id):

    cursor.execute(

        "SELECT * FROM users WHERE user_id=?",

        (user_id,)

    )

    return cursor.fetchone()



def update_field(

    user_id,

    field,

    value

):

    cursor.execute(

        f"UPDATE users SET {field}=? WHERE user_id=?",

        (

            value,

            user_id

        )

    )

    db.commit()



# ==========================
# MEDIA FUNCTIONS
# ==========================

def add_media(

    user_id,

    file_id,

    media_type

):

    cursor.execute(

        """

        INSERT INTO media(

        user_id,

        file_id,

        media_type

        )

        VALUES(

        ?,

        ?,

        ?

        )

        """,

        (

            user_id,

            file_id,

            media_type

        )

    )

    db.commit()



def get_media(user_id):

    cursor.execute(

        "SELECT * FROM media WHERE user_id=?",

        (user_id,)

    )

    return cursor.fetchall()



# ==========================
# LIKE FUNCTIONS
# ==========================

def add_like(

    from_user,

    to_user

):

    cursor.execute(

        """

        INSERT INTO likes(

        from_user,

        to_user

        )

        VALUES(

        ?,

        ?

        )

        """,

        (

            from_user,

            to_user

        )

    )

    db.commit()



# ==========================
# NOTIFICATION FUNCTIONS
# ==========================

def add_notification(

    user_id,

    notification_type,

    data

):

    cursor.execute(

        """

        INSERT INTO notifications(

        user_id,

        type,

        data

        )

        VALUES(

        ?,

        ?,

        ?

        )

        """,

        (

            user_id,

            notification_type,

            data

        )

    )

    db.commit()



def get_notifications(

    user_id

):

    cursor.execute(

        """

        SELECT * FROM notifications

        WHERE user_id=?

        ORDER BY id DESC

        """,

        (

            user_id,

        )

    )

    return cursor.fetchall()
