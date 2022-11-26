from typing import Dict, Tuple, List, Optional
from datetime import datetime

import dash
import numpy as np
from dash import html
import dash_bootstrap_components as dbc
from dash import dcc
import dash_mantine_components as dmc

import pandas as pd

from main import CAT_DB, TRANS_DB
from categories_db import CatDBSchema
from transactions_db import TransDBSchema
from accounts import CHECKING_ACCOUNTS, NON_CHECKING_ACCOUNTS
from utils import SHEKEL_SYM, conditional_coloring

dash.register_page(__name__)


CURR_TRANS_DB = TRANS_DB.get_current_month_trans()


def _calculate_outflow_total(last: bool = False) -> float:
    db = TRANS_DB if not last else CURR_TRANS_DB
    return db[TransDBSchema.OUTFLOW].sum()


def _calculate_checking_total(last: bool = False) -> float:
    """
    sum of all inflow from checking accounts (reimbursements from credit don't
    count)
    :param last: if True, sum only this month's inflow
    """
    checking_accounts = [acc.institution.value for acc in CHECKING_ACCOUNTS]
    db = TRANS_DB if not last else CURR_TRANS_DB
    return db[db[TransDBSchema.ACCOUNT].isin(checking_accounts)][
            TransDBSchema.INFLOW].sum()


def _curr_expenses_from_budget_pct() -> Optional[float]:
    """ divide current month's expenses by current month's budget """
    current_budget = CAT_DB.get_total_budget()
    if current_budget == 0:
        return None
    else:
        return _calculate_outflow_total(last=True) * 100 / current_budget


def _curr_expenses_from_income_pct() -> Optional[float]:
    """ divide current month's expenses by current month's income """
    current_income = _calculate_checking_total(last=True)
    if current_income == 0:
        return None
    current_expenses = CURR_TRANS_DB[TransDBSchema.OUTFLOW].sum()
    return current_expenses * 100 / current_income


def _pct_budget_used():
    curr_expenses = _calculate_checking_total(last=True)
    curr_budget = CAT_DB.get_budget()
    return curr_expenses * 100 / curr_budget


def _get_balance_per_account_for_popup():
    per_account = CURR_TRANS_DB.groupby(TransDBSchema.ACCOUNT)[
        TransDBSchema.INFLOW].sum()
    checking_str = [acc.institution.value for acc in CHECKING_ACCOUNTS]
    checking_only = per_account[per_account.index.isin(checking_str)]
    string_rep = ''
    for account, acc_sum in checking_only.items():
        string_rep += f'**{account}**: {acc_sum}\n'
    return string_rep[:-1]


def _get_income_per_account_popup():
    per_account = CURR_TRANS_DB.groupby(TransDBSchema.ACCOUNT)[
        TransDBSchema.OUTFLOW].sum()
    non_checking_str = [acc.institution.value for acc in NON_CHECKING_ACCOUNTS]
    non_checking_only = per_account[per_account.index.isin(non_checking_str)]
    string_rep = ''
    for account, acc_sum in non_checking_only.items():
        string_rep += f'**{account}**: {acc_sum}\n'
    return string_rep[:-1]


def _create_banner_card(title: str,
                        value: float,
                        subtitle: str,
                        color: str,
                        id: str) -> dbc.Card:
    return dbc.Card([
        dbc.CardHeader(title),
        html.H2(f"{value}{SHEKEL_SYM}"),
        html.P(subtitle, style={'color': color})],
        body=True,
        id=id,
        outline=True,
        color='light'
    )


def _create_checking_card():
    checking_total = _calculate_checking_total()

    checking_card = dbc.Card([
                    dbc.CardHeader('Checking'),
                    html.H2(f"{checking_total:.0f}{SHEKEL_SYM}"),
                    html.P(f"+12% MoM(?)", style={'color': 'green'})], # todo - think of what the subtitle needs to be
                    body=True,
                    id='checking-card',
                    color='light',
                    outline=True
    )

    checking_popover = dbc.Popover([
        dbc.PopoverHeader('Breakdown'),
        dbc.PopoverBody([
            dcc.Markdown(_get_balance_per_account_for_popup(),
                         style={'white-space': 'pre'})
        ])],
        target='checking-card',
        trigger='hover',
        placement='bottom'

    )

    return checking_card, checking_popover


