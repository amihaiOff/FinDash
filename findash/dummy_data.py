from typing import Any, List, Tuple
from datetime import timedelta

import pandas as pd
import numpy as np


def get_dummy_values():
    """
    id - running numbers 1...
    date - running dates from 2022-01-01
    :return:
    """
    account = ['fibi', 'cash', 'cal', 'oz']
    category = {'food': ['wolt', 'groceries', 'junk'],
                  'transportations': ['fuel', 'insurance'],
                  'bills': ['water', 'gas', 'arnona']}
    budget = [100, 3000, 500, 800]
    amount = [10, 30, 50, 100, 130, 150, 200]
    payee = [f'dude-{x}' for x in range(1, 7)]
    memo = ['']
    reconciled = [False]

    return {
        'payee': payee,
        'account': account,
        'budget': budget,
        'amount': amount,
        'memo': memo,
        'reconciled': reconciled,
        'cat_name': category
    }


class TransGenerator:
    def __init__(self, num_samples, seed=42):
        self._num_samples = num_samples
        self._seed = seed
        self._start_date = pd.to_datetime('2022-10-01')
        np.random.seed(seed)

    def generate(self):
        dummy_vals = get_dummy_values()
        uuids = np.arange(1, self._num_samples + 1)
        payees = self._generate_col(dummy_vals['payee'])
        accounts = self._generate_col(dummy_vals['account'])
        memos = self._generate_col(dummy_vals['memo'])
        reconciled = self._generate_col(dummy_vals['reconciled'])
        amount = self._generate_col(dummy_vals['amount'])
        inflow, outflow = self._generate_inflow_outflow(amount, accounts)
        dates = self._generate_dates()
        categories, groups = self._generate_categories_and_groups()

        return pd.DataFrame({
            'id': uuids,
            'payee': payees,
            'account': accounts,
            'memo': memos,
            'reconciled': reconciled,
            'amount': amount,
            'inflow': inflow,
            'outflow': outflow,
            'date': dates,
            'cat': categories,
            'cat_group': groups
            })

    def _generate_inflow_outflow(self,
                                 amount_col: np.array,
                                 account_col: np.array) -> Tuple[np.array,
                                                                 np.array]:
        inflow = np.zeros(amount_col.shape)
        outflow = np.zeros(amount_col.shape)
        inflow[account_col == 'fibi'] = amount_col[account_col == 'fibi']
        outflow[account_col != 'fibi'] = amount_col[account_col != 'fibi']

        return inflow, outflow

    def _generate_col(self, values: List[Any]):
        return np.random.choice(values, self._num_samples)

    def _generate_dates(self):
        start_date = self._start_date
        return [start_date + timedelta(days=x) for x in range(
                self._num_samples)]

    def _generate_categories_and_groups(self):
        dummy_cats = get_dummy_values()['category']
        dummy_groups = list(dummy_cats.keys())
        categories = []
        groups = []
        for _ in range(self._num_samples):
            group = np.random.choice(dummy_groups, 1)[0]
            cat = np.random.choice(dummy_cats[group], 1)[0]
            categories.append(cat)
            groups.append(group)
        return categories, groups


def generate_catdb():
    dummy_vals = get_dummy_values()
    categories = []
    groups = []
    budgets = []
    for group, cats in dummy_vals['cat_name'].items():
        for cat in cats:
            categories.append(cat)
            groups.append(group)
            budgets.append(np.random.choice(dummy_vals['budget'], 1)[0])
    return pd.DataFrame({
        'cat_name': categories,
        'cat_group': groups,
        'in_constant': False,
        'budget': budgets
    })


if __name__ == '__main__':
    gen = TransGenerator(10)
    print(gen.generate()[['outflow','account', 'amount', 'inflow']])
    # print(generate_catdb())
