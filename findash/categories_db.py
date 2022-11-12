from dataclasses import dataclass
from typing import List, Optional

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

    def add_category_by_name(self, category_name: str) -> None:
        if category_name not in self.get_categories():
            self._db = self._db.append(
                {CatDBSchema.CAT_NAME: category_name},
                ignore_index=True)
            self._save_db(SETTINGS['cat_db_path'])
        else:
            raise ValueError(f'category {category_name} already exists')

    def add_category_by_record(self, cat_record: CatRecord) -> None:
        self._db = self._db.append(cat_record.to_dict(), ignore_index=True)
        self._save_db(SETTINGS['cat_db_path'])

    def delete_category(self, category_name: str) -> None:
        self._db = self._db[
            self._db[CatDBSchema.CAT_NAME] != category_name]
        self._save_db(SETTINGS['cat_db_path'])

    def get_category_budget(self, category_name: str) -> float:
        return \
        self._db[self._db[CatDBSchema.CAT_NAME] == category_name][
            CatDBSchema.BUDGET].iloc[0]

    def update_category_budget(self, category_name: str,
                               budget: float) -> None:
        self._db[self._db[CatDBSchema.CAT_NAME] == category_name][
            CatDBSchema.BUDGET] = budget
        self._save_db(SETTINGS['cat_db_path'])

    def delete_category_budget(self, category_name: str) -> None:
        self._db[self._db[CatDBSchema.CAT_NAME] == category_name][
            CatDBSchema.BUDGET] = None

    def _save_db(self, db_path):
        self._db.to_parquet(db_path)

    def load_db(self, db_path: str) -> None:
        self._db = pd.read_parquet(db_path)

    def get_categories(self) -> List[str]:
        return self._db[CatDBSchema.CAT_NAME].to_list()

    def get_group_names(self):
        return self._db[CatDBSchema.CAT_GROUP].unique().to_list()

    def get_groups(self) -> pd.core.groupby.generic.DataFrameGroupBy:
        return self._db.groupby(CatDBSchema.CAT_GROUP)

    def get_categories_by_section(self, section: str) -> List[str]:
        return self._db[self._db[CatDBSchema.CAT_GROUP] == section][
            CatDBSchema.CAT_NAME].to_list()
