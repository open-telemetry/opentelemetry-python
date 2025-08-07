import random


def random_trace_id() -> int:
    return random.getrandbits(128)
