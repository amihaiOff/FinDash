import os.path
from pathlib import Path
import uuid
from typing import Optional, Dict

import pandas as pd
import numpy as np
import random
from dateutil.rrule import rrule, MONTHLY

from tests.create_dummy_data.names import payees, \
    category_groups_mapping, payee_category_mapping, payee_account_type_mapping


def create_dummy_trans_table(num_records: int = 100,
                             start_date: str = '2022-01-01',
                             end_date: str = '2022-12-31',
                             random_seed: int = 42) -> pd.DataFrame:
    # Set the random seed for reproducibility
    random.seed(random_seed)
    np.random.seed(random_seed)

    # Define the range of dates for the dataset
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)

    # Generate random data for the dataset
    payee_trans = [random.choice(payees) for _ in range(num_records)]
    data = {
        'date': [random.choice(pd.date_range(start_date, end_date)) for _ in
                 range(num_records)],
        'payee': [random.choice(payees) for _ in range(num_records)],
        'cat': [payee_category_mapping[payee] for payee in payee_trans],
        'cat_group': [category_groups_mapping[payee_category_mapping[payee]] for
                           payee
                           in payee_trans],
        'account': [payee_account_type_mapping[payee] for payee in payee_trans]
    }

    # Create the DataFrame
    df = pd.DataFrame(data)

    # Generate random amounts (positive and negative)
    amounts = np.random.randint(-500, 500, num_records)
    df['amount'] = amounts
    df['inflow'] = np.where(amounts < 0, -amounts, 0)
    df['outflow'] = np.where(amounts > 0, amounts, 0)

    df['id'] = [str(uuid.uuid4()) for _ in range(num_records)]
    df['memo'] = ['' for _ in range(num_records)]
    df['reconciled'] = [False for _ in range(num_records)]
    df['split'] = ['' for _ in range(num_records)]

    return df


def create_dummy_db(
        start_date: str,
        end_date: str,
        num_records_per_month: int = 10,
        save_path: Optional[str] = None,
        random_seed: int = 42):
    """
    create dummy data in the format for use in the app.
    This means files separated by month.
    """
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)
    transactions = {}
    for dt in rrule(MONTHLY, dtstart=start_date, until=end_date):
        year = dt.year
        month = dt.month
        curr_month = create_dummy_trans_table(num_records_per_month,
                                              start_date=f'{year}-{month}-01',
                                              end_date=f'{year}-{month}-28',
                                              random_seed=random_seed)
        transactions[f'{year}-{month}'] = curr_month

    if save_path:
        save_dummy_db(transactions, save_path)

    return transactions


def save_dummy_db(db: Dict[str, pd.DataFrame],
                  path: str):
    """
    save dummy data in the format for use in the app.
    :param db: assumes a dict with keys in format YYYY-MM and
        values as pd.DataFrame
    :param path:
    :return:
    """
    for date, trans in db.items():
        year, month = date.split('-')
        year_path = Path(f'{path}/trans_db/{year}')
        
        os.makedirs(year_path, exist_ok=True)

        trans.to_parquet(f'{year_path}/{month}.pq')


if __name__ == '__main__':
    d = create_dummy_trans_table()
    print(d.head())
