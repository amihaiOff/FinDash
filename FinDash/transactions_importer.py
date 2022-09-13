from logging import getLogger

import pandas as pd

from accounts import Account, InflowSign
from transactions_db import TransactionsColNames

logger = getLogger()

def import_file(self, trans_file_path: str, account: Account) -> pd.DataFrame:
    trans_file = self.load_file(trans_file_path)
    trans_file = self._apply_col_mapping(trans_file, account)
    return trans_file


def _apply_col_mapping(trans_file: pd.DataFrame, account: Account):
    """
    change column names according to mapping from account object
    :param trans_file:
    :param account:
    :return:
    """
    for source_col, dest_col in account.get_col_mapping():
        if source_col in trans_file.columns:
            trans_file = trans_file.rename(columns={source_col: dest_col})
        else:
            logger.warning(f'col {source_col} not found in transactions file')

    # todo think of way of enforcing mandatory cols - then this isn't needed
    # validate col mapping
    cols_not_found = [col for col in TransactionsColNames.get_mandatory_cols()
                      if col not in trans_file.columns]
    if len(cols_not_found) > 0:
        logger.exception('Not all mandatory cols are in ')
    return trans_file


def fit_to_db_scheme(trans_file: pd.DataFrame, account: Account):
    for col_name, default_val in TransactionsColNames.get_db_col_names():
        if col_name not in trans_file.columns:
            trans_file[col_name] = default_val

    # convert amount col into inflow and outflow
    inflow_col = TransactionsColNames.INFLOW
    amount_col = TransactionsColNames.AMOUNT
    cond = trans_file[amount_col] < 0 if account.inflow_sign == InflowSign.MINUS else \
        trans_file[amount_col] > 0
    trans_file[inflow_col][cond] = trans_file[amount_col]


def load_file(trans_file_path: str) -> pd.DataFrame:
    if trans_file_path.endswith('csv'):
        return pd.read_csv(trans_file_path)
    elif trans_file_path.endswith('xls') or trans_file_path.endswith('xlsx'):
        return pd.read_excel(trans_file_path)
    elif trans_file_path.endswith('parquet'):
        return pd.read_parquet(trans_file_path)
    else:
        raise ValueError(f'Transaction file {trans_file_path} not supported.')


def validate_trans_file(self):
    pass
