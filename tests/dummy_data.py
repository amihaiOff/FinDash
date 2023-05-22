import os.path
import uuid
from typing import Optional, Dict

import pandas as pd
import numpy as np
import random
from dateutil.rrule import rrule, MONTHLY


def create_dummy_trans(num_records: int = 100,
                       start_date: str = '2022-01-01',
                       end_date: str = '2022-12-31',
                       random_seed: int = 42) -> pd.DataFrame:
    # Set the random seed for reproducibility
    random.seed(random_seed)
    np.random.seed(random_seed)

    # Define the range of dates for the dataset
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)

    # Define the list of payees, categories, and category groups
    payees = ['Supermarket', 'Restaurant', 'Gas Station', 'Clothing Store', 'Utility Bill', 'Electronics Store', 'Gym', 'Pharmacy']
    # categories = ['Groceries', 'Dining', 'Transportation', 'Shopping', 'Bills']
    category_groups = {
        'Groceries': 'Essentials',
        'Dining': 'Entertainment',
        'Transportation': 'Transportation',
        'Shopping': 'Entertainment',
        'Bills': 'Essentials'
    }

    # Define the mapping between payees and categories
    payee_category_mapping = {
        'Supermarket': 'Groceries',
        'Restaurant': 'Dining',
        'Gas Station': 'Transportation',
        'Clothing Store': 'Shopping',
        'Utility Bill': 'Bills',
        'Electronics Store': 'Shopping',
        'Gym': 'Bills',
        'Pharmacy': 'Bills'
    }

    # Define the mapping between payees and account types
    payee_account_type_mapping = {
        'Supermarket': 'Bank Account',
        'Restaurant': 'Credit Card',
        'Gas Station': 'Bank Account',
        'Clothing Store': 'Credit Card',
        'Utility Bill': 'Bank Account',
        'Electronics Store': 'Credit Card',
        'Gym': 'Bank Account',
        'Pharmacy': 'Credit Card'
    }

    # Generate random data for the dataset
    payee_trans = [random.choice(payees) for _ in range(num_records)]
    data = {
        'date': [random.choice(pd.date_range(start_date, end_date)) for _ in range(num_records)],
        'payee': [random.choice(payees) for _ in range(num_records)],
        'category': [payee_category_mapping[payee] for payee in payee_trans],
        'category_group': [category_groups[payee_category_mapping[payee]] for payee in payee_trans],
        'account': [payee_account_type_mapping[payee] for payee in payee_trans]
    }

    # Create the DataFrame
    df = pd.DataFrame(data)

    # Generate random amounts (positive and negative)
    amounts = np.random.uniform(-500, 500, num_records)
    df['amount'] = amounts
    df['inflow'] = np.where(amounts < 0, -amounts, 0)
    df['outflow'] = np.where(amounts > 0, amounts, 0)

    df['id'] = [uuid.uuid4() for _ in range(num_records)]
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
        curr_month = create_dummy_trans(num_records_per_month,
                                        start_date=f'{year}-{month}-01',
                                        end_date=f'{year}-{month}-28')
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
        year_path = f'{path}/{year}'
        if not os.path.exists(year_path):
            os.mkdir(year_path)

        trans.to_parquet(f'{year_path}/{month}.pq')


if __name__ == '__main__':
    d = create_dummy_trans()
    print(d.head())
