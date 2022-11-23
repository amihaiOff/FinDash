from abc import abstractmethod, ABC
from enum import Enum
from typing import Dict

import pandas as pd

from transactions_db import TransDBSchema

CHECKING_ACCOUNTS = []
NON_CHECKING_ACCOUNTS = []


class Institution(Enum):
    FIBI = 'fibi'
    CAL = 'cal'
    OZ = 'oz'


class InflowSign(Enum):
    MINUS = -1
    PLUS = 1


class ColMapping:
    def __init__(self, col_mapping: Dict[str, str]):
        self._dict_col_mapping = col_mapping
        self._validate_mapping(col_mapping)

    @staticmethod
    def _validate_mapping(col_mapping: Dict[str, str]):
        mandatory_cols = TransDBSchema.get_mandatory_cols()
        col_inter = set(col_mapping.values()).intersection(set(mandatory_cols))
        col_diff = col_inter.symmetric_difference(set(mandatory_cols))
        if len(col_diff) != 0:
            raise ValueError(f'Missing mandatory cols ({col_diff}) in transaction file')

    @property
    def col_mapping(self):
        return self._dict_col_mapping


class Account(ABC):
    institution = None  # define in subclass

    def __init__(self, name: str):
        self._name = name

    @abstractmethod
    def _get_col_mapping(self) -> ColMapping:
        pass

    @abstractmethod
    def process_trans_file(self, trans_file: pd.DataFrame) -> pd.DataFrame:
        pass

    @property
    def name(self):
        return self._name

    @property
    def institution(self):
        return self.institution

    @property
    @abstractmethod
    def inflow_sign(self) -> InflowSign:
        pass

    @abstractmethod
    def get_datetime_format(self) -> str:
        pass


class FIBI(Account):
    is_checking = True
    institution = Institution.FIBI

    def __init__(self, name: str):
        super().__init__(name)

    def get_col_mapping(self) -> ColMapping:
        col_mapping = {

        }

        return ColMapping(col_mapping)

    @property
    def inflow_sign(self) -> InflowSign:
        return InflowSign.MINUS

    def get_datetime_format(self) -> str:
        pass


class CAL(Account):
    is_checking = False
    institution = Institution.CAL

    def __init__(self, name: str):
        super().__init__(name)

    def _get_col_mapping(self) -> ColMapping:
        col_mapping = {
            "תאריך העסקה": 'date',
            "סכום החיוב": 'amount',
            "שם בית העסק": 'payee',
            "פירוט נוסף": 'memo',
        }

        return ColMapping(col_mapping)

    def process_trans_file(self, trans_file: pd.DataFrame):
        trans_file.columns = trans_file.iloc[1, :]
        trans_file = trans_file.drop(trans_file.index[:2])
        trans_file = trans_file.drop(trans_file.index[-1])
        trans_file = self._apply_col_mapping(trans_file)
        return trans_file

    def _apply_col_mapping(self, trans_file: pd.DataFrame):
        """
        change column names according to mapping from account object
        :param trans_file:
        :return:
        """
        for source_col, dest_col in self._get_col_mapping().col_mapping.items():
            if source_col in trans_file.columns:
                trans_file = trans_file.rename(columns={source_col: dest_col})
            # else:
            #     logger.warning(
            #         f'col {source_col} not found in transactions file')

        return trans_file

    @property
    def inflow_sign(self) -> InflowSign:
        return InflowSign.MINUS

    def get_datetime_format(self) -> str:
        return "%d/%m/%y"


class OZ(Account):
    is_checking = True
    institution = Institution.OZ

    def __init__(self, name: str):
        super().__init__(name)

    def get_col_mapping(self) -> ColMapping:
        col_mapping = {

        }

        return ColMapping(col_mapping)

    @property
    def inflow_sign(self) -> InflowSign:
        pass  # todo


def init_accounts():
    import importlib, inspect
    for name, cls in inspect.getmembers(importlib.import_module("accounts"),
                                        inspect.isclass):
        if cls.__module__ == 'accounts':
            if issubclass(cls, Account) and cls is not Account:
                if cls.is_checking:
                    CHECKING_ACCOUNTS.append(cls)
                else:
                    NON_CHECKING_ACCOUNTS.append(cls)

