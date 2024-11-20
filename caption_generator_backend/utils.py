import os
import uuid


def generate_random_id():
    return str(uuid.uuid4())


def remove_if_exists(filename):
    if os.path.exists(filename):
        os.remove(filename)
