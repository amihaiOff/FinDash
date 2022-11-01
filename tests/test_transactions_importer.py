import csv
import tempfile
from io import StringIO

import pandas as pd

from db import TransactionsDBSchema
from transactions_importer import import_file
from accounts import Account, ColMapping, InflowSign, Institution
from unittest.mock import patch


class TestAccount(Account):
    def get_col_mapping(self) -> ColMapping:
        col_mapping = {
            'date': TransactionsDBSchema.DATE,
            'נמען': TransactionsDBSchema.PAYEE,
            'סכום': TransactionsDBSchema.AMOUNT
        }
        return ColMapping(col_mapping)

    @property
    def inflow_sign(self) -> InflowSign:
        return InflowSign.MINUS


def get_trans_file():
    return [['date', 'נמען', 'סכום'],
            ['2022-01-02', 'מכולת', '200'],
            ['2022-01-03', 'יהושע', '-30'],
            ['2022-01-02', 'amazon', '4']]


def get_csv_file_like():
    fake_csv = StringIO()
    fake_writer = csv.writer(fake_csv)
    fake_writer.writerows(get_trans_file())
    fake_csv.seek(0)
    return pd.read_csv(fake_csv)
    # return fake_csv


def get_account():
    return TestAccount(name='test', institution=Institution.FIBI)


def gt_trans_file():
    return pd.DataFrame([['2022-01-02', 'מכולת', 200, '', '', 'test', 0, 200, False],
                         ['2022-01-03', 'יהושע', -30, '', '', 'test', 30, 0, False],
                         ['2022-01-02', 'amazon', 4, '', '', 'test', 0, 4, False]],
                        columns=['date', 'payee', 'amount', 'sub_cat', 'memo', 'account',
                                 'inflow', 'outflow', 'reconciled'])


@patch('pandas.read_csv', return_value=get_csv_file_like())
def test_importer(mock_csv):
    df = import_file(trans_file_path='test.csv', account=get_account())
    pd.testing.assert_frame_equal(df, gt_trans_file())

