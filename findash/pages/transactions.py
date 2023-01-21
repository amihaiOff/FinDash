from datetime import datetime
from typing import List, Optional, Tuple, Any, Union
import base64
import io

import dash
import dash_mantine_components as dmc
import pandas as pd
from dash import State, html, dash_table, dcc, Input, Output, ctx, ALL
import dash_bootstrap_components as dbc
from dash.dash_table.Format import Format, Symbol
from dash.exceptions import PreventUpdate


from main import CAT_DB, TRANS_DB
from accounts import ACCOUNTS
from transactions_db import TransDBSchema
from element_ids import TransIDs
from utils import format_date_col_for_display, SHEKEL_SYM
from categories_db import _get_group_and_cat_for_dropdown
from transactions_importer import import_file
from page_elements.transactions_split_window import create_split_trans_modal
from page_elements.transactions_layout_creators import _create_file_uploader, \
    _create_category_change_modal, _create_trans_table, _create_add_row_split_buttons, \
    _create_main_trans_table
from page_elements.transactions_callbacks import *

dash.register_page(__name__)




# insert_file_modal = _create_insert_file_modal()

category_picker = dbc.Card(
    children=[
        dbc.CardHeader('Category'),
        dcc.Dropdown(
            id=TransIDs.CAT_PICKER,
            options=CAT_DB.get_categories())
    ])

group_picker = dbc.Card([
    dbc.CardHeader('Group'),
    dcc.Dropdown(CAT_DB.get_group_names(),
                 placeholder='Select a group',
                 id=TransIDs.GROUP_PICKER)
])

account_picker = dbc.Card([
    dbc.CardHeader('Account'),
    dcc.Dropdown(
        options=TRANS_DB[TransDBSchema.ACCOUNT].unique().tolist(),
        placeholder='Select an account',
        id=TransIDs.ACC_PICKER)
])

date_picker = dbc.Card([
    dbc.CardHeader('Date Range'),
    dmc.DateRangePicker(
        id=TransIDs.DATE_PICKER,
        clearable=True,
        label=''
    )
    # todo - fix up date picker
])


def _create_layout():
    return dbc.Container([
        cat_change_modal := _create_category_change_modal(),
        split_trans_modal := create_split_trans_modal(_create_trans_table),
        dcc.ConfirmDialog(id=TransIDs.ROW_DEL_CONFIRM_DIALOG,
                          displayed=False,
                          message='Are you sure you want to delete this row?'),
        dcc.Store(id=TransIDs.CHANGE_STORE),
        html.Div(id=TransIDs.ROW_DEL_PLACEDHOLDER,
                 style={'display': 'none'}),
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
                dmc.Divider(variant='dashed', size='lg'),
                dmc.Space(h=20),
                dbc.Row(_create_add_row_split_buttons()),
                dmc.Space(h=20),
                upload_file_section := _create_file_uploader(),
                # insert_file_modal
            ], width=2),
            dbc.Col([
                html.Div(_create_main_trans_table(), id=TransIDs.TRANS_TBL_DIV)
            ], width=10),
            dcc.Store(id=TransIDs.INSERT_FILE_SUMMARY_STORE)
        ])
])


layout = _create_layout
