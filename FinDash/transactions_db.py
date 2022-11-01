from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

from db import Record
from utils import SETTINGS

"""
The purpose of this module is to provide a database for transactions.
The database in a collection of parquet files, one per month, organized by year.
This is the recorded history of the transactions.
"""


class TransactionsDBParquet:
    def __init__(self):
        self._db = self.connect(SETTINGS['trans_db_path'])

    @staticmethod
    def connect(db_path: str):
        """
        load parquet files of transactions
        :param db_path: path to db root folder
        :return:
        """
        root_path = Path(db_path)
        if not root_path.exists():
            return pd.DataFrame()

        pq_files = []
        for folder in root_path.glob('[0-9]+'):
            for file in folder.iterdir():
                pq_files.append(pd.read_parquet(file))

        return pd.concat(pq_files)

    def disconnect(self):
        """
        In the case of a parquet db, disconnecting will only save the db
        """
        raise NotImplementedError('disconnecting from a parquet db is not implemented')

    def save_db(self, months_to_save: List[List[str]]) -> None:
        """
        save the db to a parquet file. Savees only modified months
        :param months_to_save: list of tuples of form (year, month)
        :return:
        """
        for year, month in months_to_save:
            self._db[self._db['year'] == year and self._db['month'] == month].to_parquet(
                Path(SETTINGS['trans_db_path']) / year / f'{month}.parquet')

    def save_db_from_uuid(self, uuid_list: List[str]) -> None:
        """
        given a list of uuids, extracts the transaction months and saves the relevant parquet
        files
        :param uuid_list:
        :return:
        """
        months = self._get_months_from_uuid(uuid_list)
        self.save_db(months)

    def get_data_by_id(self, uuid_list: List[str]) -> pd.DataFrame:
        """
        get transactions by id
        :param uuid_list: list of uuids
        :return: dataframe of transactions
        """
        return self._db[self._db['id'].isin(uuid_list)]

    def get_data_by_col_val(self, col_val_dict: Dict[str, Any]) -> pd.DataFrame:
        """
        get transactions by column value - supports only intersection of values.
        :param col_val_dict: dict where the keys are the columns and the values are the values
                             in the columns. Supports only one value per column
        :return: dataframe of transactions
        """
        db_tmp = self._db
        for col, val in col_val_dict.items():
            db_tmp = db_tmp[db_tmp[col] == val]

        return db_tmp

    def insert_data(self, df: pd.DataFrame) -> None:
        """
        insert transactions to the db
        :param df: dataframe of transactions
        :return:
        """
        self._db = pd.concat([self._db, df])
        self.save_db_from_uuid(df['id'].to_list())

    def insert_record(self, record: Record):
        """
        insert a record to the db
        :param record: record to insert
        :return:
        """
        self._db = pd.concat([self._db, record.to_df()])
        self.save_db_from_uuid([record.id])

    def update_data(self):
        pass

    def delete_data(self, uuid_list: List[str]) -> None:
        """
        delete transactions from the db
        :param uuid_list: list of uuids
        :return:
        """
        months = self._get_months_from_uuid(uuid_list)
        self._db = self._db[~self._db['id'].isin(uuid_list)]
        self.save_db(months)

    def _get_months_from_uuid(self, uuid_lst: List[str]) -> List[List[str]]:
        """
        get the months of the transactions with the given uuids
        :return: a set of lists of form [year, month]
        """
        months = set()
        for uuid in uuid_lst:
            months.add(self._db[self._db['id'] == uuid][['year', 'month']].to_list())

        return list(months)
