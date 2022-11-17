from abc import abstractmethod, ABC
from enum import Enum
from typing import Dict

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
    def get_col_mapping(self) -> ColMapping:
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


class CAL(Account):
    is_checking = False
    institution = Institution.CAL

    def __init__(self, name: str):
        super().__init__(name)

    def get_col_mapping(self) -> ColMapping:
        col_mapping = {
            "Date": 'date',
            "Amount": 'amount',
            "Payee": 'payee',
            "Memo": 'memo',
            "Inflow": 'inflow',
            "Outflow": 'outflow'
        }

        return ColMapping(col_mapping)

    @property
    def inflow_sign(self) -> InflowSign:
        pass  # todo


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

