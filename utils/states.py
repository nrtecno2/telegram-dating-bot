# ==========================
# PROFILE STATES
# ==========================

START = "START"

NAME = "NAME"

GENDER = "GENDER"

AGE = "AGE"

LOCATION = "LOCATION"

ABOUT = "ABOUT"

MEDIA = "MEDIA"

PREFERENCE = "PREFERENCE"

COMPLETE = "COMPLETE"


# ==========================
# MEMORY
# ==========================

user_states = {}


# ==========================
# FUNCTIONS
# ==========================

def set_state(

    user_id,

    state

):

    user_states[user_id] = state



def get_state(

    user_id

):

    return user_states.get(

        user_id,

        START

    )



def clear_state(

    user_id

):

    if user_id in user_states:

        del user_states[user_id]
