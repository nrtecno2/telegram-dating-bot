import database


# ==========================
# ADD NOTIFICATION
# ==========================

def add_notification(

    user_id,

    notification_type,

    data

):

    database.cursor.execute(

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

    database.db.commit()



# ==========================
# GET ALL NOTIFICATIONS
# ==========================

def get_notifications(

    user_id

):

    database.cursor.execute(

        """

        SELECT *

        FROM notifications

        WHERE

        user_id=?

        ORDER BY id DESC

        """,

        (

            user_id,

        )

    )

    return database.cursor.fetchall()



# ==========================
# GET UNREAD
# ==========================

def get_unread_notifications(

    user_id

):

    database.cursor.execute(

        """

        SELECT *

        FROM notifications

        WHERE

        user_id=?

        AND

        status=0

        ORDER BY id DESC

        """,

        (

            user_id,

        )

    )

    return database.cursor.fetchall()



# ==========================
# MARK AS READ
# ==========================

def mark_as_read(

    notification_id

):

    database.cursor.execute(

        """

        UPDATE notifications

        SET status=1

        WHERE id=?

        """,

        (

            notification_id,

        )

    )

    database.db.commit()



# ==========================
# MARK ALL AS READ
# ==========================

def mark_all_as_read(

    user_id

):

    database.cursor.execute(

        """

        UPDATE notifications

        SET status=1

        WHERE user_id=?

        """,

        (

            user_id,

        )

    )

    database.db.commit()



# ==========================
# DELETE NOTIFICATION
# ==========================

def delete_notification(

    notification_id

):

    database.cursor.execute(

        """

        DELETE FROM notifications

        WHERE id=?

        """,

        (

            notification_id,

        )

    )

    database.db.commit()



# ==========================
# CLEAR USER NOTIFICATIONS
# ==========================

def clear_notifications(

    user_id

):

    database.cursor.execute(

        """

        DELETE FROM notifications

        WHERE user_id=?

        """,

        (

            user_id,

        )

    )

    database.db.commit()



# ==========================
# TOTAL UNREAD
# ==========================

def unread_count(

    user_id

):

    database.cursor.execute(

        """

        SELECT COUNT(*)

        FROM notifications

        WHERE

        user_id=?

        AND

        status=0

        """,

        (

            user_id,

        )

    )

    result = (
        database.cursor.fetchone()
    )

    return result[0]
