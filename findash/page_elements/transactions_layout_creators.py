from typing import Optional, List, Tuple, Union

import pandas as pd
from dash.dash_table.Format import Format, Symbol
import dash_mantine_components as dmc
import dash_bootstrap_components as dbc
from dash import dcc, dash_table

from element_ids import TransIDs
from main import CAT_DB, TRANS_DB
from accounts import ACCOUNTS
from transactions_db import TransDBSchema
from utils import SHEKEL_SYM, format_date_col_for_display
from categories_db import _get_group_and_cat_for_dropdown


def setup_table_cols(cols_subset: Optional[List[str]] = None) -> List[dict]:
    def setup_col_order():
        col_order = TransDBSchema.get_col_order_for_table()
        num_cols = len(cols_subset) if cols_subset else len(col_order)
        trans_df_cols = [None] * num_cols
        if cols_subset is not None:
            col_order = [col for col in col_order if col in cols_subset]

        return col_order, trans_df_cols

    col_order, trans_df_cols = setup_col_order()
    col_dtypes = TransDBSchema.get_displayed_cols_by_type()
    for col_type, cols in col_dtypes.items():
        for col in cols:
            if cols_subset is not None and col not in cols_subset:
                continue  # we want a subset of the columns

            col_def = {'name': TransDBSchema.col_display_name_mapping()[col],
                       'id': col,
                       'renamable': False,
                       'hideable': True,
                       'deletable': False}

            if col_type == 'date':
                col_def['type'] = 'datetime'

            elif col_type == 'str':
                col_def['type'] = 'text'

            elif col_type == 'numeric':
                col_def['type'] = 'numeric'
                col_def['format'] = Format(group=',').symbol(Symbol.yes).symbol_suffix(SHEKEL_SYM)

            elif col_type == 'cat':
                col_def['presentation'] = 'dropdown'

            elif col_type == 'readonly':
                col_def['editable'] = False

            else:
                raise ValueError(f'Unknown column type: {col_type}')

            # trans_df_cols.append(col_def)
            trans_df_cols[col_order.index(col)] = col_def
    return trans_df_cols

# def _create_insert_file_modal() -> dbc.Modal:
#     """
#
#     :return:
#     """
#     return dbc.Modal(
#         title='Insert Transactions',
#         id=TransIDs.INSERT_FILE_MODAL,
#         children=[
#             dmc.Text()]
#     )


def _create_category_change_modal() -> dmc.Modal:
    """
    Creates a modal for changing the category of a transaction
    :return:
    """
    return dmc.Modal(
        title="Change Category",
        id=TransIDs.MODAL_CAT_CHANGE,
        children=[
            dmc.Text(
                'Would you like to apply this change to all transactions ofthis payee?'
            ),
            dmc.Space(h=20),
            dmc.Group(
                [
                    dmc.Button(
                        "Yes",
                        id=TransIDs.MODAL_CAT_CHANGE_YES,
                        color="primary",
                    ),
                    dmc.Button(
                        "No",
                        color="red",
                        variant="outline",
                        id=TransIDs.MODAL_CAT_CHANGE_NO,
                    ),
                ],
                position="right",
            ),
        ],
    )


def _create_file_uploader():
    uploader = dcc.Upload(
        id='file_uploader',
        multiple=True,
        children=[dbc.Button('Upload File')]
    )
    acc_names = [acc_name for acc_name, _ in ACCOUNTS.items()]
    dropdown = dcc.Dropdown(id=TransIDs.FILE_UPLOADER_DROPDOWN,
                            placeholder='Select account',
                            clearable=False,
                            options=[{'label': f'{account}',
                                      'value': f'{account}'} for
                                            account in acc_names],
                            )
    return dbc.Card([
                dbc.CardHeader('Upload Transactions'),
                dropdown,
                dmc.Space(h=8),
                uploader,
                ],
            )


def _setup_table_cell_dropdowns():
    account_names = [acc_name for acc_name, _ in ACCOUNTS.items()]

    dropdown_options = {
        TransDBSchema.CAT: {
            'options': _get_group_and_cat_for_dropdown(CAT_DB),
        },
        TransDBSchema.ACCOUNT: {
            'options': [{'label': f'{account}', 'value': f'{account}'} for
                        account in account_names]
        },
    }
    return dropdown_options


