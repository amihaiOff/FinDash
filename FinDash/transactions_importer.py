from logging import getLogger
from typing import TextIO, Union

import pandas as pd

from accounts import Account, InflowSign
from db import TransactionsDBSchema

logger = getLogger()


def import_file(trans_file_path: Union[str, TextIO], account: Account) -> pd.DataFrame:
    trans_file = _load_file(trans_file_path)
    trans_file = _apply_col_mapping(trans_file, account)
    trans_file = _fit_to_db_scheme(trans_file, account)
    return trans_file


def _apply_col_mapping(trans_file: pd.DataFrame, account: Account):
    """
    change column names according to mapping from account object
    :param trans_file:
    :param account:
    :return:
    """
    for source_col, dest_col in account.get_col_mapping().col_mapping.items():
        if source_col in trans_file.columns:
            trans_file = trans_file.rename(columns={source_col: dest_col})
        else:
            logger.warning(f'col {source_col} not found in transactions file')

    return trans_file


def _fit_to_db_scheme(trans_file: pd.DataFrame, account: Account):
    for col_name, default_val in TransactionsDBSchema.get_non_mandatory_cols().items():
        if col_name not in trans_file.columns:
            trans_file[col_name] = default_val

    # convert amount col into inflow and outflow
    cond = trans_file[TransactionsDBSchema.AMOUNT] < 0 if account.inflow_sign == InflowSign.MINUS else \
        trans_file[TransactionsDBSchema.AMOUNT] > 0
    trans_file[TransactionsDBSchema.INFLOW][cond] = trans_file[TransactionsDBSchema.AMOUNT][cond].abs()
    trans_file[TransactionsDBSchema.OUTFLOW][trans_file[TransactionsDBSchema.INFLOW] == 0] = \
        trans_file[TransactionsDBSchema.AMOUNT][trans_file[TransactionsDBSchema.INFLOW] == 0]

    # add account name
    trans_file[TransactionsDBSchema.ACCOUNT] = account.name
    return trans_file


def _load_file(trans_file_path: str) -> pd.DataFrame:
    if trans_file_path.endswith('csv'):
        return pd.read_csv(trans_file_path)
    elif trans_file_path.endswith('xls') or trans_file_path.endswith('xlsx'):
        return pd.read_excel(trans_file_path)
    elif trans_file_path.endswith('parquet'):
        return pd.read_parquet(trans_file_path)
    else:
        raise ValueError(f'Transaction file {trans_file_path} not supported.')
