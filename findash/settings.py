from typing import Dict, Any

import yaml


class SK:
    PATH_FROM_ROOT = 'path_from_root'
    PATH_TO_DATA = 'path_to_data'
    TRANS_DB_PATH = 'trans_db_path'
    CAT_DB_PATH = 'cat_db_path'
    PAYEE2CAT_DB_PATH = 'payee2cat_db_path'
    CAT2PAYEE_DB_PATH = 'cat2payee_db_path'
    AUTO_CAT_DB_PATH = 'auto_cat_db_path'
    ACCOUNTS = 'accounts'


class Settings:
    def __init__(self, env='local'):
        self._settings = self.load_settings()
        # todo make this work with remote deployment
        self._path_to_data = self._settings[env][SK.PATH_TO_DATA]

    def load_settings(self) -> Dict[str, Any]:
        return yaml.safe_load(open('../settings.yaml'))

    def _add_path_prefix(self, db_asset_path: str):
        return f'{self._path_to_data}/{db_asset_path}'

    @property
    def trans_db_path(self) -> str:
        return self._add_path_prefix(self._settings[SK.PATH_FROM_ROOT][SK.TRANS_DB_PATH])

    @property
    def cat_db_path(self):
        return self._add_path_prefix(self._settings[SK.PATH_FROM_ROOT][SK.CAT_DB_PATH])

    @property
    def payee2cat_db_path(self) -> str:
        return self._add_path_prefix(self._settings[SK.PATH_FROM_ROOT][SK.PAYEE2CAT_DB_PATH])

    @property
    def cat2payee_db_path(self):
        return self._add_path_prefix(self._settings[SK.PATH_FROM_ROOT][SK.CAT2PAYEE_DB_PATH])

    @property
    def auto_cat_db_path(self):
        return self._add_path_prefix(self._settings[SK.PATH_FROM_ROOT][SK.AUTO_CAT_DB_PATH])

    @property
    def accounts_path(self):
        return self._add_path_prefix(self._settings[SK.PATH_FROM_ROOT][SK.ACCOUNTS])


SETTINGS = Settings()
