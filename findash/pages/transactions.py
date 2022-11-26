from typing import List, Optional, Tuple

import dash
import dash_mantine_components as dmc
import numpy as np
import pandas as pd
from dash import State, html, dash_table, dcc, Input, Output, ctx
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate

from main import TRANS_DB, CAT_DB
from transactions_db import TransDBSchema
from categories_db import CatDBSchema
from element_ids import TransIDs
from utils import format_date_col_for_display

# for filtering the trans table
START_DATE_DEFAULT = '1900-01-01'
END_DATE_DEFAULT = '2100-01-01'


def setup_table_cols():
    col_dtypes = TransDBSchema.get_displayed_cols_by_type()
    trans_df_cols = []
    for col_type, cols in col_dtypes.items():
        for col in cols:
            col = {'name': f'{col}',
                   'id': f'{col}',
                   'deletable': False,
                   'renamable': False,
                   'hideable': True}

            if col_type == 'date':
                col['type'] = 'datetime'

            elif col_type == 'str':
                col['type'] = 'text'

            elif col_type == 'numeric':
                col['type'] = 'numeric'

            elif col_type == 'cat':
                col['presentation'] = 'dropdown'

            elif col_type == 'readonly':
                col['editable'] = False

            else:
                raise ValueError(f'Unknown column type: {col_type}')

            trans_df_cols.append(col)
    return trans_df_cols


def _create_category_change_modal() -> dmc.Modal:
    """
    Creates a modal for changing the category of a transaction
    :return:
    """
    return dmc.Modal(
        title="Change Category",
        id=TransIDs.MODAL_CAT_CHANGE,
        children=[
            dmc.Text(f"Would you like to apply this change to all transactions of"
                     f"this payee?"),
            dmc.Space(h=20),
            dmc.Group(
                [
                    dmc.Button("Yes", id=TransIDs.MODAL_CAT_CHANGE_YES,
                               color="primary"),
                    dmc.Button(
                        "No",
                        color="red",
                        variant="outline",
                        id=TransIDs.MODAL_CAT_CHANGE_NO
                    ),
                ],
                position="right",
            ),
        ],
    )


def setup_table_cell_dropdowns():
    dropdown_options = {
        TransDBSchema.CAT: {
            'options': [{'label': f'{cat}', 'value': f'{cat}'} for cat in
                        CAT_DB.get_categories()]
        },
        TransDBSchema.ACCOUNT: {
            'options': [{'label': f'{account}', 'value': f'{account}'} for
                        account in TRANS_DB[TransDBSchema.ACCOUNT].unique()]
        },
    }
    return dropdown_options


dash.register_page(__name__)


def _create_trans_table() -> dash_table.DataTable:
    """
    Creates the transaction table
    :return:
    """
    trans_db_formatted = format_date_col_for_display(TRANS_DB,
                                                     TransDBSchema.DATE)
    return dash_table.DataTable(data=trans_db_formatted.to_dict('records'),
                                id=TransIDs.TRANS_TBL,
                                editable=True,
                                export_format='xlsx',
                                export_headers='display',
                                sort_by=[{'column_id': TransDBSchema.DATE,
                                          'direction': 'desc'}],
                                # fixed_rows={'headers': True},
                                page_action='native',
                                page_size=50,
                                row_deletable=True,
                                style_table={'height': '2000px'},
                                             # 'overflowX': 'auto'},
                                columns=setup_table_cols(),
                                dropdown=setup_table_cell_dropdowns(),
                                style_data_conditional=[
                                    {'if': {'row_index': 'odd'},
                                        'backgroundColor': 'rgb(220, 220, 220)'},
                                    {'if': {'column_id': TransDBSchema.ID},
                                        'width': '500px'},
                                    {'if': {'column_id': TransDBSchema.MEMO},
                                        'width': '50px'},
                                ],
                                # style_cell={
                                #     'overflow': 'hidden',
                                #     'textOverflow': 'ellipsis',
                                #     'maxWidth': 10
                                # },
                                tooltip_data=[
                                       {
                                           column: {'value': str(value), 'type': 'markdown'}
                                           for column, value in row.items()
                                       } for row in trans_db_formatted.to_dict('records')
                                   ],
                                tooltip_duration=20000,
                                # style_data={
                                #         'whiteSpace': 'normal',
                                #         'height': 'auto',
                                #     },
                                )


trans_table = _create_trans_table()

category_picker = dbc.Card(
    children=[
        dbc.CardHeader('Category'),
        dcc.Dropdown(
            id=TransIDs.CAT_PICKER,
            options=CAT_DB.get_categories())
    ])

