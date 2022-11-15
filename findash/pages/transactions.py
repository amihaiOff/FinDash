import dash
import pandas as pd
from dash import State, html, dash_table, dcc, Input, Output
import dash_bootstrap_components as dbc

from main import TRANS_DB
from transactions_db import TransDBSchema
from element_ids import TransIDs


def setup_table_cols():
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
    return trans_df_cols


def setup_table_cell_dropdowns():
    dropdown_options = {
        TransDBSchema.CAT: {
            'options': [{'label': f'{cat}', 'value': f'{cat}'} for cat in
                        TRANS_DB[TransDBSchema.CAT].unique()]
        },
        TransDBSchema.ACCOUNT: {
            'options': [{'label': f'{account}', 'value': f'{account}'} for
                        account in TRANS_DB[TransDBSchema.ACCOUNT].unique()]
        }
    }
    return dropdown_options


dash.register_page(__name__)
trans_table = dash_table.DataTable(data=TRANS_DB.to_dict('records'),
                                   id=TransIDs.TRANS_TBL,
                                   editable=True,
                                   export_format='xlsx',
                                   export_headers='display',
                                   # fixed_rows={'headers': True},
                                   page_action='native',
                                   page_size=50,
                                   row_deletable=True,
                                   style_table={'height': '2000px'},
                                   columns=setup_table_cols(),
                                   dropdown=setup_table_cell_dropdowns(),
                                   style_data_conditional=[
                                       {'if': {'row_index': 'odd'},
                                        'backgroundColor': 'rgb(220, 220, 220)'}
                                   ]
                                   )

category_picker = dbc.Card(
    children=[
        dbc.CardHeader('Category'),
        dcc.Dropdown(
            id=TransIDs.CAT_PICKER,
            options=TRANS_DB[TransDBSchema.CAT].unique().tolist())
    ])

subcategory_picker = dbc.Card([
    dbc.CardHeader('Group'),
    dcc.Dropdown(['X', 'Y', 'Z'])
])

account_picker = dbc.Card([
    dbc.CardHeader('Account'),
    dcc.Dropdown(
        options=TRANS_DB[TransDBSchema.ACCOUNT].unique().tolist(),
        id=TransIDs.ACC_PICKER)
])

date_picker = dbc.Card([
    dbc.CardHeader('Date Range'),
    dcc.DatePickerRange(
        id=TransIDs.DATE_PICKER,
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
            date_picker,
            html.Br(),
            dbc.Button('Add row',
                       id=TransIDs.ADD_ROW_BTN,
                       n_clicks=0)
        ], width=3),
        dbc.Col(children=[trans_table,
                          html.Div(id=TransIDs.PLACEDHOLDER,
                                   style={'display': 'none'})
                          ],
                width=9)
    ])
])

"""
Callbacks
"""
START_DATE_DEFAULT = '1900-01-01'
END_DATE_DEFAULT = '2100-01-01'


@dash.callback(
    Output(TransIDs.TRANS_TBL, 'data'),
    Input(TransIDs.CAT_PICKER, 'value'),
    Input(TransIDs.ACC_PICKER, 'value'),
    Input(TransIDs.DATE_PICKER, 'start_date'),
    Input(TransIDs.DATE_PICKER, 'end_date'),
    Input(TransIDs.ADD_ROW_BTN, 'n_clicks'),
    State(TransIDs.TRANS_TBL, 'data'),
    State(TransIDs.TRANS_TBL, 'columns'),
    config_prevent_initial_callbacks=True
)
def update_table_callback(cat: str,
                          account: str,
                          start_date: str,
                          end_date: str,
                          n_clicks: int,
                          rows: list,
                          columns: list):
    """
    This is the main callback for updating the table since each id can only
    have one callback that uses it as output. This function calls helper
    functions based on the triggering element
    :param cat: chosen category in filter dropdown
    :param account: chosen account in filter dropdown
    :param start_date: chosen start date in filter date picker
    :param end_date: chosen end date in filter date picker
    :param n_clicks: property of add row button
    :param rows: rows list of table to append a new row to
    :param columns: columns list of table to provide values for new row
    :return: depends on triggering element
    """
    if dash.callback_context.triggered_id == TransIDs.ADD_ROW_BTN:
        return add_row(n_clicks, rows, columns)
    elif dash.callback_context.triggered_id in [TransIDs.CAT_PICKER,
                                                TransIDs.ACC_PICKER,
                                                TransIDs.DATE_PICKER,
                                                TransIDs.DATE_PICKER]:
        return filter_table(cat, account, start_date, end_date)
    else:
        raise ValueError('Unknown trigger')


def filter_table(cat: str, account: str, start_date: str, end_date: str):
    """
    Filters the table based on the chosen filters
    :return: dict of filtered df
    """
    def create_conditional_filter(col, val):
        return TRANS_DB[col] == val if val is not None else True

    def create_date_cond_filter(col, start_date, end_date):
        # todo raise error when start_date > end_date
        start_date = pd.to_datetime(
            start_date) if start_date is not None else pd.to_datetime(
            START_DATE_DEFAULT)
        end_date = pd.to_datetime(
            end_date) if end_date is not None else pd.to_datetime(
            END_DATE_DEFAULT)
        return (start_date <= TRANS_DB[col]) & (TRANS_DB[col] <= end_date)

    cat_cond = create_conditional_filter(TransDBSchema.CAT, cat)
    account_cond = create_conditional_filter(TransDBSchema.ACCOUNT, account)
    date_cond = create_date_cond_filter(TransDBSchema.DATE, start_date,
                                        end_date)
    table = TRANS_DB[(cat_cond) &
                     (account_cond) &
                     (date_cond)]

    return table.to_dict("records")


def add_row(n_clicks, rows, columns):
    """
    Adds a new row to the table
    :return: list of rows with new row appended
    """
    if n_clicks > 0:
        rows.insert(0, {c['id']: '' for c in columns})
    # todo add new row to trans_df
    return rows


@dash.callback(
    Output(TransIDs.PLACEDHOLDER, 'children'),
    Input(TransIDs.TRANS_TBL, 'active_cell'),
    Input(TransIDs.TRANS_TBL, 'data'),
    config_prevent_initial_callbacks=True
)
def update_trans_df(active_cell, data):
    print(active_cell)
    print('##################################')
    # print(data)
    row, col_name = active_cell['row'], active_cell['column_id']
    # df_row = TRANS_DB[TRANS_DB.id == row_id]
    print(data[row][col_name])
    # df_cell = df_row.loc[0, col_name]
