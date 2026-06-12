import math


# ==========================
# SAVE LOCATION
# ==========================

def make_location(

    latitude,

    longitude

):

    return str(
        latitude
    ) + "," + str(
        longitude
    )


# ==========================
# SPLIT LOCATION
# ==========================

def split_location(

    location

):

    try:

        lat, lon = location.split(",")

        return (

            float(lat),

            float(lon)

        )

    except:

        return (

            None,

            None

        )


# ==========================
# DISTANCE
# ==========================

def calculate_distance(

    lat1,

    lon1,

    lat2,

    lon2

):

    radius = 6371

    dlat = math.radians(
        lat2 - lat1
    )

    dlon = math.radians(
        lon2 - lon1
    )

    a = (

        math.sin(
            dlat / 2
        ) ** 2

        +

        math.cos(
            math.radians(lat1)
        )

        *

        math.cos(
            math.radians(lat2)
        )

        *

        math.sin(
            dlon / 2
        ) ** 2

    )

    c = 2 * math.atan2(

        math.sqrt(a),

        math.sqrt(1 - a)

    )

    return radius * c


# ==========================
# USER DISTANCE
# ==========================

def user_distance(

    location1,

    location2

):

    lat1, lon1 = split_location(
        location1
    )

    lat2, lon2 = split_location(
        location2
    )

    if (

        lat1 is None

        or

        lat2 is None

    ):

        return None

    return calculate_distance(

        lat1,

        lon1,

        lat2,

        lon2

    )


# ==========================
# NEARBY CHECK
# ==========================

def is_nearby(

    location1,

    location2,

    max_distance=100

):

    distance = user_distance(

        location1,

        location2

    )

    if distance is None:

        return False

    return distance <= max_distance


# ==========================
# SORT USERS
# ==========================

def sort_by_distance(

    my_location,

    users

):

    result = []

    for user in users:

        location = user[4]

        distance = user_distance(

            my_location,

            location

        )

        if distance is None:

            continue

        result.append(

            (

                distance,

                user

            )

        )

    result.sort(

        key=lambda x: x[0]

    )

    output = []

    for item in result:

        output.append(

            item[1]

        )

    return output
