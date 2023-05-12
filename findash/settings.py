from typing import Dict, Any

import yaml

from utils import SK


class Settings:
    def __init__(self):
        self._settings = self.load_settings()
        self._vault_name = self._settings[SK.USER][SK.VAULT_NAME]

    def load_settings(self) -> Dict[str, Any]:
        return yaml.safe_load(open('settings.yaml'))

    def _add_path_prefix(self, db_asset_path: str):
        path_to_vault = self._settings[SK.DB][SK.PATH_TO_VAULTS]
        path_prefix = f'{path_to_vault}/{self._vault_name}'
        return f'{path_prefix}/{db_asset_path}'

    @property
    def vault_name(self) -> str:
        return self._vault_name

    @property
    def trans_db_path(self) -> str:
        return self._add_path_prefix(self._settings[SK.DB][SK.TRANS_DB_PATH])

    @property
    def cat_db_path(self):
        return self._add_path_prefix(self._settings[SK.DB][SK.CAT_DB_PATH])

    @property
    def payee2cat_db_path(self) -> str:
        return self._add_path_prefix(self._settings[SK.DB][SK.PAYEE2CAT_DB_PATH])

    @property
    def cat2payee_db_path(self):
        return self._add_path_prefix(self._settings[SK.DB][SK.CAT2PAYEE_DB_PATH])

    @property
    def auto_cat_db_path(self):
        return self._add_path_prefix(self._settings[SK.DB][SK.AUTO_CAT_DB_PATH])

    @property
    def accounts_path(self):
        return self._add_path_prefix(self._settings[SK.DB][SK.ACCOUNTS])


SETTINGS = Settings()