def _create_income_card() -> Tuple[dbc.Card, dbc.Popover]:
    income = _calculate_checking_total(last=True)
    if income == 0:
        subtitle = 'No income this month'
        color = 'red'
    else:
        curr_expenses_pct = _curr_expenses_from_income_pct()
        subtitle = f"{curr_expenses_pct:.0f}% income used"
        color = conditional_coloring(curr_expenses_pct, {'green': (0, np.inf),
                                                         'red': (-np.inf, 0)})
    card = _create_banner_card(title='Last Income',
                               value=income,
                               subtitle=subtitle,
                               color=color,
                               id='income-card')

    income_popover = dbc.Popover([
        dbc.PopoverHeader('Breakdown'),
        dbc.PopoverBody([
            dcc.Markdown(_get_income_per_account_popup(),
                         style={'white-space': 'pre'})
        ])],
        target='income-card',
        trigger='hover',
        placement='bottom'
    )
    return card, income_popover


def _create_expenses_card():
    expenses = _calculate_outflow_total(True)
    curr_expenses_pct = _curr_expenses_from_budget_pct()
    if curr_expenses_pct is None:
        color = 'red'
        subtitle = 'No budget this month'
    else:
        color = conditional_coloring(curr_expenses_pct, {
            'green': (0, np.inf),
            'red': (-np.inf, 0)
        })
        subtitle = f"{curr_expenses_pct:.0f}% budget used"

    return _create_banner_card(title="Expenses",
                               value=expenses,
                               subtitle=subtitle,
                               color=color,
                               id='expenses-card'
                               )


def _create_savings_card():
    return _create_banner_card(title='Savings',
                               value=2000,
                               subtitle=f'Previous month 1000',
                               color='green',
                               id='savings-card'
                               )


def _create_notif_card():
    return dbc.Card([
        html.H2('Notifications')
    ])


"""
Categories
"""
LOW_USAGE_THR = 85
HIGH_USAGE_THR = 100


def cat_content(title: str,
                usage: float,
                cat_budget: float,
                size: str = 'lg',
                text_weight=500):
    """
    create content for category progress line
    :param title:
    :param usage:
    :param cat_budget:
    :param size:
    :param text_weight:
    :return:
    """
    usage_pct = int(usage*100/cat_budget)
    color = conditional_coloring(usage_pct, {
        'green': (-np.inf, LOW_USAGE_THR),
        'yellow': (LOW_USAGE_THR, HIGH_USAGE_THR),
        'red': (HIGH_USAGE_THR, np.inf)
    })
    progress_val = min(100, usage_pct)
    return dmc.Grid(
        children=[
            dmc.Col(dmc.Text(f"{title}", weight=text_weight), span=2),
            dmc.Col(dmc.Text(f"{usage_pct}% budget used", align="center"),
                    span=2),
            dmc.Col(dmc.Progress(value=progress_val, label=f"{usage}/{cat_budget}",
                                 size=size, color=color), span=5),
            dmc.Col(dmc.Text(f'Remaining: {cat_budget-usage}'), span=2)
        ],
        gutter="xs",
)


def accordion_item(group_title: str,
                   group_usage: int,
                   group_budget: float,
                   cat_stats: Dict[str, Tuple[float, float]]):
    """
    :param cat_stats: dictionary of cat_name: (usage, budget)
    :return:
    """
    return dmc.AccordionItem([
        dmc.AccordionControl(cat_content(group_title, group_usage, group_budget,
                                         size='xl', text_weight=700)),
        dmc.AccordionPanel([
            cat_content(title, usage, budget) for title, (usage, budget) in
            cat_stats.items()
        ])
    ],
        value=str(np.random.randint(1000))
    )


def create_cat_usage(group: pd.core.groupby.generic.DataFrameGroupBy):
    cat_dict = {}
    for ind, (cat_name, _, _, budget) in group.iterrows():
        usage = CURR_TRANS_DB[
                        CURR_TRANS_DB[TransDBSchema.CAT] == cat_name][
                                                    TransDBSchema.AMOUNT].sum()
        cat_dict[cat_name] = (usage, budget)
    return cat_dict


def create_accordion_items():
    accordion_items = []
    for group_name, group in CAT_DB.get_groups():
        group_budget = group[CatDBSchema.BUDGET].sum()
        group_usage = CURR_TRANS_DB.get_data_by_group(group_name)[
            TransDBSchema.AMOUNT].sum()

        categories = create_cat_usage(group)
        accordion_items.append(accordion_item(group_name, group_usage,
                                              group_budget, categories))

    return accordion_items


layout = dbc.Container([
    dbc.Row([
       dbc.Col(_create_checking_card(), width=2),
       dbc.Col(_create_income_card(), width=2),
       dbc.Col(_create_expenses_card(), width=2),
       dbc.Col(_create_savings_card(), width=2),
       dbc.Col(_create_notif_card(), width=4)]),
    html.Br(),
    dbc.Row([
        dmc.AccordionMultiple(
            children=create_accordion_items())
    ])
], fluid=True)
