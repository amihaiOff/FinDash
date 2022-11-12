from typing import Dict
from datetime import datetime

import dash
from dash import html
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc

import pandas as pd

from main import CAT_DB, TRANS_DB
from categories_db import CatDBSchema
from transactions_db import TransDBSchema

dash.register_page(__name__)


def create_current_month_trans_db() -> pd.DataFrame:
    """
    create a transactions database for the current month
    :return:
    """
    current_month = datetime.now().strftime('%Y-%m')
    return TRANS_DB[TRANS_DB[TransDBSchema.DATE].dt.strftime('%Y-%m') ==
                    current_month]


CURR_TRANS_DB = create_current_month_trans_db()


dummy_table = pd.DataFrame([['2022-01-01', 'מכולת', 0, 200],
                            ['2022-01-01', 'ספר', 0, 20]],
                           columns=['Date', 'Payee', 'Inflow', 'Outflow'])

checking_card = dbc.Card([
                dbc.CardHeader('Checking'),
                html.H2(f"{dummy_table.Outflow.sum()}")],
                body=True)

income_card = dbc.CardGroup([
                dbc.Card([
                    dbc.CardHeader("Income"),
                    html.H2(f"{dummy_table.Inflow.sum()}")
                ],
                    color='light',
                    body=True
                ),
                dbc.Card([
                    dbc.CardHeader("Income usage"),
                    html.H2('90%')
                ],
                    color="light",
                    body=True
                )
])

expenses_card = dbc.CardGroup([
                    dbc.Card([
                        dbc.CardHeader("Expenses"),
                        html.H2(f"{dummy_table.Inflow.sum()}")
                    ],
                        color='light',
                        body=True
                    ),
                    dbc.Card([
                        dbc.CardHeader("Expenses usage"),
                        html.H2('90%')
                    ],
                        color="light",
                        body=True
                    )
])

savings_card = dbc.Card([
                dbc.CardHeader("Savings"),
                html.H2(f"{dummy_table.Inflow.sum()}")],
                body=True,
                outline=True,
                )

"""
Categories
"""


def cat_content(title: str,
                usage: float,
                cat_budget: float,
                size: str = 'lg',
                color: str = 'green',
                text_weight=500):
    return dmc.Grid(
        children=[
            dmc.Col(dmc.Text(f"{title}", weight=text_weight), span=2),
            dmc.Col(dmc.Text(f"{int(usage*100/cat_budget)}% budget used",
                             align="center"), span=2),
            dmc.Col(dmc.Progress(value=usage, label=f"{usage}/{cat_budget}",
                                 size=size, color=color), span=3),
            dmc.Col(dmc.Text(f'Remaining: {cat_budget-usage}'), span=2)
        ],
        gutter="xs",
)


def accordion_item(main_title: str,
                   main_usage: int,
                   main_budget: float,
                   cat_stats: Dict[str, int]):
    return dmc.AccordionItem([
        dmc.AccordionControl(cat_content(main_title, main_usage, main_budget,
                                         size='xl', color='red',
                                         text_weight=700)),
        dmc.AccordionPanel([
            cat_content(title, usage, budget) for title, (usage, budget) in
            cat_stats.items()
        ])
    ],
        value='1'
    )


def create_accordion_items():
    accordion_items = []
    for group_name, group in CAT_DB.get_groups():
        group_budget = group[CatDBSchema.BUDGET].sum()
        group_usage = CURR_TRANS_DB.get_data_by_group(group_name)[
            TransDBSchema.AMOUNT].sum()

        cat_stats = {}

        # todo - sum trans over each cat and divide by cat budget
        categories = dict(zip(group.loc[:, CatDBSchema.CAT_NAME],
                              group.loc[:, CatDBSchema.BUDGET]))
        accordion_items.append(accordion_item(group_name, group_usage,
                                              group_budget, categories))

    return accordion_items


layout = dbc.Container([
    dbc.Row([
       dbc.Col([checking_card], width=2),
       dbc.Col([income_card], width=4),
       dbc.Col([expenses_card], width=4),
       dbc.Col([savings_card], width=2)]),
    html.Br(),
    dbc.Row([
        dmc.Accordion(create_accordion_items(),
        )
    ])
], fluid=True)
