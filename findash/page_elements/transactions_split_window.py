from functools import partial
from typing import Optional, List, Callable

import dash_mantine_components as dmc
from dash_iconify import DashIconify
from dash import html, dash_table

from element_ids import TransIDs
from transactions_db import TransDBSchema
from categories_db import _get_group_and_cat_for_dropdown
from main import CAT_DB, TRANS_DB


def _create_split_input(split_num) -> dmc.Group:
    icon = dmc.Tooltip(children=[DashIconify(icon="radix-icons:question-mark-circled")],
                       label='Must be less than original transaction',
                       withArrow=True,
                       position='top'
    )
    return dmc.Group([
            dmc.TextInput(id={'type': 'split_amount',
                              'index': f'{TransIDs.SPLIT_AMOUNT}-{split_num}'},
                          placeholder='Amount',
                          type='number',
                          label=dmc.Group(['Split amount', icon],
                                          spacing=5),
                          style={'width': '20%'}),
            dmc.TextInput(id={'type': 'split_memo',
                              'index': f'{TransIDs.SPLIT_MEMO}-{split_num}'},
                          placeholder='Memo',
                          label='Add memo',
                          style={'width': '40%'}),
            dmc.Select(
                id={'type': 'split_cat',
                    'index': f'{TransIDs.SPLIT_CAT}-{split_num}'},
                label='Category',
                searchable=True,
                nothingFound="No options found",
                data=_get_group_and_cat_for_dropdown(CAT_DB),
                style={'width': '30%'})
    ],
        align='flex-end')


def _create_split_input_card(split_num: int):
    return dmc.Card([
        dmc.CardSection([
            dmc.Text(f'Split {split_num}', weight=500)],
            inheritPadding=True,
            py='xs',
            withBorder=True),
        _create_split_input(split_num)],
        withBorder=True,
        style={'z-index': 999, 'overflow': 'visible'},
        shadow="sm",
        radius="md",
    )


def _create_split_trans_table(table_creation_func: Callable,
                              table: Optional[List[int]] = None) \
        -> dash_table.DataTable:
    if table is None:
        table = TRANS_DB

    return table_creation_func(id=TransIDs.SPLIT_TBL,
                               table=table,
                               row_selectable='single',
                               rows_deletable=False,
                               filter_action='native',
                               subset_cols=[TransDBSchema.DATE,
                                            TransDBSchema.PAYEE,
                                            TransDBSchema.AMOUNT],
                               export_format=None,
                               editable=False)


def _create_split_notif(msg: str, color: str, title: str, action: str, **kwargs) -> dmc.Notification:
    return dmc.Notification(
        title=title,
        message=msg,
        color=color,
        action=action,
        **kwargs
    )


_create_split_fail = partial(_create_split_notif, color='red',
                             title='Split error', action='show',
                             id='split-fail-notif',
                             icon=DashIconify(icon="akar-icons:circle-x"))
_create_split_success = partial(_create_split_notif, color='green',
                                title='Split success', action='show',
                                id='split-success-notif',
                                icon=DashIconify(icon="akar-icons:circle-check"))


def create_split_trans_modal(create_table_func: Callable) -> dmc.Modal:
    table = _create_split_trans_table(create_table_func)

    return dmc.Modal(
        title='Split Transaction',
        id=TransIDs.SPLIT_MODAL,
        children=[
            # html.Div(id=TransIDs.SPLIT_NOTIF_DIV),
            html.Div([
                html.Div(dmc.Button(id=TransIDs.ADD_SPLIT_BTN,
                                    children=['+'],
                                    radius='xl',
                                    size='lg',
                                    compact=True),
                         style={'position': 'fixed', 'bottom': '50px', 'right': '50px'}),
                html.Div(dmc.Button(id=TransIDs.APPLY_SPLIT_BTN,
                                    children=['Apply'],
                                    size='md'),
                            style={'position': 'fixed', 'bottom': '50px', 'right': '550px'}
                         ),

                dmc.Grid([
                    dmc.Col([html.Div(table, id=TransIDs.SPLIT_TBL_DIV)],
                            style={'max-height': '90vh', 'overflowY': 'auto'},
                            span=5),
                    dmc.Col([
                        _create_split_input_card(1),
                        _create_split_input_card(2),
                        # dmc.Button(id=TransIDs.APPLY_SPLIT_BTN,
                        #            children=['Apply'],
                        #            size='md'),
                        # dmc.Button(id=TransIDs.ADD_SPLIT_BTN,
                        #            children=['+'],
                        #            radius='xl',
                        #            size='lg',
                        #            compact=True),
                    ],
                        id=TransIDs.SPLITS_COL,
                        style={'overflowY': 'auto'},
                        span=6),
                ])
            ], style={'height': '100%'})

        ],
        size='90%',
        styles={'modal': {'height': '90vh'}},
        overflow='inside',
        closeOnClickOutside=True,
        closeOnEscape=True,
    )
