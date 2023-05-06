from dash import html, dcc
import dash_bootstrap_components as dbc
from dash_iconify import DashIconify

from accounts import ACCOUNTS
from shared_elements import create_page_heading
from page_elements.transactions_split_window import create_split_trans_modal
from page_elements.transactions_layout_creators import create_file_upload_modal, \
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


def _create_action_icon(icon, id, tooltip_label: str, size='xl'):
    return dmc.Tooltip(dmc.ActionIcon(children=DashIconify(icon=icon, width=35),
                                      id=id,
                                      size=size),
                       label=tooltip_label,
                       position='right',
                       color='gray',
                       transition='slide-up',
                       withArrow=True,
                       openDelay=500)


def _create_add_action_icons():
    return dmc.HoverCard([
        dmc.HoverCardTarget(DashIconify(icon='mdi:dots-horizontal', width=35, color='gray')),
        dmc.HoverCardDropdown([
            dmc.Stack([
                _create_action_icon('mdi:table-row-plus-before',
                                    TransIDs.ADD_ROW_BTN, 'Add Row'),
                _create_action_icon('ic:round-upload-file',
                                    TransIDs.UPLOAD_FILE_ICON, 'Upload File'),
                _create_action_icon('ic:outline-splitscreen',
                                    TransIDs.SPLIT_ICON, 'Split Transaction')
            ])
        ], className='hover-card-dropdown')
    ])


def _create_layout():
    import logging
    logger = logging.getLogger('Logger')
    logger.info('Creating transactions layout')
    container = dmc.Grid([
        dmc.Col([
            create_page_heading('Transactions')
        ], span=12),
        dmc.Space(h=150),
        dmc.Col([
            dmc.Group([
                _create_filtering_components(),
                _create_add_action_icons()
            ], position='apart')
        ], style={'margin-bottom': '40px'}, span=12),
        dmc.Col([
            html.Div(_create_main_trans_table(), id=TransIDs.TRANS_TBL_DIV, style={'width': '100%'})
        ], span=12)
    ], id='trans_cont')
    container.children.extend([
        html.Div(id=TransIDs.NOTIF_DIV),
        create_split_trans_modal(create_trans_table),
        create_file_upload_modal(),
        dcc.ConfirmDialog(id=TransIDs.ROW_DEL_CONFIRM_DIALOG,
                          displayed=False,
                          message='Are you sure you want to delete this row?'),
        _create_file_insert_summary_modal(),
        dcc.Store(id=TransIDs.CHANGE_STORE),
        dcc.Store(id=TransIDs.INSERT_FILE_SUMMARY_STORE),
    ])
    return container


layout = _create_layout
