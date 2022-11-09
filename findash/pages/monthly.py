from typing import Dict

import dash
from dash import html
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc

import pandas as pd

dash.register_page(__name__)

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


def content(title,
            pct,
            size='lg',
            color='green',
            text_weight=500):
    return dmc.Grid(
        children=[
            dmc.Col(dmc.Text(f"{title}", weight=text_weight), span=2),
            dmc.Col(dmc.Text(f"{pct}% budget used", align="center"), span=2),
            dmc.Col(dmc.Progress(value=pct, label=f"{pct}/1000", size=size,
                                 color=color), span=3),
            dmc.Col(dmc.Text(f'Remaining: 300'), span=2)
        ],
        gutter="xs",
)


def accordion_item(main_title: str,
                   main_usage: int,
                   line_parameters: Dict[str, int]):
    return dmc.AccordionItem([
        dmc.AccordionControl(content(main_title, main_usage, size='xl',
                                     color='red', text_weight=700)),
        dmc.AccordionPanel([
            content(line_title, line_pct) for line_title, line_pct in
            line_parameters.items()
        ])
    ],
        value='1'
    )


layout = dbc.Container([
    dbc.Row([
       dbc.Col([checking_card], width=2),
       dbc.Col([income_card], width=4),
       dbc.Col([expenses_card], width=4),
       dbc.Col([savings_card], width=2)]),
    html.Br(),
    dbc.Row([
        dmc.Accordion([
            accordion_item('Transportation', 25, {'Trains': 40, 'Planes': 75}),
            accordion_item("Food", 50, {"Groceries": 40, "Restaurants": 75})],
        )
    ])
], fluid=True)
