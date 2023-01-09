from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional, Union

import pandas as pd

from categories_db import CategoriesDB
from utils import SETTINGS, create_uuid, format_date_col_for_display, \
    set_cat_col_categories, check_null, get_current_year_and_month

"""
The purpose of this module is to provide a database for transactions.
The database in a collection of parquet files, one per month, organized by year.
This is the recorded history of the transactions.
"""


@dataclass
class TransDBSchema:
    ID: str = 'id'
    DATE: str = 'date'
    PAYEE: str = 'payee'
    CAT: str = 'cat'
    CAT_GROUP: str = 'cat_group'
    MEMO: str = 'memo'
    ACCOUNT: str = 'account'
    INFLOW: float = 'inflow'  # if forex trans will show the conversion to ils here
    OUTFLOW: float = 'outflow'  # if forex trans will show the conversion to ils here
    RECONCILED: bool = 'reconciled'
    AMOUNT: float = 'amount'  # can be in forex
    SPLIT: str = 'split'

    @classmethod
    def col_display_name_mapping(cls):
        return {
            cls.DATE: 'Date',
            cls.PAYEE: 'Payee',
            cls.CAT: 'Category',
            cls.CAT_GROUP: 'Group',
            cls.MEMO: 'Memo',
            cls.ACCOUNT: 'Account',
            cls.AMOUNT: 'Amount',
            cls.INFLOW: 'Inflow',
            cls.OUTFLOW: 'Outflow',
        }
    @classmethod
    def get_mandatory_col_sets(cls) -> Tuple[List[Union[str, float]]]:
        """
        mandatory cols every raw transactions file must have
        """
        option1 = [cls.DATE, cls.PAYEE, cls.AMOUNT]
        option2 = [cls.DATE, cls.PAYEE, cls.INFLOW, cls.OUTFLOW]
        return option1, option2

    @classmethod
    def get_col_order_for_table(cls):
        return [TransDBSchema.DATE, TransDBSchema.PAYEE, TransDBSchema.AMOUNT,
                TransDBSchema.INFLOW, TransDBSchema.OUTFLOW, TransDBSchema.CAT,
                TransDBSchema.MEMO, TransDBSchema.ACCOUNT]

    @classmethod
    def get_cols_for_trans_drawer(cls) -> List[str]:
        return [cls.DATE, cls.PAYEE, cls.MEMO, cls.INFLOW, cls.OUTFLOW]

    @classmethod
    def get_non_mandatory_cols(cls) -> Dict[str, Any]:
        """
        dictionary of non-mandatory cols (keys) to add to trans file to align with
        DB schema along with default values (values)
        """
        return {cls.CAT: '',
                cls.CAT_GROUP: '',
                cls.MEMO: '',
                cls.ACCOUNT: None,
                cls.INFLOW: 0,
                cls.OUTFLOW: 0,
                cls.RECONCILED: False,
                cls.SPLIT: None}

    @classmethod
    def get_db_col_names(cls):
        return [f.name for f in fields(cls)]

    @classmethod
    def get_db_col_vals(cls):
        return [f.default for f in fields(cls)]

    @classmethod
    def get_db_col_dict(cls):
        return dict(zip(cls.get_db_col_names(), cls.get_db_col_vals()))

    @classmethod
    def get_numeric_cols(cls):
        return [cls.INFLOW, cls.OUTFLOW, cls.AMOUNT]

    @classmethod
    def get_displayed_cols_by_type(cls):
        return {
            'date': [cls.DATE],
            'str': [cls.PAYEE, cls.MEMO],
            'numeric': [cls.AMOUNT, cls.INFLOW, cls.OUTFLOW],
            'cat': [cls.CAT, cls.ACCOUNT],
        }

    @classmethod
    def get_dropdown_cols(cls):
        return [cls.CAT, cls.ACCOUNT]

    @classmethod
    def get_categorical_cols(cls):
        return [cls.CAT, cls.ACCOUNT, cls.CAT_GROUP]

    @classmethod
    def get_cols_for_dup_checking(cls):
        """ these cols dictate which transactions are considered duplicates """
        return [cls.PAYEE, cls.AMOUNT, cls.DATE]


