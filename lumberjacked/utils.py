import random

def generate_id():
    """
    Generate a psuedo-random 48 bit ID number for all DB records.
    Reserve 16 bits for potential future use.
    """
    return random.SystemRandom().getrandbits(48)