def _create_add_row_split_buttons() -> Tuple[dbc.Col, dbc.Col]:
    """
    Creates the add row and split transaction buttons
    :return:
    """
    add_row_btn = dbc.Col([dbc.Button('Add row',
                                      id=TransIDs.ADD_ROW_BTN,
                                      n_clicks=0,
                                      style=({'font-size': '14px'}))])
    split_btn = dbc.Col([dbc.Button('Split',
                                    id=TransIDs.SPLIT_BTN,
                                    style=({'font-size': '14px'}))])

    return add_row_btn, split_btn


def create_trans_table(id: str,
                       table: pd.DataFrame,
                       row_selectable: Union[str, bool, float] = False,
                       rows_deletable: bool = True,
                       filter_action: str = 'none',
                       subset_cols: Optional[List[str]] = None,
                       export_format: str = 'xlsx',
                       editable: bool = True) -> dash_table.DataTable:
    """
    Creates the transaction table
    :param row_selectable: Whether the table rows are selectable,
                           Options: 'single', 'multi', False
    :return:
    """
    trans_db_formatted = format_date_col_for_display(table,
                                                     TransDBSchema.DATE)
    col_defs = setup_table_cols(subset_cols)

    if subset_cols is not None:
        trans_db_formatted = trans_db_formatted[subset_cols]
        # col_defs = setup_table_cols(subset_cols)

    tooltip_data = None
    if subset_cols is None or TransDBSchema.MEMO in subset_cols:
        tooltip_data = [{column: {'value': str(value), 'type': 'markdown'}
                           for column, value in row.items()} for row in
                        trans_db_formatted[TransDBSchema.MEMO].to_frame().to_dict('records')]

    return dash_table.DataTable(data=trans_db_formatted.to_dict('records'),
                                id=id,
                                editable=editable,
                                filter_action=filter_action,
                                export_format=export_format,
                                export_headers='display',
                                row_selectable=row_selectable,
                                sort_by=[{'column_id': TransDBSchema.DATE,
                                          'direction': 'desc'}],
                                page_size=50,
                                row_deletable=rows_deletable,
                                fill_width=False,
                                style_table={'overflowX': 'auto'},
                                columns=col_defs,
                                dropdown=_setup_table_cell_dropdowns(),
                                style_data_conditional=[
                                    {'if': {'row_index': 'odd'},
                                        'backgroundColor': 'rgb(240, 246, 255)'},
                                    {'if': {'column_id': TransDBSchema.MEMO},
                                        'textOverflow': 'ellipsis',
                                        'maxWidth': 200,
                                        'overflow': 'hidden'},
                                    {'if': {'column_id': TransDBSchema.DATE},
                                        'color': 'gray'},
                                ],
                                tooltip_data=tooltip_data,
                                tooltip_duration=20000,
                                style_data={
                                    'border': 'none',
                                    },
                                style_cell={
                                    'textAlign': 'center',
                                    'font-family': 'sans-serif',
                                    'font-size': '12px',
                                    'padding-right': '5px',
                                    'padding-left': '5px'
                                }
                                )


def _create_main_trans_table() -> dash_table.DataTable:
    """
    Creates the main transaction table
    :return:
    """
    col_subset = [TransDBSchema.DATE, TransDBSchema.PAYEE, TransDBSchema.INFLOW,
                 TransDBSchema.OUTFLOW, TransDBSchema.CAT, TransDBSchema.MEMO,
                 TransDBSchema.ACCOUNT]
    return create_trans_table(id=TransIDs.TRANS_TBL,
                              table=TRANS_DB,
                              subset_cols=col_subset)


def _create_file_insert_summary_modal() -> dmc.Modal:
    """
    Creates a modal for showing the summary of the file insert
    :return:
    """
    return dmc.Modal(
        title="File Insert Summary",
        id=TransIDs.INSERT_FILE_SUMMARY_MODAL,
        children=[
            dmc.Text(
                [],
                id=TransIDs.INSERT_FILE_SUMMARY_LABEL
            ),
        ],
    )
