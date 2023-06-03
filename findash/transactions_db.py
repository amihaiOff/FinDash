from dataclasses import dataclass, fields
from datetime import datetime
from functools import reduce
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional, Union
import logging

import pandas as pd

from categories_db import CategoriesDB
from file_io import FileIO
from utils import create_uuid, format_date_col_for_display, \
    check_null, get_current_year_and_month, Change, ChangeType, START_DATE_DEFAULT
from change_list import ChangeList

"""
The purpose of this module is to provide a database for transactions.
The database in a collection of parquet files, one per month, organized by year.
This is the recorded history of the transactions.
"""

logger = logging.getLogger('Logger')


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
            cls.ID: 'ID'
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
        return [TransDBSchema.DATE, TransDBSchema.PAYEE,
                TransDBSchema.AMOUNT, TransDBSchema.INFLOW, TransDBSchema.OUTFLOW,
                TransDBSchema.CAT, TransDBSchema.MEMO, TransDBSchema.ACCOUNT, TransDBSchema.ID]

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
            'str': [cls.PAYEE, cls.MEMO, cls.ID],
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
                 file_io: FileIO,
                 cat_db: CategoriesDB,
                 accounts: dict,  # todo - how to solve the problem that I cannot import accounts type for typing?
                 db: pd.DataFrame = pd.DataFrame()):

        self._file_io = file_io
        self._path_from_data_root = 'trans_db'
        self._db: pd.DataFrame = db
        self._full_db: pd.DataFrame = db.copy()
        self._filtered_db: pd.DataFrame = db.copy()
        self._cat_db = cat_db
        self._accounts = accounts
        self._specific_month_date: str = ''
        self.change_list = ChangeList()
        self._applied_filters = {}

    def __getitem__(self, item):
        return TransactionsDBParquet(self._file_io,
                                     self._cat_db,
                                     self._accounts,
                                     self._db.__getitem__(item))

    def __getattr__(self, item):
        return self._db.__getattr__(item)

    def __setitem__(self, name, value):
        return TransactionsDBParquet(
            self._file_io,
            self._cat_db,
            self._accounts,
            self._db.__setitem__(name, value))

    def __eq__(self, other):
        return self._db.__eq__(other)

    def __ge__(self, other):
        return self._db.__ge__(other)

    def __le__(self, other):
        return self._db.__le__(other)

    def __lt__(self, other):
        return self._db.__lt__(other)

    def __gt__(self, other):
        return self.__ge__(other)

    def __repr__(self):
        return self._db.__repr__()

    def __len__(self):
        return len(self._db)

    def connect(self):
        """
        load parquet files of transactions
        :return:
        """
        pq_files = []
        for year_dir in self._file_io.get_dirs_in_dir(
                self._path_from_data_root, full_paths=True):
            pq_files.extend(self._file_io.load_file(file) for file in
                            self._file_io.get_files_in_dir(year_dir,
                                                           full_paths=True))

        if not len(pq_files):
            logger.info('init empty trans db')
            self._init_empty_db()
            return

        # category_vals = self._get_category_vals(pq_files[0])
        final_df = pd.concat(pq_files)
        final_df = apply_dtypes(final_df, include_date=False)
        final_df = self._set_cat_col_categories(final_df)
        self._db = final_df

        self._sort_db()

        # set monthly_trans
        self.set_specific_month(*get_current_year_and_month())
        logger.info('loaded trans db')

    def _set_cat_col_categories(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        given a dict of col_name: cat_vals, set the categorical values of col_name
        to cat_val, in df
        :return: df with set categoricals
        """
        df[TransDBSchema.CAT] = df[TransDBSchema.CAT].cat.set_categories(
            self._cat_db.get_categories())
        df[TransDBSchema.CAT_GROUP] = df[TransDBSchema.CAT_GROUP].\
            cat.set_categories(self._cat_db.get_group_names())
        df[TransDBSchema.ACCOUNT] = df[TransDBSchema.ACCOUNT].\
            cat.set_categories(list(self._accounts.keys()))

        return df

    def _init_empty_db(self):
        # todo - not in use for now, need to find solution for loading app with empty db
        cols_with_def_value = TransDBSchema.get_non_mandatory_cols()
        cols_with_def_value.update({TransDBSchema.DATE: pd.to_datetime(START_DATE_DEFAULT),
                                    TransDBSchema.PAYEE: 'null',
                                    TransDBSchema.AMOUNT: 0.0,
                                    TransDBSchema.ID: 0})
        self._db = pd.DataFrame(cols_with_def_value, index=[0])

    def save_db(self, months_to_save: List[Tuple[str, str]]) -> None:
        """
        save the db to a parquet file. Saves only modified months
        :param months_to_save: list of tuples of form (year, month)
        :return:
        """
        for year, month in months_to_save:
            year_dir = Path(f'{self._path_from_data_root}/{year}')
            cond1 = self._db[TransDBSchema.DATE].dt.year == int(year)
            cond2 = self._db[TransDBSchema.DATE].dt.month == int(month)
            self._file_io.save_file(str(year_dir / f'{month}.pq'),
                                    self._db[cond1 & cond2])
            logger.info(f'saved transactions db to {year_dir / f"{month}.pq"}')

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

    def add_new_row(self) -> None:
        """
        when adding a new transaction, add a blank row to the db which will
        probably be edited and populated later
        :return:
        """
        uuid = create_uuid()
        new_row = pd.DataFrame([[None] * self._db.shape[1]],
                               columns=self._db.columns)
        new_row[TransDBSchema.ID] = uuid
        date = datetime.now().strftime('%Y-%m-%d')
        new_row[TransDBSchema.DATE] = pd.to_datetime(date)
        new_row[TransDBSchema.ACCOUNT] = ''
        new_row[TransDBSchema.PAYEE] = ''
        new_row[TransDBSchema.INFLOW] = 0
        new_row[TransDBSchema.OUTFLOW] = 0

        db = pd.concat([new_row, self._db])
        self._db = apply_dtypes(db,
                                include_date=True,
                                datetime_format='%Y-%m-%d')
        self._db = db.reset_index(drop=True)
        logger.info(f'added new row with id {uuid}')

        self.save_db_from_uuids([uuid])

    def remove_row_with_id(self, id: str):
        """
        remove row with id
        :param id: id of row to remove
        :return:
        """
        months = self._get_months_from_uuid([id])
        self._db = self._db[self._db[TransDBSchema.ID] != id]
        self._sort_db()
        self.save_db(months)

    def _update_cat_col_data(self, col_name: str, trans_id: str, value: Any):
        """
        when updating a category we also might need to change the category group
        :param col_name:
        :param index:
        :param value:
        :return:
        """
        # None is not a valid category
        value = '' if value is None else value

        index = self._get_row_index_from_trans_id(trans_id)
        # update mapping of payee to category
        payee = self._db.loc[index, TransDBSchema.PAYEE]
        if check_null(self._db.loc[index, col_name]):  # only update first time
            self._cat_db.update_payee_to_cat_mapping(payee, cat=value)

        self._update_cat_group(trans_id, value)
        self._update_data(col_name, trans_id, value)

    def submit_change(self, change: Change):
        if change.change_type == ChangeType.ADD_ROW:
            self.add_new_row()

        elif change.change_type == ChangeType.DELETE_ROW:
            self.remove_row_with_id(change.trans_id)

        elif change.change_type == ChangeType.CHANGE_DATA:
            if change.current_value == change.prev_value:
                return
            if change.col_name == TransDBSchema.CAT:
                # move all trans logic to here.
                # add an optional parameter in the change object
                self._update_cat_col_data(change.col_name,
                                          change.trans_id,
                                          change.current_value)
            else:
                self._update_data(change.col_name, change.trans_id, change.current_value)

        self.change_list.append(change)

    def undo(self):
        pass

    def redo(self):
        pass

    def _update_data(self, col_name: str, trans_id: str, value: Any) -> None:
        """
        update a specific cell in the db
        :param col_name:
        :param index:
        :param value:
        :return:
        """
        index = self._get_row_index_from_trans_id(trans_id)
        prev_value = self._db.loc[index, col_name]
        self._db.loc[index, col_name] = value

        # a change in inflow\outflow occured, should also change amount
        if col_name in [TransDBSchema.OUTFLOW, TransDBSchema.INFLOW]:
            self._db.loc[index, TransDBSchema.AMOUNT] = value

        # trans moved to another month - save original month to save removal
        if (
            isinstance(prev_value, pd.Timestamp)
            and prev_value.month != pd.to_datetime(value).month
        ):
            self.save_db([(str(prev_value.year), str(prev_value.month))])

        uuid_list = [self._db.loc[index, TransDBSchema.ID]]

        if col_name == TransDBSchema.DATE:
            self._sort_db()

        self.save_db_from_uuids(uuid_list)

    def set_specific_month(self, year: str, month: str):
        self._specific_month_date = f'{year}-{month}'

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

    def _update_cat_group(self, trans_id: str, new_value: str):
        """
        update the category group of a transaction
        """
        group = self._cat_db.get_group_of_category(new_value)
        self._update_data(TransDBSchema.CAT_GROUP, trans_id, group)

    def _create_new_split_row(self,
                              row_to_split: pd.Series,
                              amount: str,
                              cat: str,
                              memo: str,
                              split_ind: int,
                              next_split: int) -> pd.Series:
        new_split = row_to_split.copy()
        amount = float(amount)
        new_split[TransDBSchema.AMOUNT] = amount

        if new_split[TransDBSchema.OUTFLOW].iloc[0] > 0:
            new_split[TransDBSchema.OUTFLOW] = amount
        else:
            new_split[TransDBSchema.INFLOW] = amount

        new_split[
            TransDBSchema.PAYEE] = f'[{split_ind}] {new_split[TransDBSchema.PAYEE].iloc[0]}'
        new_split[TransDBSchema.ID] = create_uuid()
        new_split.index = [len(self._db)]

        new_split[TransDBSchema.CAT] = cat
        new_split[
            TransDBSchema.CAT_GROUP] = self._cat_db.get_group_of_category(cat)
        new_split[TransDBSchema.MEMO] = memo
        new_split[TransDBSchema.SPLIT] = f'{next_split}-{split_ind + 1}'

        return new_split

    def apply_split(self,
                    row_id: str,
                    split_amounts: List[str],
                    split_memos: List[str],
                    split_cats: List[str]) -> List[pd.Series]:
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

        rows = []
        for split_ind, (amount, cat, memo) in enumerate(zip(split_amounts, split_cats, split_memos)):
            new_split_row = self._create_new_split_row(split_row, amount, cat, memo, split_ind, next_split)
            self._db = pd.concat([self._db, new_split_row])
            rows.append(new_split_row)

        self._db.drop(index=split_row.index, inplace=True)
        self._sort_db()
        self.save_db_from_uuids([row[TransDBSchema.ID].iloc[0] for row in rows])
        return rows

    @staticmethod
    def _get_next_split_index(col: pd.Series) -> int:
        if len(col) == 0:
            return 1
        col_copy = col.copy().to_frame()
        col_copy['s1'] = col_copy.iloc[0, :].str.split('-').str[0].iloc[0]
        return col_copy['s1'].astype(int).sort_values().iloc[-1] + 1

    def get_data_by_group(self, group: str):
        """
        get data by group
        :param group: group to get data from
        :return: dataframe of data
        """
        return TransactionsDBParquet(
            self._file_io,
            self._cat_db,
            self._accounts,
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
        return self._db[
            self._db[TransDBSchema.DATE].dt.strftime('%Y-%m') == target_date
        ]

    @staticmethod
    def _get_category_vals(df) -> Dict[str, pd.CategoricalDtype]:
        """
        get all possible values for category columns
        :param df:
        :return:
        """
        return {
            col: df[col].cat.categories.tolist()
            for col in TransDBSchema.get_categorical_cols()
        }

    def _get_row_index_from_trans_id(self, trans_id: str):
        return self._db[self._db[TransDBSchema.ID] == trans_id].index[0]

    def get_records(self) -> dict:
        """
        get records of db to feed into dash datatable
        :return:
        """
        df = self._db.copy()
        if len(self._applied_filters) > 0:
            df = self._db[reduce(lambda x, y: x & y, self._applied_filters.values())]

        formatted_df = format_date_col_for_display(df,
                                                   TransDBSchema.DATE)
        return formatted_df.to_dict('records')

    def set_filters(self, filters: Dict[str, pd.Series]):
        """
        set filters for the db
        :param filters: list of filters
        :return:
        """
        for filter_name, filter_series in filters.items():
            if not isinstance(filter_series, pd.Series) and not isinstance(filter_series, bool):
                raise ValueError(f'filter {filter_name} must be a pandas series '
                                 f'of dtype bool')

        self._applied_filters = filters

    @property
    def db(self):
        return self._db

    @property
    def specific_month(self):
        year, month = self._specific_month_date.split('-')
        trans = self.get_trans_by_month(year, month)
        return TransactionsDBParquet(self._file_io,
                                     self._cat_db,
                                     self._accounts,
                                     trans)


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
