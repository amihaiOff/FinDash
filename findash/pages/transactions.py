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
from dash_iconify import DashIconify

from main import CAT_DB, TRANS_DB
from accounts import ACCOUNTS
from shared_elements import create_page_heading
from transactions_db import TransDBSchema
from element_ids import TransIDs
from utils import format_date_col_for_display, SHEKEL_SYM
from categories_db import _get_group_and_cat_for_dropdown
from transactions_importer import import_file
from page_elements.transactions_split_window import create_split_trans_modal
from page_elements.transactions_layout_creators import _create_file_uploader, \
    _create_category_change_modal, create_trans_table, _create_add_row_split_buttons, \
    _create_main_trans_table, _create_file_insert_summary_modal
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
        options=list(ACCOUNTS.keys()),
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


def _create_filtering_components():
    return dmc.Group([
                dmc.Select(data=CAT_DB.get_categories(),
                           id=TransIDs.CAT_PICKER,
                           clearable=True,
                           placeholder='Select a category',
                           icon=DashIconify(icon='ic:round-category')),
                dmc.Select(data=CAT_DB.get_group_names(),
                           id=TransIDs.GROUP_PICKER,
                           clearable=True,
                           placeholder='Select a group',
                           icon=DashIconify(icon='ic:round-category')),
                dmc.Select(data=list(ACCOUNTS.keys()),
                           id=TransIDs.ACC_PICKER,
                           clearable=True,
                           placeholder='Select an account',
                           icon=DashIconify(icon='ic:round-account-balance-wallet')),
                dmc.DateRangePicker(id=TransIDs.DATE_PICKER,
                                    clearable=True,
                                    label='',
                                    placeholder='Select a date range',
                                    icon=DashIconify(icon='ic:round-date-range'))
            ])


def _create_add_del_row_components():
    return dmc.Group([
        dmc.ActionIcon(DashIconify(icon='mdi:table-row-plus-before', width=40),
                       id=TransIDs.ADD_ROW_BTN,
                       size='xl'),
        dmc.ActionIcon(children=DashIconify(icon='ic:round-upload-file', width=35),
                       id=TransIDs.UPLOAD_FILE_ICON,
                       size='xl'),
    ])


def _create_layout():
    container = dmc.Grid([
        dbc.Row([
            create_page_heading('Transactions')
        ]),
        dbc.Row([
            dmc.Group([
                _create_filtering_components(),
                _create_add_del_row_components()
            ], position='apart')
        ], style={'margin-bottom': '40px'}),
        dbc.Row([
            html.Div(_create_main_trans_table(), id=TransIDs.TRANS_TBL_DIV, style={'width': '100%'})
        ])
        # dbc.Row([
        #     dbc.Col([
        #         category_picker,
        #         html.Br(),
        #         group_picker,
        #         html.Br(),
        #         account_picker,
        #         html.Br(),
        #         date_picker,
        #         html.Br(),
        #         dmc.Divider(variant='dashed', size='lg'),
        #         dmc.Space(h=20),
        #         dbc.Row(_create_add_row_split_buttons()),
        #         dmc.Space(h=20),
        #         # todo insert_file_modal
        #     ], width=2),
        #     dbc.Col([
        #         html.Div(_create_main_trans_table(), id=TransIDs.TRANS_TBL_DIV)
        #     ], width=10),
        # ])
    ])
    container.children.extend([
        cat_change_modal := _create_category_change_modal(),
        split_trans_modal := create_split_trans_modal(create_trans_table),
        upload_file_section := _create_file_uploader(),
        dcc.ConfirmDialog(id=TransIDs.ROW_DEL_CONFIRM_DIALOG,
                          displayed=False,
                          message='Are you sure you want to delete this row?'),
        _create_file_insert_summary_modal(),
        dcc.Store(id=TransIDs.CHANGE_STORE),
        dcc.Store(id=TransIDs.INSERT_FILE_SUMMARY_STORE),
        html.Div(id=TransIDs.ROW_DEL_PLACEDHOLDER,
                 style={'display': 'none'}),
    ])
    return container


layout = _create_layout
