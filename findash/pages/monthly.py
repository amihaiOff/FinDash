import dash
from dash import html
import dash_bootstrap_components as dbc
import pandas as pd

dash.register_page(__name__)

dummy_table = pd.DataFrame([['2022-01-01', 'מכולת', 0, 200],
                            ['2022-01-01', 'ספר', 0, 20]],
                           columns=['Date', 'Payee', 'Inflow', 'Outflow'])

income_card = dbc.Card([
                html.H4("Income"),
                html.H2(f"{dummy_table.Outflow.sum()}")],
                body=True,
                color="red")

expense_card = dbc.Card([
                html.H4("Expense"),
                html.H2(f"{dummy_table.Inflow.sum()}")],
                body=True,
                color="light")

savings_card = dbc.Card([
                html.H4("Savings"),
                html.H2(f"{dummy_table.Inflow.sum()}")],
                body=True,
                color="blue",
                outline=True,
                inverse=True
                )


layout = dbc.Container([
    dbc.Row([
       dbc.Col([html.Div(income_card)], width=3),
       dbc.Col([expense_card], width=6),
       dbc.Col([savings_card], width=3)]),
    html.Br(),
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader('Fuel'),
                dbc.CardBody([dbc.Progress(value='100', label='100/1000', max=1000, color='green')])
            ])
        ], width=6)
    ]),

    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader('Groceries'),
                dbc.CardBody([dbc.Progress(value='1500', label='1500/2000', max=2000, color='warning')])
            ])
        ], width=6)
    ]),

    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader('Clothes'),
                dbc.CardBody([dbc.Progress(value='1000', label='1000/1000', max=1000, color='danger')])
            ])
        ], width=6)
    ]),

    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader('Wolt'),
                dbc.CardBody([dbc.Progress(value='1500', label='1500/1000', max=1000, color='dark')])
            ])
        ], width=6)
    ])
], fluid=True)
