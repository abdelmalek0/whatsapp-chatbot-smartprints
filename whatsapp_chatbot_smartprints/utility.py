import base64
import os
import re
import uuid

import yaml

def check_text_language(text):
    # Pattern for Arabic letters
    arabic_pattern = re.compile(r'[\u0600-\u06FF]')
    
    has_arabic = bool(arabic_pattern.search(text))
    
    if has_arabic:
        return "Arabic"
    else:
        return "English"

def generate_short_id():
    # Generate a random UUID
    uuid_bytes = uuid.uuid4().bytes
    # Encode it to base64 and remove unnecessary characters
    short_id = base64.urlsafe_b64encode(uuid_bytes).rstrip(b'=').decode('utf-8')
    return short_id


def load_template(template_name):
    template_path = os.path.join('templates', f'{template_name}.yaml')
    with open(template_path, 'r') as file:
        return yaml.safe_load(file)['prompt']

def normalize_distance_reversed(distance: float | int, max_distance=700) -> float:
    """
    Normalize a distance value to the range [0, 1] where 0 distance corresponds to 1 
    and max_distance (e.g., 700) corresponds to 0.

    :param distance: The input distance (expected to be between 0 and max_distance).
    :param max_distance: The maximum distance value for normalization.
    :return: The normalized distance in the range [0, 1].
    """
    # Clip the distance to ensure it doesn't exceed max_distance
    clipped_distance = min(distance, max_distance)

    # Reverse normalize the distance to the range [0, 1]
    normalized = 1 - (clipped_distance / max_distance)
    return normalized
