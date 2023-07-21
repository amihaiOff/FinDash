from io import BytesIO, StringIO
from pathlib import Path
from typing import Union

import pandas as pd

from findash.accounts import InflowSign, ACCOUNTS
from findash.transactions_db import TransDBSchema
from findash.transactions_db import apply_dtypes
from findash.categories_db import CategoriesDB


def import_file(trans_file: Union[str, StringIO, BytesIO], account_name: str,
                cat_db: CategoriesDB) -> pd.DataFrame:
    account = ACCOUNTS[account_name]

    trans_file = _load_file(trans_file)
    trans_file = account.process_trans_file(trans_file)
    trans_file = _fit_to_db_scheme(trans_file, account.name)
    trans_file = _remove_non_numeric_chars(trans_file)
    trans_file = apply_dtypes(trans_file,
                              datetime_format=account.get_datetime_format())
    trans_file = _add_cats_to_categorical_columns(trans_file, cat_db)
    trans_file = _populate_inflow_outflow(trans_file, account.inflow_sign)
    trans_file = _fill_nan_values(trans_file)
    trans_file = _apply_prev_categories(trans_file, cat_db)
    return trans_file


def _apply_prev_categories(trans_file: pd.DataFrame, cat_db: CategoriesDB) \
        -> pd.DataFrame:
    """
    apply categories to payees that were already categorized
    :param trans_file:
    """
    for row_ind, row in trans_file.iterrows():
        payee = row.payee
        cat = cat_db.get_payee_category(payee)
        if cat is not None:
            cat_group = cat_db.get_group_of_category(cat)
            trans_file.loc[row_ind, TransDBSchema.CAT] = cat
            trans_file.loc[row_ind, TransDBSchema.CAT_GROUP] = cat_group

    return trans_file


def _add_cats_to_categorical_columns(trans_df: pd.DataFrame,
                                    cat_db: CategoriesDB) -> pd.DataFrame:
    """
    add all possible categories to categorical columns
    :return:
    """
    trans_df[TransDBSchema.CAT] = trans_df[TransDBSchema.CAT].cat.set_categories(cat_db.get_categories())
    trans_df[TransDBSchema.CAT] = trans_df[TransDBSchema.CAT].cat.add_categories('')

    trans_df[TransDBSchema.CAT_GROUP] = trans_df[TransDBSchema.CAT_GROUP].cat.set_categories(cat_db.get_group_names())
    trans_df[TransDBSchema.CAT_GROUP] = trans_df[TransDBSchema.CAT_GROUP].cat.add_categories('')

    trans_df[TransDBSchema.ACCOUNT] = trans_df[TransDBSchema.ACCOUNT].cat.set_categories(list(ACCOUNTS.keys()))
    trans_df[TransDBSchema.ACCOUNT] = trans_df[TransDBSchema.ACCOUNT].cat.add_categories('')

    return trans_df


def _fit_to_db_scheme(trans_file: pd.DataFrame, account_name: str) \
        -> pd.DataFrame:
    for col_name, default_val in TransDBSchema.get_non_mandatory_cols().items():
        if col_name not in trans_file.columns:
            trans_file[col_name] = default_val

    # remove nan named cols
    trans_file = trans_file.loc[:, trans_file.columns.notna()]

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


def _load_file(file: Union[str, StringIO, BytesIO]) -> pd.DataFrame:
    """
    load file into dataframe
    :param file: file to load
    :return: dataframe of file
    """
    if isinstance(file, str) or isinstance(file, Path):
        return _load_file_str(file)
    elif isinstance(file, StringIO):
        return pd.read_csv(file)
    elif isinstance(file, BytesIO):
        return pd.read_excel(file, header=None, index_col=None)
    else:
        raise ValueError('file must be str, StringIO or BytesIO')


def _load_file_str(trans_file_path: str) -> pd.DataFrame:
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
