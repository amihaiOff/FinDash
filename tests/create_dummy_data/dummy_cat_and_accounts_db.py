import numpy as np
import pandas as pd

from tests.create_dummy_data.names import categories, category_groups_mapping,\
    accounts, payee_category_mapping


def create_dummy_cat_db(random_seed: int = 42):
    """
    creates a dummy database for categories taken from names.py file.
    Each category belongs to a category group and has a budget.
    with the following columns:
    1. cat_group (str)
    2. cat_name (str)
    3. budget (int)
    is_constant (bool)
    """
    np.random.seed(random_seed)
    rows = []
    is_constant = False
    for cat in categories:
        budget = np.random.randint(100, 1000)
        cat_group = category_groups_mapping[cat]
        rows.append([cat_group, cat, budget, is_constant])

    return pd.DataFrame(
        rows, columns=['cat_group', 'cat_name', 'budget', 'is_constant']
    )


def create_payee2cat():
    return payee_category_mapping


def create_cat2payee():
    return {v: k for k, v in payee_category_mapping.items()}


def create_accounts_dict():
    """
    each accoutn has a name and an institution.
    :return:
    """
    accounts_dict = {}
    for account in accounts:
        accounts_dict[account] = {'institution': 'cal'}

    return accounts_dict
