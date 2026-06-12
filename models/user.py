import database


# ==========================
# CREATE USER
# ==========================

def create_user(

    user_id

):

    if get_user(
        user_id
    ):

        return

    database.cursor.execute(

        """

        INSERT INTO users(

        user_id

        )

        VALUES(?)

        """,

        (

            user_id,

        )

    )

    database.db.commit()



# ==========================
# GET USER
# ==========================

def get_user(

    user_id

):

    database.cursor.execute(

        """

        SELECT *

        FROM users

        WHERE user_id=?

        """,

        (

            user_id,

        )

    )

    return database.cursor.fetchone()



# ==========================
# UPDATE FIELD
# ==========================

def update_user(

    user_id,

    field,

    value

):

    database.cursor.execute(

        f"""

        UPDATE users

        SET {field}=?

        WHERE user_id=?

        """,

        (

            value,

            user_id

        )

    )

    database.db.commit()



# ==========================
# DELETE USER
# ==========================

def delete_user(

    user_id

):

    database.cursor.execute(

        """

        DELETE FROM users

        WHERE user_id=?

        """,

        (

            user_id,

        )

    )

    database.db.commit()



# ==========================
# PROFILE COMPLETE
# ==========================

def complete_profile(

    user_id

):

    database.cursor.execute(

        """

        UPDATE users

        SET completed=1

        WHERE user_id=?

        """,

        (

            user_id,

        )

    )

    database.db.commit()



# ==========================
# IS PROFILE COMPLETE
# ==========================

def is_completed(

    user_id

):

    database.cursor.execute(

        """

        SELECT completed

        FROM users

        WHERE user_id=?

        """,

        (

            user_id,

        )

    )

    result = (
        database.cursor.fetchone()
    )

    if result:

        return result[0]

    return 0



# ==========================
# GET ALL USERS
# ==========================

def get_all_users():

    database.cursor.execute(

        """

        SELECT *

        FROM users

        """

    )

    return database.cursor.fetchall()



# ==========================
# GET USERS BY GENDER
# ==========================

def get_users_by_gender(

    gender

):

    database.cursor.execute(

        """

        SELECT *

        FROM users

        WHERE

        gender=?

        AND

        completed=1

        """,

        (

            gender,

        )

    )

    return database.cursor.fetchall()



# ==========================
# GET MATCHING USERS
# ==========================

def get_matching_users(

    user_id

):

    user = get_user(
        user_id
    )

    if not user:

        return []

    preference = user[6]

    if preference.lower() == "both":

        database.cursor.execute(

            """

            SELECT *

            FROM users

            WHERE

            user_id!=?

            AND

            completed=1

            """,

            (

                user_id,

            )

        )

    else:

        database.cursor.execute(

            """

            SELECT *

            FROM users

            WHERE

            gender=?

            AND

            user_id!=?

            AND

            completed=1

            """,

            (

                preference.capitalize(),

                user_id

            )

        )

    return database.cursor.fetchall()



# ==========================
# GET USER NAME
# ==========================

def get_name(

    user_id

):

    user = get_user(
        user_id
    )

    if user:

        return user[1]

    return None



# ==========================
# GET USER PREFERENCE
# ==========================

def get_preference(

    user_id

):

    user = get_user(
        user_id
    )

    if user:

        return user[6]

    return None
