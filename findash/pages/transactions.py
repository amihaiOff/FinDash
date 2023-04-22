from dash import html, dcc
import dash_bootstrap_components as dbc
from dash_iconify import DashIconify

from accounts import ACCOUNTS
from shared_elements import create_page_heading
from page_elements.transactions_split_window import create_split_trans_modal
from page_elements.transactions_layout_creators import _create_file_uploader, \
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
            ], position='apart', style={'box-shadow': '5px 5px 5px -3px rgba(0, 0, 0, 0.5)',
                                        'border-radius': '10px'})
        ], style={'margin-bottom': '40px'}),
        dbc.Row([
            html.Div(_create_main_trans_table(), id=TransIDs.TRANS_TBL_DIV, style={'width': '100%'})
        ])
    ])
    container.children.extend([
        create_split_trans_modal(create_trans_table),
        _create_file_uploader(),
        dcc.ConfirmDialog(id=TransIDs.ROW_DEL_CONFIRM_DIALOG,
                          displayed=False,
                          message='Are you sure you want to delete this row?'),
        _create_file_insert_summary_modal(),
        dcc.Store(id=TransIDs.CHANGE_STORE),
        dcc.Store(id=TransIDs.INSERT_FILE_SUMMARY_STORE),
    ])
    return container


layout = _create_layout