class TransactionsDBParquet:
    def __init__(self,
                 cat_db: CategoriesDB,
                 db: pd.DataFrame = pd.DataFrame()):
        self._db: pd.DataFrame = db
        self._cat_db = cat_db
        self.specific_month = None

    def __getitem__(self, item):
        return TransactionsDBParquet(self._cat_db, self._db.__getitem__(item))

    def __getattr__(self, item):
        return self._db.__getattr__(item)

    def __setitem__(self, name, value):
        return TransactionsDBParquet(self._cat_db,
                                     self._db.__setitem__(name, value))

    def __eq__(self, other):
        return self._db.__eq__(other)

    def __ge__(self, other):
        return self._db.__ge__(other)

    def __le__(self, other):
        return self._db.__le__(other)

    def __repr__(self):
        return self._db.__repr__()

    def connect(self, db_path: str):
        """
        load parquet files of transactions
        :param db_path: path to db root folder
        :return:
        """
        root_path = Path(db_path)

        pq_files = []
        for item in root_path.glob('*'):
            if item.is_dir():
                for file in item.iterdir():
                    pq_files.append(pd.read_parquet(file))
            else:
                if item.name.endswith('pq'):
                    pq_files.append(pd.read_parquet(item))

        if len(pq_files) == 0:
            self._db = pd.DataFrame()

        category_vals = self._get_category_vals(pq_files[0])
        final_df = pd.concat(pq_files)
        final_df = apply_dtypes(final_df, include_date=False)
        final_df = set_cat_col_categories(final_df, category_vals)
        self._db = final_df

        # todo remove
        if TransDBSchema.SPLIT not in self._db.columns:
            self._db[TransDBSchema.SPLIT] = None

        self._sort_db()

        # set monthly_trans
        self.set_specific_month(*get_current_year_and_month())

    def save_db(self, months_to_save: List[Tuple[str, str]]) -> None:
        """
        save the db to a parquet file. Saves only modified months
        :param months_to_save: list of tuples of form (year, month)
        :return:
        """
        # if len(months_to_save) == 0:
        #     self._save_no_date_db()

        trans_db_path = Path(SETTINGS['db']['trans_db_path'])
        for year, month in months_to_save:
            year_dir = trans_db_path / str(year)
            if not year_dir.exists():
                year_dir.mkdir()

            cond1 = self._db[TransDBSchema.DATE].dt.year == int(year)
            cond2 = self._db[TransDBSchema.DATE].dt.month == int(month)
            self._db[cond1 & cond2].to_parquet(year_dir / f'{month}.pq')

    def save_db_from_uuids(self, uuid_list: List[str]) -> None:
        """
        given a list of uuids, extracts the transaction months and saves the relevant parquet
        files
        :param uuid_list:
        :return:
        """
        months = self._get_months_from_uuid(uuid_list)
        self.save_db(months)

    def insert_data(self, df: pd.DataFrame) -> Dict[str, int]:
        """
        insert transactions to the db
        :param df: dataframe of transactions
        :return:
        """
        # todo - return how many added and how many skipped (duplicate) to
        #  display to user
        orig_len = len(df)
        df = self._remove_duplicate_trans(df)
        if len(df) == 0:
            return {'added': 0, 'skipped': orig_len - len(df)}
        df = self._add_uuids(df)
        df = self._apply_categories_and_groups(df)
        self._db = pd.concat([self._db, df])
        self._sort_db()
        self._db = self._db.reset_index(drop=True)
        self.save_db_from_uuids(df[TransDBSchema.ID].to_list())

        return {'added': len(df), 'skipped': orig_len - len(df)}

    def _remove_duplicate_trans(self, new_trans_df: pd.DataFrame) -> pd.DataFrame:
        """
        remove duplicate transactions from the new transactions dataframe
        """
        original_len = len(self._db)
        tmp_df = pd.concat([self._db, new_trans_df])
        tmp_df = tmp_df.drop_duplicates(subset=TransDBSchema.get_cols_for_dup_checking(),
                                        keep='first')

        return tmp_df.iloc[original_len:, :]


    @staticmethod
    def _add_uuids(df: pd.DataFrame) -> pd.DataFrame:
        """
        add uuids to the transactions
        :param df: dataframe of transactions
        :return: dataframe of transactions with uuids
        """
        # TODO: maybe vectorize the uuid creation
        df[TransDBSchema.ID] = df.apply(lambda x: create_uuid(), axis=1)

        return df

    def _sort_db(self):
        """
        sort the db by date
        :return:
        """
        self._db['s1'] = self._db[TransDBSchema.SPLIT].str.split('-').str[0]
        self._db['s2'] = self._db[TransDBSchema.SPLIT].str.split('-').str[2]
        self._db = self._db.sort_values(by=[TransDBSchema.DATE, 's1', 's2'],
                                        ascending=False)
        self.drop(columns=['s1', 's2'], inplace=True)
        self._db = self._db.reset_index(drop=True)

    def _apply_categories_and_groups(self, df: pd.DataFrame):
        """
        add categories to new inserted transactions
        :param df: new transactions
        :return:
        """
        for ind, row in df.iterrows():
            payee = row[TransDBSchema.PAYEE]
            cat, group = self._cat_db.get_cat_and_group_by_payee(payee)
            if cat is not None:
                df.loc[ind, TransDBSchema.CAT] = cat
                df.loc[ind, TransDBSchema.CAT_GROUP] = group

        return df

    def add_new_row(self, date: str) -> None:
        """
        when adding a new transaction, add a blank row to the db which will
        probably be edited and populated later
        :return:
        """
        uuid = create_uuid()
        new_row = pd.DataFrame([[None] * self._db.shape[1]],
                               columns=self._db.columns)
        new_row[TransDBSchema.ID] = uuid
        new_row[TransDBSchema.DATE] = pd.to_datetime(date)
        new_row[TransDBSchema.ACCOUNT] = ''

        db = pd.concat([new_row, self._db])
        self._db = apply_dtypes(db,
                                include_date=True,
                                datetime_format='%Y-%m-%d')
        self._db = db.reset_index(drop=True)

        self.save_db_from_uuids([uuid])

    def remove_row_with_id(self, id: str):
        """
        remove row with id
        :param id: id of row to remove
        :return:
        """
        months = self._get_months_from_uuid([id])
        self._db = self._db[self._db[TransDBSchema.ID] != id]
        self.save_db(months)

    def update_cat_col_data(self, col_name: str, index: int, value: Any):
        """
        when updating a category we also might need to change the category group
        :param col_name:
        :param index:
        :param value:
        :return:
        """
        # update mapping of payee to category
        payee = self._db.loc[index, TransDBSchema.PAYEE]
        if check_null(self._db.loc[index, col_name]):  # only update first time
            self._cat_db.update_payee_to_cat_mapping(payee, cat=value)

        self._update_cat_group(index, value)
        self.update_data(col_name, index, value)

    def update_data(self, col_name: str, index: int, value: Any) -> None:
        """
        update a specific cell in the db
        :param col_name:
        :param index:
        :param value:
        :return:
        """
        prev_value = self._db.loc[index, col_name]
        self._db.loc[index, col_name] = value

        # trans moved to another month - save original month to save removal
        if isinstance(prev_value, pd.Timestamp):
            if prev_value.month != pd.to_datetime(value).month:
                self.save_db([(str(prev_value.year), str(prev_value.month))])

        uuid_list = [self._db.loc[index, TransDBSchema.ID]]

        if col_name == TransDBSchema.DATE:
            self._sort_db()

        self.save_db_from_uuids(uuid_list)

    def set_specific_month(self, year: str, month: str):
        monthly_trans = self.get_trans_by_month(year, month)
        self.specific_month = TransactionsDBParquet(self._cat_db, monthly_trans)


    def _get_months_from_uuid(self, uuid_lst: List[str]) -> List[
        Tuple[str, str]]:
        """
        get the months of the transactions with the given uuids
        :return: a set of lists of form [year, month]
        """
        months = set()
        for uuid in uuid_lst:
            date = self._db[self._db[TransDBSchema.ID] == uuid][
                TransDBSchema.DATE]
            if date.isnull().any():
                return []

            date = date.iloc[0]
            months.add((date.year, date.month))

        return list(months)

    def _update_cat_group(self, index: int, new_value: str):
        """
        update the category group of a transaction
        """
        group = self._cat_db.get_group_of_category(new_value)
        self.update_data(TransDBSchema.CAT_GROUP, index, group)

    def apply_split(self,
                    row_id: str,
                    split_amounts,
                    split_memos,
                    split_cats) -> List[str]:
        """
        Split a transaction into multiple categories
        :param row_id:
        :param split_amounts:
        :param split_memos:
        :param split_cats:
        :return:
        """
        non_na_splits = self._db[TransDBSchema.SPLIT][~self._db[TransDBSchema.SPLIT].isna()]
        next_split = self._get_next_split_index(non_na_splits)
        split_row = self._db[self._db[TransDBSchema.ID] == row_id]
        split_row[TransDBSchema.SPLIT] = f'{next_split}-0'

        ids = []
        for split_ind, (amount, cat, memo) in enumerate(zip(split_amounts, split_cats, split_memos)):
            new_split = split_row.copy()
            new_split[TransDBSchema.AMOUNT] = amount

            if new_split[TransDBSchema.OUTFLOW].iloc[0] > 0:
                new_split[TransDBSchema.OUTFLOW] = amount
            else:
                new_split[TransDBSchema.INFLOW] = amount

            ids.append(create_uuid())
            new_split[TransDBSchema.ID] = ids[-1]

            new_split[TransDBSchema.CAT] = cat
            new_split[TransDBSchema.CAT_GROUP] = self._cat_db.get_group_of_category(cat)
            new_split[TransDBSchema.MEMO] = memo
            new_split[TransDBSchema.SPLIT] = f'{next_split}-{split_ind + 1}'
            self._db = pd.concat([self._db, new_split])

        self._db.drop(index=split_row.index, inplace=True)
        self._sort_db()
        # self.save_db_from_uuids(ids)
        return ids

    @staticmethod
    def _get_next_split_index(col: pd.Series) -> int:
        if len(col) == 0:
            return 1
        col_copy = col.copy().to_frame()
        col_copy['s1'] = col_copy.iloc[0, :].str.split('-').str[0]
        return col_copy['s1'].astype(int).sort_values().iloc[-1] + 1

    def get_data_by_group(self, group: str):
        """
        get data by group
        :param group: group to get data from
        :return: dataframe of data
        """
        return TransactionsDBParquet(self._cat_db,
                                     self._db[self._db[TransDBSchema.CAT_GROUP]
                                              == group])

    def get_data_by_cat(self, cat: str) -> pd.DataFrame:
        """
        get data by category
        :param cat: category to get data from
        :return: dataframe of data
        """
        return self._db[self._db[TransDBSchema.CAT] == cat]

    def get_data_by_id(self, uuid_list: List[str]) -> pd.DataFrame:
        """
        get transactions by id
        :param uuid_list: list of uuids
        :return: dataframe of transactions
        """
        return self._db[self._db[TransDBSchema.ID].isin(uuid_list)]

    def get_data_by_col_val(self,
                            col_val_dict: Dict[str, Any]) -> pd.DataFrame:
        """
        get transactions by column value - supports only intersection of values.
        :param col_val_dict: dict where the keys are the columns and the values
               are the values in the columns. Supports only one value per column
        :return: dataframe of transactions
        """
        db_tmp = self._db
        for col, val in col_val_dict.items():
            db_tmp = db_tmp[db_tmp[col] == val]

        return db_tmp

    # def get_current_month_trans(self):
    #     """
    #     get data of current month
    #     :return: dataframe of data
    #     """
    #     current_month = datetime.now().strftime('%Y-%m')
    #     curr_trans = self._db[self._db[TransDBSchema.DATE].dt.strftime('%Y-%m')
    #                           == current_month]
    #     return TransactionsDBParquet(self._cat_db, curr_trans)

    def get_trans_by_month(self, year: str, month: str) -> pd.DataFrame:
        """
        get transactions of specific month
        :param year: year in for digit format (e.g. 2020)
        :param month: month in two digit format (e.g. 04 for april)
        :return: dataframe of data
        """
        if len(year) != 4 or len(month) != 2:
            raise ValueError('year must be in 4 digit format and month must be'
                             ' in two digit format')
        target_date = f'{year}-{month}'
        target_trans = self._db[self._db[TransDBSchema.DATE].dt.strftime(
            '%Y-%m') == target_date]

        return target_trans

    @staticmethod
    def _get_category_vals(df) -> Dict[str, pd.CategoricalDtype]:
        """
        get all possible values for category columns
        :param df:
        :return:
        """
        vals = {}
        for col in TransDBSchema.get_categorical_cols():
            vals[col] = df[col].cat.categories.tolist()

        return vals

    def get_records(self) -> dict:
        """
        get records of db to feed into dash datatable
        :return:
        """
        formatted_df = format_date_col_for_display(self._db,
                                                   TransDBSchema.DATE)
        return formatted_df.to_dict('records')

    @property
    def db(self):
        return self._db


