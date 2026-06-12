import database


# ==========================
# ADD LIKE
# ==========================

def add_like(

    from_user,

    to_user

):

    if already_liked(

        from_user,

        to_user

    ):

        return False

    database.cursor.execute(

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

    database.db.commit()

    return True


# ==========================
# CHECK LIKE
# ==========================

def already_liked(

    from_user,

    to_user

):

    database.cursor.execute(

        """

        SELECT *

        FROM likes

        WHERE

        from_user=?

        AND

        to_user=?

        """,

        (

            from_user,

            to_user

        )

    )

    return database.cursor.fetchone()


# ==========================
# GET USER LIKES
# ==========================

def get_user_likes(

    user_id

):

    database.cursor.execute(

        """

        SELECT *

        FROM likes

        WHERE

        to_user=?

        ORDER BY id DESC

        """,

        (

            user_id,

        )

    )

    return database.cursor.fetchall()


# ==========================
# TOTAL LIKES
# ==========================

def total_likes(

    user_id

):

    database.cursor.execute(

        """

        SELECT COUNT(*)

        FROM likes

        WHERE

        to_user=?

        """,

        (

            user_id,

        )

    )

    result = (
        database.cursor.fetchone()
    )

    return result[0]


# ==========================
# REMOVE LIKE
# ==========================

def remove_like(

    from_user,

    to_user

):

    database.cursor.execute(

        """

        DELETE FROM likes

        WHERE

        from_user=?

        AND

        to_user=?

        """,

        (

            from_user,

            to_user

        )

    )

    database.db.commit()


# ==========================
# CLEAR USER LIKES
# ==========================

def clear_user_likes(

    user_id

):

    database.cursor.execute(

        """

        DELETE FROM likes

        WHERE

        to_user=?

        """,

        (

            user_id,

        )

    )

    database.db.commit()
