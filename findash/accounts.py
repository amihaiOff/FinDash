import contextlib
import os
from abc import abstractmethod, ABC
from enum import Enum
import yaml

import numpy as np
from typing import Dict
from dotenv import load_dotenv
import pandas as pd

from findash.file_io import FileIO
from findash.transactions_db import TransDBSchema
from findash.utils import MappingDict

ACCOUNTS = {}


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
        self._validate_mapping()

    def _validate_mapping(self):
        """
        make sure the mapping includes all mandatory columns
        :return:
        """
        for option in TransDBSchema.get_mandatory_col_sets():
            col_inter = set(self._dict_col_mapping.values()).intersection(set(option))
            col_diff = col_inter.symmetric_difference(set(option))
            if not col_diff:
                return

        raise ValueError('Missing mandatory cols in transaction file')

    @property
    def col_mapping(self):
        return self._dict_col_mapping


class Account(ABC):
    def __init__(self, name: str):
        self._name = name
        self._validate_account()

    def _validate_account(self):
        self._get_col_mapping()._validate_mapping()

    @abstractmethod
    def _get_col_mapping(self) -> ColMapping:
        pass

    @abstractmethod
    def process_trans_file(self, trans_file: pd.DataFrame) -> pd.DataFrame:
        """
        The purpose of this processing is to format the file such that it has
        the mandatory columns and removes unnecessary rows.
        :param trans_file:
        :return:
        """
        pass

    @property
    def name(self):
        return self._name

    @property
    @abstractmethod
    def inflow_sign(self) -> InflowSign:
        pass

    @abstractmethod
    def get_datetime_format(self) -> str:
        pass


class FIBI(Account):
    def process_trans_file(self, trans_file: pd.DataFrame) -> pd.DataFrame:
        trans_file.columns = trans_file.iloc[1, :]
        first_trans_row_ind = self._find_first_date_row_ind(trans_file)
        trans_file = trans_file.drop(trans_file.index[:first_trans_row_ind])
        trans_file = _apply_col_mapping(trans_file, self._get_col_mapping())
        trans_file[TransDBSchema.INFLOW] = \
            trans_file[TransDBSchema.INFLOW].map(MappingDict({' ': '0'}))
        trans_file[TransDBSchema.OUTFLOW] = \
            trans_file[TransDBSchema.OUTFLOW].map(MappingDict({' ': '0'}))
        trans_file[TransDBSchema.AMOUNT] = np.where(trans_file[TransDBSchema.OUTFLOW] != '0',
                                                    trans_file[TransDBSchema.OUTFLOW],
                                                    trans_file[TransDBSchema.INFLOW] * self.inflow_sign.value)
        return trans_file

    @staticmethod
    def _find_first_date_row_ind(trans_file: pd.DataFrame) -> int:
        for row_ind, row in trans_file.iloc[:, -1].items():
            with contextlib.suppress(ValueError):
                res = pd.to_datetime(row)
                if pd.notna(res):
                    return row_ind

    def __init__(self, name: str):
        self.is_checking = True
        self.institution = Institution.FIBI
        super().__init__(name)

    def _get_col_mapping(self) -> ColMapping:
        col_mapping = {
            'תאריך': TransDBSchema.DATE,
            'תיאור': TransDBSchema.PAYEE,
            'זכות': TransDBSchema.INFLOW,
            'חובה': TransDBSchema.OUTFLOW,
            'תאור': TransDBSchema.PAYEE,
        }

        return ColMapping(col_mapping)

    @property
    def inflow_sign(self) -> InflowSign:
        return InflowSign.MINUS

    def get_datetime_format(self) -> str:
        pass


class CAL(Account):
    def __init__(self, name: str):
        self.institution = Institution.CAL
        self.is_checking = False
        super().__init__(name)

    def _get_col_mapping(self) -> ColMapping:
        col_mapping = {
            "תאריך עסקה": TransDBSchema.DATE,
            "סכום חיוב": TransDBSchema.AMOUNT,
            "שם בית עסק": TransDBSchema.PAYEE,
            "הערות": TransDBSchema.MEMO,
        }

        return ColMapping(col_mapping)

    def process_trans_file(self, trans_file: pd.DataFrame):
        trans_file.columns = trans_file.iloc[1, :]  # set columns names
        trans_file = trans_file.drop(trans_file.index[:3])  # remove the first 2 rows which are headers
        trans_file = _apply_col_mapping(trans_file, self._get_col_mapping())
        return trans_file

    @property
    def inflow_sign(self) -> InflowSign:
        return InflowSign.MINUS

    def get_datetime_format(self) -> str:
        return "%d/%m/%Y"


class OZ(Account):
    def __init__(self, name: str):
        self.institution = Institution.OZ
        self.is_checking = True
        super().__init__(name)

    def _get_col_mapping(self) -> ColMapping:
        col_mapping = {}

        return ColMapping(col_mapping)

    @property
    def inflow_sign(self) -> InflowSign:
        return InflowSign.MINUS

    def process_trans_file(self, trans_file: pd.DataFrame) -> pd.DataFrame:
        pass

    def get_datetime_format(self) -> str:
        pass


def _apply_col_mapping(trans_file: pd.DataFrame,
                       col_mapping: ColMapping) -> pd.DataFrame:
    """
    change column names according to mapping from account object
    :param trans_file:
    :return:
    """
    for source_col, dest_col in col_mapping.col_mapping.items():
        if source_col in trans_file.columns:
            trans_file = trans_file.rename(columns={source_col: dest_col})
        # else:
        #     logger.warning(
        #         f'col {source_col} not found in transactions file')

    return trans_file


def init_accounts(file_io: FileIO) -> None:
    """
    create account classes of all available accounts as defined in
    accounts.yaml - this is to make it possible to choose from all accounts
    in trans table dropdown.
    :return:
    """
    accounts_db_path = 'accounts.yaml'
    accounts_yaml = file_io.read_yaml(accounts_db_path)
    for name, settings in accounts_yaml.items():
        cls = accounts_register[settings['institution']]
        acc = cls(name)
        ACCOUNTS[name] = acc


accounts_register = {
        'fibi': FIBI,
        'cal': CAL,
        'oz': OZ,
    }