def apply_dtypes(df: pd.DataFrame,
                 include_date: bool = True,
                 datetime_format: Optional[str] = None) -> pd.DataFrame:
    """
    apply the dtypes of the db schema to the dataframe
    :param df: dataframe to apply dtypes to
    :param include_date: whether to include date column
    :param datetime_format: format of the date column according to input
                            trans file
    :return: dataframe with dtypes applied
    """
    if include_date:
        df[TransDBSchema.DATE] = pd.to_datetime(df[TransDBSchema.DATE],
                                                format=datetime_format)
    df[TransDBSchema.RECONCILED] = df[TransDBSchema.RECONCILED].astype(
        bool)
    df[TransDBSchema.INFLOW] = df[TransDBSchema.INFLOW].astype(float)
    df[TransDBSchema.OUTFLOW] = df[TransDBSchema.OUTFLOW].astype(float)
    df[TransDBSchema.AMOUNT] = df[TransDBSchema.AMOUNT].astype(float)
    df[TransDBSchema.CAT] = df[TransDBSchema.CAT].astype('category')
    df[TransDBSchema.CAT_GROUP] = df[TransDBSchema.CAT_GROUP]. \
        astype('category')
    df[TransDBSchema.ACCOUNT] = df[TransDBSchema.ACCOUNT].astype(
        'category')
    df[TransDBSchema.RECONCILED] = df[TransDBSchema.RECONCILED].astype(
        bool)

    return df
