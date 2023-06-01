import json
import os
from typing import Optional

import pandas as pd
import yaml

from tests.create_dummy_data.dummy_cat_and_accounts_db import \
    create_dummy_cat_db, create_accounts_dict, create_cat2payee, \
    create_payee2cat

from tests.create_dummy_data.dummy_trans_db import create_dummy_db


def _create_dirs(path: str) -> None:
    if not os.path.exists(f'{path}/cat_db'):
        os.makedirs(f'{path}/cat_db')

    if not os.path.exists(f'{path}/trans_db'):
        os.makedirs(f'{path}/trans_db')


def create_all_dummy_data(
        save_path: str,
        start_date: str,
        end_date: str,
        num_records: Optional[int] = 10,
        random_seed: Optional[int] = 42,
) -> None:
    create_dummy_db(start_date, end_date, num_records, save_path,
                    random_seed=random_seed)

    dummy_cat_db: pd.DataFrame = create_dummy_cat_db(random_seed=random_seed)
    payee2cat: dict = create_payee2cat()
    cat2payee: dict = create_cat2payee()
    accounts_dict: dict = create_accounts_dict()

    _create_dirs(save_path)
    dummy_cat_db.to_parquet(f'{save_path}/cat_db/cat_db.pq')
    json.dump(payee2cat, open(f'{save_path}/cat_db/payee2cat.json', 'w'),
              indent=4)
    json.dump(cat2payee, open(f'{save_path}/cat_db/cat2payee.json', 'w'),
              indent=4)
    yaml.dump(accounts_dict, open(f'{save_path}/accounts.yaml', 'w'))


if __name__ == '__main__':
    create_all_dummy_data('/Users/amihaio/Documents/personal/FinDash/dbs/dev',
                          start_date='2020-01-01',
                          end_date='2020-03-31',
                          num_records=10
                          )
