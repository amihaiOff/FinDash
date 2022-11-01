from abc import ABC, abstractmethod
from dataclasses import dataclass, fields
from typing import Any, Dict, List, Tuple

import pandas as pd


class DB(ABC):

    @abstractmethod
    def connect(self, db_path: str):
        pass

    @abstractmethod
    def disconnect(self):
        pass

    @abstractmethod
    def get_data_by_id(self, uuid_list: List[str]) -> pd.DataFrame:
        pass

    @abstractmethod
    def insert_data(self, df: pd.DataFrame) -> None:
        pass

    @abstractmethod
    def update_data(self):
        pass

    @abstractmethod
    def delete_data(self, uuid_list: List[str]) -> None:
        pass


@dataclass
class TransactionsDBSchema:
    TRANS_ID: str = 'id'  # todo - add this where needed in existing code
    DATE: str = 'date'
    PAYEE: str = 'payee'
    CAT: str = 'cat'
    MEMO: str = 'memo'
    ACCOUNT: str = 'account'
    INFLOW: str = 'inflow'  # if forex trans will show the conversion to ils here
    OUTFLOW: str = 'outflow'  # if forex trans will show the conversion to ils here
    RECONCILED: str = 'reconciled'
    AMOUNT: str = 'amount'  # can be in forex

    @classmethod
    def get_mandatory_cols(cls) -> Tuple[str, str, str]:
        """
        mandatory cols every raw transactions file must have
        """
        return cls.DATE, cls.PAYEE, cls.AMOUNT

    @classmethod
    def get_non_mandatory_cols(cls) -> Dict[str, Any]:
        """
        dictionary of non-mandatory cols (keys) to add to trans file to align with
        DB schema along with default values (values)
        """
        return {cls.CAT:        '',
                cls.MEMO: '',
                cls.ACCOUNT:    None,
                cls.INFLOW:     0,
                cls.OUTFLOW:    0,
                cls.RECONCILED: False}

    @classmethod
    def get_db_col_names(cls):
        return [f.name for f in fields(cls)]


class Record:
    def to_df(self):
        pass
