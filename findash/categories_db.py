from dataclasses import dataclass
from typing import List, Optional, Tuple
import json

import pandas as pd

from db import Record
from utils import SETTINGS

"""
The purpose of this module is to define the database that deals with categories.
It is a parquet file.
It manages -
1. the division of categories into groups
2. the attributes of each category such as budget (might have more in the future)
"""


@dataclass
class CatDBSchema:
    CAT_NAME: str = 'cat_name'
    CAT_GROUP: str = 'cat_group'
    IS_CONSTANT: str = 'is_constant'
    BUDGET: str = 'budget'

    # @classmethod
    # def __iter__(cls):
    #     return iter([getattr(cls, f.name) for f in fields(cls)])


class CatRecord(Record):
    def __init__(self,
                 cat_name: str,
                 cat_group: Optional[str] = None,
                 is_constant: Optional[str] = None,
                 budget: Optional[str] = None):
        self.cat_name = cat_name
        self.cat_group = cat_group
        self.is_constant = is_constant
        self.budget = budget

    @property
    def schema_cols(self):
        return [self.cat_name, self.cat_group, self.is_constant, self.budget]


class CategoriesDB:
    def __init__(self):
        self._db = pd.DataFrame()
        self._payee2cat = None
        self._cat2payee = None

    def _load_dbs(self):
        self._db = pd.read_parquet(SETTINGS['db']['cat_db_path'])

        if SETTINGS['db']['payee2cat_db_path'].exists():
            with open(SETTINGS['db']['payee2cat_db_path'], 'r') as f:
                self._payee2cat = json.load(f)
        else:
            self._payee2cat = {}

        if SETTINGS['db']['cat2payee_db_path'].exists():
            with open(SETTINGS['db']['cat2payee_db_path'], 'r') as f:
                self._cat2payee = json.load(f)
        else:
            self._cat2payee = {}

    def _save_payee2cat(self):
        with open(SETTINGS['db']['payee2cat_db_path'], 'w') as f:
            json.dump(self._payee2cat, f)

    def _save_cat2payee(self):
        with open(SETTINGS['db']['cat2payee_db_path'], 'w') as f:
            json.dump(self._cat2payee, f)

    def add_category_by_name(self, category_name: str) -> None:
        if category_name not in self.get_categories():
            self._db = self._db.append(
                {CatDBSchema.CAT_NAME: category_name},
                ignore_index=True)
            self._save_cat_db(SETTINGS['cat_db_path'])
        else:
            raise ValueError(f'category {category_name} already exists')

    def add_category_by_record(self, cat_record: CatRecord) -> None:
        self._db = self._db.append(cat_record.to_dict(), ignore_index=True)
        self._save_cat_db(SETTINGS['cat_db_path'])

    def delete_category(self, category_name: str) -> None:
        self._db = self._db[
            self._db[CatDBSchema.CAT_NAME] != category_name]
        self._save_cat_db(SETTINGS['cat_db_path'])

    def get_category_budget(self, category_name: str) -> float:
        return self._db[self._db[CatDBSchema.CAT_NAME] == category_name][
            CatDBSchema.BUDGET].iloc[0]

    def update_category_budget(self, category_name: str,
                               budget: float) -> None:
        self._db[self._db[CatDBSchema.CAT_NAME] == category_name][
            CatDBSchema.BUDGET] = budget
        self._save_cat_db(SETTINGS['cat_db_path'])

    def delete_category_budget(self, category_name: str) -> None:
        self._db[self._db[CatDBSchema.CAT_NAME] == category_name][
            CatDBSchema.BUDGET] = None

    def _save_cat_db(self, db_path):
        self._db.to_parquet(db_path)

    def load_db(self, db_path: str) -> None:
        self._db = pd.read_parquet(db_path)

    def get_categories(self) -> List[str]:
        return self._db[CatDBSchema.CAT_NAME].to_list()

    def get_cat_and_group_by_payee(self, payee: str) -> \
            Optional[Tuple[str, str]]:
        cat = self._payee2cat.get(payee)
        if cat is not None:
            cat_group = self.get_category_group(cat)
            return cat, cat_group
        else:
            return None

    def get_category_group(self, cat: str) -> Optional[str]:
        cat_row = self._db[self._db[CatDBSchema.CAT_NAME == cat]]
        if len(cat_row) > 0:
            return cat_row[CatDBSchema.CAT_GROUP]
        return None

    def get_group_names(self):
        return self._db[CatDBSchema.CAT_GROUP].unique().to_list()

    def get_groups(self) -> pd.core.groupby.generic.DataFrameGroupBy:
        return self._db.groupby(CatDBSchema.CAT_GROUP)

    def get_categories_in_group(self, group: str) -> List[str]:
        return self._db[self._db[CatDBSchema.CAT_GROUP] == group][
            CatDBSchema.CAT_NAME].to_list()

    def get_total_budget(self):
        return self._db[CatDBSchema.BUDGET].sum()
