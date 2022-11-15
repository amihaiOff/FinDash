from typing import Dict, Tuple
from datetime import datetime

import dash
from dash import html
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc

import pandas as pd

from main import CAT_DB, TRANS_DB
from categories_db import CatDBSchema
from transactions_db import TransDBSchema
from accounts import CHECKING_ACCOUNTS
from utils import SHEKEL_SYM

dash.register_page(__name__)


CURR_TRANS_DB = TRANS_DB.get_current_month_trans()


def _calculate_checking_total(last=False):
    """
    sum of all inflow
    :param last: if True, sum only This month's inflow
    """
    checking_accounts = [acc.institution.value for acc in CHECKING_ACCOUNTS]
    db = TRANS_DB if not last else CURR_TRANS_DB
    return db[db[TransDBSchema.ACCOUNT].isin(checking_accounts)][
            TransDBSchema.INFLOW].sum()


def _curr_expenses_pct():
    """ divide current month's expenses by current month's income """
    current_income = _calculate_checking_total(last=True)
    current_expenses = CURR_TRANS_DB[TransDBSchema.OUTFLOW].sum()
    return current_expenses * 100 / current_income


def _pct_budget_used():
    curr_expenses = _calculate_checking_total(last=True)
    curr_budget = CAT_DB.get_budget()
    return curr_expenses * 100 / curr_budget
# def _checking_m_over_m():
#     curr_income = CURR_TRANS_DB[TransDBSchema.INFLOW].sum()
#     prev_month = datetime.date().strftime()
#     prev_income = TRANS_DB[TRANS_DB[TransDBSchema.DATE] == prev_month][
#         TransDBSchema.INFLOW.su

checking_card = dbc.Card([
                dbc.CardHeader('Checking'),
                html.H2(f"{_calculate_checking_total():.2f}{SHEKEL_SYM}"),
                html.P(f"+12% MoM(?)", style={'color': 'green'})],
                body=True)

income_card = dbc.Card([
                    dbc.CardHeader("Last Income"),
                    html.H2(f"{_calculate_checking_total(last=True):.2f}{SHEKEL_SYM}"),
                    html.P(f"{_curr_expenses_pct():.0f}% income used",
                           style={'color': 'green'}),
                ],
                    color='light',
                    body=True)

expenses_card = dbc.Card([
                    dbc.CardHeader("Expenses"),
                    html.H2(f'{_calculate_checking_total(True)}{SHEKEL_SYM}'),
                    html.P(f"{_curr_expenses_pct():.0f}% income used"),
                ],
                    color="light",
                    body=True)


savings_card = dbc.Card([
                dbc.CardHeader("Savings"),
                html.H2(f"2000{SHEKEL_SYM}")],
                body=True,
                outline=True,
                )


"""
Categories
"""
LOW_USAGE_THR = 85
HIGH_USAGE_THR = 100


def conditional_coloring(usage_pct: float):
    if usage_pct < LOW_USAGE_THR:
        return 'green'
    elif LOW_USAGE_THR <= usage_pct < HIGH_USAGE_THR:
        return 'yellow'
    else:
        return 'red'


def cat_content(title: str,
                usage: float,
                cat_budget: float,
                size: str = 'lg',
                text_weight=500):
    usage_pct = int(usage*100/cat_budget)
    color = conditional_coloring(usage_pct)
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
        value='1'
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
       dbc.Col([checking_card], width=2),
       dbc.Col([income_card], width=2),
       dbc.Col([expenses_card], width=2),
       dbc.Col([savings_card], width=2)]),
    html.Br(),
    dbc.Row([
        dmc.Accordion(create_accordion_items())
    ])
], fluid=True)
