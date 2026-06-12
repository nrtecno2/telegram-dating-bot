import database


# ==========================
# ADD MEDIA
# ==========================

def add_media(

    user_id,

    file_id,

    media_type

):

    database.cursor.execute(

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

    database.db.commit()



# ==========================
# GET ALL MEDIA
# ==========================

def get_media(

    user_id

):

    database.cursor.execute(

        """

        SELECT *

        FROM media

        WHERE

        user_id=?

        ORDER BY id ASC

        """,

        (

            user_id,

        )

    )

    return database.cursor.fetchall()



# ==========================
# GET FIRST MEDIA
# ==========================

def get_first_media(

    user_id

):

    database.cursor.execute(

        """

        SELECT *

        FROM media

        WHERE

        user_id=?

        ORDER BY id ASC

        LIMIT 1

        """,

        (

            user_id,

        )

    )

    return database.cursor.fetchone()



# ==========================
# MEDIA COUNT
# ==========================

def media_count(

    user_id

):

    database.cursor.execute(

        """

        SELECT COUNT(*)

        FROM media

        WHERE

        user_id=?

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
# DELETE USER MEDIA
# ==========================

def delete_media(

    user_id

):

    database.cursor.execute(

        """

        DELETE FROM media

        WHERE

        user_id=?

        """,

        (

            user_id,

        )

    )

    database.db.commit()



# ==========================
# CHECK LIMIT
# ==========================

def can_upload(

    user_id

):

    total = media_count(
        user_id
    )

    if total >= 3:

        return False

    return True



# ==========================
# GET PHOTO MEDIA
# ==========================

def get_photos(

    user_id

):

    database.cursor.execute(

        """

        SELECT *

        FROM media

        WHERE

        user_id=?

        AND

        media_type='photo'

        """,

        (

            user_id,

        )

    )

    return database.cursor.fetchall()



# ==========================
# GET VIDEO MEDIA
# ==========================

def get_videos(

    user_id

):

    database.cursor.execute(

        """

        SELECT *

        FROM media

        WHERE

        user_id=?

        AND

        media_type='video'

        """,

        (

            user_id,

        )

    )

    return database.cursor.fetchall()
