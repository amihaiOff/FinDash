import uuid
import yaml
from typing import Any, Dict


def create_uuid():
    return uuid.uuid4().hex


def get_settings() -> Dict[str, Any]:
    return yaml.safe_load(open('settings.yaml'))


SETTINGS = get_settings()
SHEKEL_SYM = '₪'
