import dash
from dash import html, dash_table, dcc
import dash_bootstrap_components as dbc
import pandas as pd

dash.register_page(__name__)

df = pd.DataFrame([['2022-01-01', 'מכולת', 200, 0, 200, 'weekend shopping', 'Food', 'Groceries', 'Credit'],
                            ['2022-01-01', 'ספר', 20, 0, 20, '', 'Personal', 'Grooming', 'Credit']],
                           columns=['Date', 'Payee', 'Amount', 'Inflow', 'Outflow', 'Memo',
                                    'Category', 'Subcategory', 'Account'])

trans_table = dash_table.DataTable(df.to_dict('records'),
                                   style_data_conditional=[
                                       {
                                           'if':              {'row_index': 'odd'},
                                           'backgroundColor': 'rgb(220, 220, 220)',
                                       }
                                       ]
                                   )
category_picker = dbc.Card([
    dbc.CardHeader('Category'),
    dcc.Dropdown(['Fuel', 'Wolt', 'Clothes'])
])

subcategory_picker = dbc.Card([
    dbc.CardHeader('Sub Category'),
    dcc.Dropdown(['X', 'Y', 'Z'])
])

account_picker = dbc.Card([
    dbc.CardHeader('Account'),
    dcc.Dropdown(['הבינלאומי', 'Credit1', 'Cash'])
])

date_picker = dbc.Card([
    dbc.CardHeader('Date Range'),
    dcc.DatePickerRange(
        start_date_placeholder_text='Pick a date',
        end_date_placeholder_text='Pick a date'
    )
])


layout = dbc.Container([
    dbc.Row([
       dbc.Col([
           category_picker,
           html.Br(),
           subcategory_picker,
           html.Br(),
           account_picker,
           html.Br(),
           date_picker
       ], width=3),
       dbc.Col([
            trans_table,
       ], width=9)
    ])
])