group_picker = dbc.Card([
    dbc.CardHeader('Group'),
    dcc.Dropdown(CAT_DB.get_group_names())
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

cat_change_modal = _create_category_change_modal()

layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            category_picker,
            html.Br(),
            group_picker,
            html.Br(),
            account_picker,
            html.Br(),
            date_picker,
            html.Br(),
            dbc.Button('Add row',
                       id=TransIDs.ADD_ROW_BTN,
                       n_clicks=0),
            cat_change_modal
        ], width=2),
        dbc.Col(children=[trans_table,
                          html.Div(id=TransIDs.PLACEDHOLDER,
                                   style={'display': 'none'})],
                width=10)
    ])
])

"""
Callbacks
"""


def _detect_changes_in_table(df: pd.DataFrame,
                             df_previous: pd.DataFrame,
                             row_id_name: Optional[str] = None) \
        -> Optional[dict]:
    """
     Modified from: https://community.plotly.com/t/detecting-changed-cell-in-editable-datatable/26219/2
    :param df:
    :param df_previous:
    :param row_id_name:
    :return:
    """
    if row_id_name is not None:
       # If using something other than the index for row id's, set it here
       for _df in [df, df_previous]:
           _df = _df.set_index(row_id_name)
    else:
       row_id_name = "index"

    # todo make more efficient since we know there is only one change
    # Pandas/Numpy says NaN != NaN, so we cannot simply compare the dataframes.  Instead we can either replace the
    # NaNs with some unique value (which is fastest for very small arrays, but doesn't scale well) or we can do
    # (from https://stackoverflow.com/a/19322739/5394584):
    # Mask of elements that have changed, as a dataframe.  Each element indicates True if df!=df_prev
    df_mask = ~((df == df_previous) | (
                (df != df) & (df_previous != df_previous)))

    # ...and keep only rows that include a changed value
    df_mask = df_mask.loc[df_mask.any(axis=1)]
    changes = []
    for idx, row in df_mask.iterrows():
        row_id = row.name

        # Act only on columns that had a change
        row = row[row.eq(True)]
        for change in row.iteritems():
            changes.append(
                {
                    row_id_name: row_id,
                    "column_name": change[0],
                    "current_value": df.at[row_id, change[0]],
                    "previous_value": df_previous.at[row_id, change[0]],
                }
            )

    return changes[0] if len(changes) == 1 else None


def _open_modal(change) -> bool:
    """ logic for opening cat change modal """
    if change is None:
        return False

    # first time setting a category
    if change['previous_value'] == '':
        return False

    # open modal
    return True


def _trans_table_callback_trigger(data: List[dict],
                                  data_prev: List[dict]) -> bool:
    """
    logic for handling callbacks triggered by changes to trans table
    :param data:
    :param data_prev:
    :return:
    """
    to_open_modal = False
    data, data_prev = pd.DataFrame(data=data), pd.DataFrame(data_prev)
    if len(data) != len(data_prev):
        _add_or_remove_row(data, data_prev)  # updates TRANS_DB
        return to_open_modal

    change = _detect_changes_in_table(data, data_prev)
    if change['column_name'] != TransDBSchema.CAT:
        # there is another callback for dealing with changes in cat column
        _apply_changes_to_trans_db_no_cat(change)  # updates TRANS_DB

    else:
        to_open_modal = _open_modal(change)
        # if not to_open_modal:  # the change will happen after modal selection
        _apply_changes_to_trans_db_cat_col(change, all_trans=False)

    return to_open_modal


def _cat_change_modal_callback_trigger(data: List[dict],
                                       data_prev: List[dict]) -> None:
    """
    logic for handling callbacks triggered by changes to cat change modal
    :param data:
    :param data_prev:
    :return:
    """
    data, data_prev = pd.DataFrame(data=data), pd.DataFrame(data_prev)
    change = _detect_changes_in_table(data, data_prev)
    if ctx.triggered_id == TransIDs.MODAL_CAT_CHANGE_NO:
        all_trans = False
    elif ctx.triggered_id == TransIDs.MODAL_CAT_CHANGE_YES:
        all_trans = True
    else:
        raise ValueError("Invalid triggered id in cat change modal")
    _apply_changes_to_trans_db_cat_col(change, all_trans)


