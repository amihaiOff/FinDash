from abc import abstractmethod, ABC
from enum import Enum
from typing import Dict

from db import TransactionsDBSchema


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
        mandatory_cols = TransactionsDBSchema.get_mandatory_cols()
        col_inter = set(col_mapping.values()).intersection(set(mandatory_cols))
        col_diff = col_inter.symmetric_difference(set(mandatory_cols))
        if len(col_diff) != 0:
            raise ValueError(f'Missing mandatory cols ({col_diff}) in transaction file')

    @property
    def col_mapping(self):
        return self._dict_col_mapping


class Account(ABC):
    def __init__(self, name: str, institution: Institution):
        self._name = name
        self._institution = institution

    @abstractmethod
    def get_col_mapping(self) -> ColMapping:
        pass

    @property
    def name(self):
        return self._name

    @property
    def institution(self):
        return self._institution

    @property
    @abstractmethod
    def inflow_sign(self) -> InflowSign:
        pass


class FIBI(Account):
    def __init__(self, name: str):
        super().__init__(name, Institution.FIBI)

    def get_col_mapping(self) -> ColMapping:
        col_mapping = {

        }

        return ColMapping(col_mapping)

    @property
    def inflow_sign(self) -> InflowSign:
        return InflowSign.MINUS


class CAL(Account):
    def __init__(self, name: str):
        super().__init__(name, Institution.CAL)

    def get_col_mapping(self) -> ColMapping:
        col_mapping = {

        }

        return ColMapping(col_mapping)

    @property
    def inflow_sign(self) -> InflowSign:
        pass  # todo


class OZ(Account):
    def __init__(self, name: str):
        super().__init__(name, Institution.OZ)

    def get_col_mapping(self) -> ColMapping:
        col_mapping = {

        }

        return ColMapping(col_mapping)

    @property
    def inflow_sign(self) -> InflowSign:
        pass  # todo
