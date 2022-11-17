import uuid
import yaml
from typing import Any, Dict, Tuple


def create_uuid():
    return uuid.uuid4().hex


def get_settings() -> Dict[str, Any]:
    return yaml.safe_load(open('settings.yaml'))


def conditional_coloring(value: float,
                         threshold_colors: Dict[str,
                                                Tuple[float, float]]) -> str:
    """
    return the text color based on the value and the threshold_colors
    :param value:
    :param threshold_colors: dict with colors as keys and tuples of (min, max)
                             as values
    :return:
    """
    for color, (lower, upper) in threshold_colors.items():
        if lower <= value < upper:
            return color
    raise ValueError(f'Value {value} not in any range')


SETTINGS = get_settings()
SHEKEL_SYM = '₪'