@dash.callback(
    Output(TransIDs.TRANS_TBL, 'data'),
    Output(TransIDs.MODAL_CAT_CHANGE, 'opened'),
    Input(TransIDs.CAT_PICKER, 'value'),
    Input(TransIDs.ACC_PICKER, 'value'),
    Input(TransIDs.DATE_PICKER, 'start_date'),
    Input(TransIDs.DATE_PICKER, 'end_date'),
    Input(TransIDs.ADD_ROW_BTN, 'n_clicks'),
    State(TransIDs.TRANS_TBL, 'data'),
    State(TransIDs.TRANS_TBL, 'columns'),
    Input(TransIDs.TRANS_TBL, "data"),
    Input(TransIDs.TRANS_TBL, "data_previous"),
    Input(TransIDs.MODAL_CAT_CHANGE_YES, 'n_clicks'),
    Input(TransIDs.MODAL_CAT_CHANGE_NO, 'n_clicks'),
    State(TransIDs.MODAL_CAT_CHANGE, 'opened'),
    config_prevent_initial_callbacks=True
)
def update_table_callback(cat: str,
                          account: str,
                          start_date: str,
                          end_date: str,
                          n_clicks: int,
                          rows: list,
                          columns: list,
                          data: list,
                          data_prev: list,
                          yes_clicks: int,
                          no_clicks: int,
                          opened: bool) -> Tuple[list, bool]:
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
    :param data: current data in trans table
    :param data_prev: previous data in trans table
    :param yes_clicks: property of yes button in change cat modal
    :param no_clicks: property of no button in change cat modal
    :param opened: property of change cat modal - if it is opened
    :return: changes to table data and if the change cat modal should be opened
    """
    to_open_modal = False
    if dash.callback_context.triggered_id == TransIDs.ADD_ROW_BTN:
        return add_row(n_clicks, rows, columns), to_open_modal

    elif dash.callback_context.triggered_id in [TransIDs.CAT_PICKER,
                                                TransIDs.ACC_PICKER,
                                                TransIDs.DATE_PICKER,
                                                TransIDs.DATE_PICKER]:
        return _filter_table(cat, account, start_date, end_date), to_open_modal

    elif dash.callback_context.triggered_id == TransIDs.TRANS_TBL:
        to_open_modal = _trans_table_callback_trigger(data, data_prev)

    elif dash.callback_context.triggered_id in [TransIDs.MODAL_CAT_CHANGE_YES,
                                                TransIDs.MODAL_CAT_CHANGE_NO]:
        _cat_change_modal_callback_trigger(data, data_prev)
    else:
        raise ValueError('Unknown trigger')

    return TRANS_DB.get_records(), to_open_modal


def _filter_table(cat: str, account: str, start_date: str, end_date: str):
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
    return rows


def _add_or_remove_row(df: pd.DataFrame, df_previous: pd.DataFrame):
    """
    The users added or removed a row from the trans table -> update the db
    :param df:
    :param df_previous:
    :return:
    """
    if len(df) > len(df_previous):
        # user added a row
        TRANS_DB.add_blank_row()
    else:
        removed_id = (set(df_previous.id) - set(df.id)).pop()
        TRANS_DB.remove_row_with_id(removed_id)


def _apply_changes_to_trans_db_no_cat(change: dict):
    """
    given a dict of changes the user made in trans table. apply them to trans
    db
    :param change: dict with keys: index, column_name, previous_value,
                                    current_value
    :return:
    """
    ind, col_name = change['index'], change['column_name']
    prev_val = change['previous_value']
    db_val = TRANS_DB[col_name].iloc[ind]
    if col_name == TransDBSchema.DATE:
        db_val = str(db_val.date())
    db_val = None if pd.isna(db_val) else db_val
    if db_val != prev_val:
        raise ValueError('mismatch between prev_value and db value when'
                         'trying to apply changes')

    TRANS_DB.update_data(col_name=col_name, index=ind,
                         value=change['current_value'])


def _apply_changes_to_trans_db_cat_col(change: dict, all_trans: bool):
    """
    change the category of the transactions in trans db. If all_trans - change
    all transactions of given payee
    :param all_trans: if True change all transactions of given payee
    :return:
    """
    if change['current_value'] == change['previous_value']:
        return

    if change['current_value'] is None:
        # None is not a valid category
        change['current_value'] = ''

    if all_trans:
        payee = TRANS_DB.loc[change['index'], TransDBSchema.PAYEE]
        TRANS_DB.loc[TRANS_DB[TransDBSchema.PAYEE] == payee, TransDBSchema.CAT]\
            = change['current_value']
        uuids = TRANS_DB.loc[TRANS_DB[TransDBSchema.PAYEE] == payee,
                             TransDBSchema.ID].to_list()
        TRANS_DB.save_db_from_uuids(uuids)
    else:
        TRANS_DB.update_data(TransDBSchema.CAT, change['index'],
                             change['current_value'])
