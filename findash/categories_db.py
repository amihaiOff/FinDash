from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple, Union
import json

import pandas as pd

from settings import SETTINGS


@dataclass
class CatDBSchema:
    CAT_NAME: str = 'cat_name'
    CAT_GROUP: str = 'cat_group'
    IS_CONSTANT: str = 'is_constant'
    BUDGET: str = 'budget'
    NEW_CATEGORY_NAME = 'New Category'


class CategoriesDB:
    def __init__(self):
        self._db = pd.DataFrame()
        self._payee2cat = {}
        self._cat2payee = {}
        self._new_cat_counter = 0

        self._load_dbs()
        self._update_new_category_counter()

    def _load_dbs(self):
        """
        load the categoeies db and the payee2cat and cat2payee dbs
        :return:
        """
        self._db = pd.read_parquet(SETTINGS.cat_db_path)

        if Path(SETTINGS.payee2cat_db_path).exists():
            with open(SETTINGS.payee2cat_db_path, 'r') as f:
                self._payee2cat = json.load(f)
        else:
            self._payee2cat = {}

        if Path(SETTINGS.cat2payee_db_path).exists():
            with open(SETTINGS.cat2payee_db_path, 'r') as f:
                self._cat2payee = json.load(f)
        else:
            self._cat2payee = {}

    def _save_payee2cat(self):
        with open(SETTINGS.payee2cat_db_path, 'w') as f:
            json.dump(self._payee2cat, f, indent=4, ensure_ascii=False)

    def _save_cat2payee(self):
        with open(SETTINGS.cat2payee_db_path, 'w') as f:
            json.dump(self._cat2payee, f, indent=4, ensure_ascii=False)

    def _save_cat_db(self, db_path):
        self._db.to_parquet(db_path)

    def _create_new_category_row(self, cat_group: str):
        self._new_cat_counter += 1
        return {
            CatDBSchema.CAT_GROUP: cat_group,
            CatDBSchema.CAT_NAME: self.get_new_category_name(),
            CatDBSchema.IS_CONSTANT: False,
            CatDBSchema.BUDGET: 0
        }

    def add_category(self,
                     category_group: str) -> None:
        self._db = self._db.append(
            self._create_new_category_row(category_group),
            ignore_index=True)
        self._save_cat_db(SETTINGS.cat_db_path)

    def update_category_name(self, old_name: str, new_name: str) -> None:
        if new_name in self.get_categories():
            # todo make into error for user
            raise ValueError(f'Category {new_name} already exists')

        self._db.loc[self._db[CatDBSchema.CAT_NAME] == old_name,
                     CatDBSchema.CAT_NAME] = new_name
        self._save_cat_db(SETTINGS.cat_db_path)

    def _update_new_category_counter(self):
        new_cat_only = self._db[self._db[CatDBSchema.CAT_NAME].str.startswith(
                CatDBSchema.NEW_CATEGORY_NAME)][CatDBSchema.CAT_NAME]

        if len(new_cat_only) == 0:
            self._new_cat_counter = 0
        else:
            self._new_cat_counter = new_cat_only.str.split(
                CatDBSchema.NEW_CATEGORY_NAME).str[1].astype(int).max()

    def delete_category(self, category_name: str) -> None:
        self._db = self._db[
            self._db[CatDBSchema.CAT_NAME] != category_name]

        self._save_cat_db(SETTINGS.cat_db_path)

        if category_name.startswith(CatDBSchema.NEW_CATEGORY_NAME):
            self._update_new_category_counter()

    def update_category_budget(self, category_name: str,
                               budget: float) -> None:
        row_ind = self._db[CatDBSchema.CAT_NAME] == category_name
        self._db.loc[row_ind, CatDBSchema.BUDGET] = budget
        self._save_cat_db(SETTINGS.cat_db_path)

    def update_payee_to_cat_mapping(self, payee: str, cat: str):
        original_cat = self._payee2cat.get(payee)
        if original_cat is not None and original_cat != cat:
            self._cat2payee[original_cat].remove(payee)

        if cat not in self._cat2payee:
            self._cat2payee[cat] = []
        if payee not in self._cat2payee[cat]:
            self._cat2payee[cat].append(payee)
            self._save_cat2payee()

        self._payee2cat[payee] = cat
        self._save_payee2cat()

    def get_cat_and_group_by_payee(self, payee: str) -> \
            Union[Tuple[str, str], Tuple[None, None]]:
        cat = self._payee2cat.get(payee)
        if cat is not None:
            cat_group = self.get_group_of_category(cat)
            return cat, cat_group
        else:
            return None, None

    def get_new_category_name(self) -> str:
        return f'{CatDBSchema.NEW_CATEGORY_NAME} {self._new_cat_counter}'

    def get_group_of_category(self, cat: str) -> Optional[str]:
        cat_row = self._db[self._db[CatDBSchema.CAT_NAME] == cat]
        return cat_row[CatDBSchema.CAT_GROUP].iloc[0] if len(cat_row) > 0 else None

    def get_group_names(self) -> List[str]:
        return self._db[CatDBSchema.CAT_GROUP].unique().tolist()

    def get_groups_as_groupby(self) -> pd.core.groupby.generic.DataFrameGroupBy:
        return self._db.groupby(CatDBSchema.CAT_GROUP)

    def get_categories_in_group(self, group: str) -> List[str]:
        return self._db[self._db[CatDBSchema.CAT_GROUP] == group][
            CatDBSchema.CAT_NAME].to_list()

    def get_total_budget(self):
        return self._db[CatDBSchema.BUDGET].sum()

    def get_payee_category(self, payee: str) -> Optional[str]:
        return self._payee2cat.get(payee)

    def get_category_budget(self, category_name: str) -> float:
        return self._db[self._db[CatDBSchema.CAT_NAME] == category_name][
            CatDBSchema.BUDGET].iloc[0]

    def get_categories(self) -> List[str]:
        return self._db[CatDBSchema.CAT_NAME].to_list()

    def get_group(self, group_name: str) -> pd.DataFrame:
        return self._db[self._db[CatDBSchema.CAT_GROUP] == group_name]

    def get_group_budget(self, group_name: str) -> pd.DataFrame:
        group_ind = self._db[CatDBSchema.CAT_GROUP] == group_name
        return self._db.loc[group_ind, CatDBSchema.BUDGET].sum()


def _get_group_and_cat_for_dropdown(cat_db):
    options = []
    for name, group in cat_db.get_groups_as_groupby():
        options.extend(
            [{'label': f'{name}: {cat}', 'value': f'{cat}'} for cat in
             group[CatDBSchema.CAT_NAME]])
    return options
