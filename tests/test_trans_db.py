import tempfile

import pandas as pd

from findash.transactions_db import TransactionsDBParquet


def input_trans_df():
    return pd.DataFrame({'id': ['1', '2', '3'],
                         'date': ['2021-01-01', '2021-01-02', '2021-01-03'],
                         'payee': ['a', 'b', 'c'],
                         'category': ['cat1', 'cat2', 'cat2'],
                         'account': ['acc1', 'acc1', 'acc2'],
                         'amount': [100, 200, 300],
                         'inflow': [0, 0, 300],
                         'outflow': [100, 200, 0],
                         'reconciled': [True, False, True],
                         'memo': ['j', 'k', 'l']})

def trans_df_from_path():
    """
    create temporary file trans_df to it and return it
    :return:
    """
    df = input_trans_df()
    with tempfile.NamedTemporaryFile(suffix='.parquet') as f:
        df.to_parquet(f.name)
        return f.name


def additional_trans_df():
    return pd.DataFrame({'id': ['4', '5', '6'],
                         'date': ['2021-01-04', '2021-01-05', '2021-01-06'],
                         'payee': ['d', 'e', 'f'],
                         'category': ['cat1', 'cat2', 'cat3'],
                         'account': ['acc3', 'acc3', 'acc2'],
                         'amount': [400, 500, 600],
                         'inflow': [0, 0, 600],
                         'outflow': [400, 500, 0],
                         'reconciled': [False, False, False],
                         'memo': ['m', 'n', 'o']})


def test_connect():
    db_path = trans_df_from_path()
    db = TransactionsDBParquet()
    assert db.connect(db_path) is not None


def test_save_db():
    db = TransactionsDBParquet()
    assert db.save_db() is None


def test_insert_data():
    db = TransactionsDBParquet()
    db._db = input_trans_df()
    new_df = additional_trans_df()
    assert db.insert_data(new_df) is None


def test_get_data():
    db = TransactionsDBParquet()
