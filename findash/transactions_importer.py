from typing import TextIO, Union

import pandas as pd

from accounts import Account, InflowSign
from transactions_db import TransDBSchema
from transactions_db import apply_dtypes


# logger = getLogger()


def import_file(trans_file_path: Union[str, TextIO], account: Account) \
        -> pd.DataFrame:
    trans_file = _load_file(trans_file_path)
    trans_file = account.process_trans_file(trans_file)
    trans_file = _fit_to_db_scheme(trans_file, account.name)
    trans_file = _remove_non_numeric_chars(trans_file)
    trans_file = apply_dtypes(trans_file,
                              datetime_format=account.get_datetime_format())
    trans_file = _populate_inflow_outflow(trans_file, account.inflow_sign)
    trans_file = _fill_nan_values(trans_file)
    return trans_file


def _fit_to_db_scheme(trans_file: pd.DataFrame, account_name: str) \
        -> pd.DataFrame:
    for col_name, default_val in TransDBSchema.get_non_mandatory_cols().items():
        if col_name not in trans_file.columns:
            trans_file[col_name] = default_val

    for col in trans_file.columns:
        if col not in TransDBSchema.get_db_col_vals():
            trans_file = trans_file.drop(columns=col)

    # add account name
    trans_file[TransDBSchema.ACCOUNT] = account_name
    return trans_file


def _populate_inflow_outflow(trans_file: pd.DataFrame,
                             account_inflow_sign: InflowSign) -> pd.DataFrame:
    """
    populate inflow and outflow columns
    :param trans_file: dataframe to populate
    :return: dataframe with inflow and outflow populated
    """
    # convert amount col into inflow and outflow
    cond = trans_file[TransDBSchema.AMOUNT] < 0 if account_inflow_sign == InflowSign.MINUS else \
        trans_file[TransDBSchema.AMOUNT] > 0
    trans_file[TransDBSchema.INFLOW][cond] = trans_file[TransDBSchema.AMOUNT][cond].abs()
    trans_file[TransDBSchema.OUTFLOW][trans_file[TransDBSchema.INFLOW] == 0] = \
        trans_file[TransDBSchema.AMOUNT][trans_file[TransDBSchema.INFLOW] == 0]

    return trans_file


def _load_file(trans_file_path: str) -> pd.DataFrame:
    if trans_file_path.name.endswith('csv'):
        file = pd.read_csv(trans_file_path)
        if 'Unnamed: 0' in file.columns:
            return file.drop(columns=['Unnamed: 0'])
        return file
    elif trans_file_path.endswith('xls') or trans_file_path.endswith('xlsx'):
        return pd.read_excel(trans_file_path)
    elif trans_file_path.endswith('parquet'):
        return pd.read_parquet(trans_file_path)
    else:
        raise ValueError(f'Transaction file {trans_file_path} not supported.')


def _remove_non_numeric_chars(trans_file: pd.DataFrame) -> pd.DataFrame:
    """
    remove non-numeric chars from numeric columns
    """
    for col in TransDBSchema.get_numeric_cols():
        trans_file[col] = trans_file[col].astype(str).str.replace(r'[^0-9\.-]+', '')

    return trans_file


def _fill_nan_values(trans_file: pd.DataFrame) -> pd.DataFrame:
    """
    fill nan values
    :param trans_file:
    :return:
    """
    trans_file[TransDBSchema.INFLOW] = trans_file[TransDBSchema.INFLOW].fillna(0)
    trans_file[TransDBSchema.OUTFLOW] = trans_file[TransDBSchema.OUTFLOW].fillna(0)
    trans_file[TransDBSchema.AMOUNT] = trans_file[TransDBSchema.AMOUNT].fillna(0)
    return trans_file
