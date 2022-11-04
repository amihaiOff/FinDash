import dash
import pandas as pd
from dash import html, dash_table, dcc, Input, Output
import dash_bootstrap_components as dbc

from main import TRANS_DB
from transactions_db import TransDBSchema


def setup_trans_db():
    raw_table = TRANS_DB.db
    raw_table = raw_table.drop(columns=[TransDBSchema.ID,
                                        TransDBSchema.RECONCILED])
    raw_table[TransDBSchema.DATE] = raw_table[TransDBSchema.DATE].dt.date
    return raw_table


dash.register_page(__name__)

trans_df = setup_trans_db()
col_dtypes = TransDBSchema.get_displayed_cols_by_type()
trans_df_cols = []
for col_type, cols in col_dtypes.items():
    for col in cols:
        if col_type == 'date':
            col = {'name': f'{col}',
                   'id': f'{col}',
                   'deletable': False,
                   'renamable': False,
                   'hideable': True,
                   'type': 'datetime'}
        elif col_type == 'str':
            col = {'name': f'{col}',
                   'id': f'{col}',
                   'deletable': False,
                   'renamable': False,
                   'hideable': True,
                   'type': 'text'}
        elif col_type == 'numeric':
            col = {'name': f'{col}',
                   'id': f'{col}',
                   'deletable': False,
                   'renamable': False,
                   'hideable': True,
                   'type': 'numeric'}
        elif col_type == 'cat':
            col = {'name': f'{col}',
                   'id': f'{col}',
                   'deletable': False,
                   'renamable': False,
                   'hideable': True,
                   'presentation': 'dropdown'}
        else:
            raise ValueError(f'Unknown column type: {col_type}')

        trans_df_cols.append(col)

dropdown_options = {
    TransDBSchema.CAT:     {
        'options': [{'label': f'{cat}', 'value': f'{cat}'} for cat in trans_df[TransDBSchema.CAT].unique()]
    },
    TransDBSchema.ACCOUNT: {
        'options': [{'label': f'{account}', 'value': f'{account}'} for account in trans_df[TransDBSchema.ACCOUNT].unique()]
    }
}

trans_table = dash_table.DataTable(data=trans_df.to_dict('records'),
                                   id='trans_table',
                                   editable=True,
                                   export_format='xlsx',
                                   export_headers='display',
                                   fixed_rows={'headers': True},
                                   page_action='native',
                                   page_size=5,
                                   style_table={'height': '2000px'},
                                   columns=trans_df_cols,
                                   dropdown=dropdown_options,
                                   style_data_conditional=[
                                       {'if': {'row_index': 'odd'},
                                        'backgroundColor': 'rgb(220, 220, 220)'}
                                       ]
                                   )

category_picker = dbc.Card(
        children=[
            dbc.CardHeader('Category'),
            dcc.Dropdown(
                    id='category_picker',
                    options=trans_df[TransDBSchema.CAT].unique().tolist())
])

subcategory_picker = dbc.Card([
    dbc.CardHeader('Group'),
    dcc.Dropdown(['X', 'Y', 'Z'])
])

account_picker = dbc.Card([
    dbc.CardHeader('Account'),
    dcc.Dropdown(
            options=trans_df[TransDBSchema.ACCOUNT].unique().tolist(),
            id='account_picker')
])

date_picker = dbc.Card([
    dbc.CardHeader('Date Range'),
    dcc.DatePickerRange(
        id='date_picker',
        clearable=True,
        stay_open_on_select=False,  # doesn't work
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
       dbc.Col(children=[trans_table],
               width=9)
    ])
])


@dash.callback(
    Output('trans_table', 'data'),
    Input('category_picker', 'value'),
    Input('account_picker', 'value'),
    Input('date_picker', 'start_date'),
    Input('date_picker', 'end_date'),
    config_prevent_initial_callbacks=True
)
def update_table_by_cat(cat: str, account: str, start_date: str, end_date: str):
    def create_conditional_filter(col, val):
        return trans_df[col] == val if val is not None else True

    def create_date_cond_filter(col, start_date, end_date):
        # todo raise error when start_date > end_date
        start_date = pd.to_datetime(start_date) if start_date is not None else pd.to_datetime('1900-01-01')
        end_date = pd.to_datetime(end_date) if end_date is not None else pd.to_datetime('2100-01-01')
        return (start_date <= trans_df[col]) & (trans_df[col] <= end_date)

    cat_cond = create_conditional_filter(TransDBSchema.CAT, cat)
    account_cond = create_conditional_filter(TransDBSchema.ACCOUNT, account)
    date_cond = create_date_cond_filter(TransDBSchema.DATE, start_date, end_date)
    table = trans_df[(cat_cond) &
                     (account_cond) &
                     (date_cond)]

    return table.to_dict("records")
