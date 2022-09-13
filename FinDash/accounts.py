from abc import abstractmethod, ABC
from enum import Enum
from typing import Dict

from transactions_db import TransactionsColNames

class Institution(Enum):
    FIBI = 'fibi'
    CAL = 'cal'
    OZ = 'oz'


class InflowSign(Enum):
    MINUS = -1
    PLUS = 1

# todo think of way of enforcing mandatory cols
class ColMapping:
    MANDATORY_COLS = TransactionsColNames.get_mandatory_cols()
    def __init__(self, ):
        pass


class Account(ABC):
    def __init__(self, name: str, institution: Institution):
        self._name = name
        self._institution = institution

    @abstractmethod
    def get_col_mapping(self) -> Dict[str, str]:
        pass

    @property
    def name(self):
        return self._name

    @property
    def institution(self):
        return self._institution

    @abstractmethod
    @property
    def inflow_sign(self) -> InflowSign:
        pass


class FIBI(Account):
    def __init__(self, name: str):
        super().__init__(name, Institution.FIBI)

    def get_col_mapping(self) -> Dict[str, str]:
        return {

        }

    @property
    def inflow_sign(self) -> InflowSign:
        return InflowSign.MINUS


class CAL(Account):
    def __init__(self, name: str):
        super().__init__(name, Institution.CAL)

    def get_col_mapping(self) -> Dict[str, str]:
        return {

        }


class OZ(Account):
    def __init__(self, name: str):
        super().__init__(name, Institution.OZ)

    def get_col_mapping(self) -> Dict[str, str]:
        return {

        }

