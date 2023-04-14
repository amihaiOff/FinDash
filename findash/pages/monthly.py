from typing import Dict, Tuple, Optional, List

import dash
import numpy as np
from dash import html, Output, Input, State, ctx, ALL
import dash_bootstrap_components as dbc
from dash import dcc
import dash_mantine_components as dmc

import pandas as pd
from dash.exceptions import PreventUpdate
from dash_iconify import DashIconify

from main import CAT_DB, TRANS_DB
from accounts import ACCOUNTS
from element_ids import MonthlyIDs
from categories_db import CatDBSchema
from shared_elements import create_page_heading
from transactions_db import TransDBSchema
from utils import SHEKEL_SYM, conditional_coloring, get_current_year_month, \
    create_table, format_date_col_for_display, format_currency_num, safe_divide

dash.register_page(__name__)


def _create_month_dd():
    months = TRANS_DB[TransDBSchema.DATE].dt.strftime('%Y-%m')
    months = months.unique().tolist()
    return dmc.Select(
        id=MonthlyIDs.MONTHLY_DD,
        data=months,
        value=None,
        size='lg',
        clearable=False
    )


def _calculate_outflow_total(last: bool = False) -> float:
    db = TRANS_DB.specific_month if last else TRANS_DB
    return db[TransDBSchema.OUTFLOW].sum()


def _calculate_checking_total(last: bool = False) -> float:
    """
    sum of all inflow from checking accounts (reimbursements from credit don't
    count)
    :param last: if True, sum only this month's inflow
    """
    # checking_accounts = [acc.institution for acc in ACCOUNTS.values()]
    checking_accounts = list(ACCOUNTS.keys())
    db = TRANS_DB.specific_month if last else TRANS_DB
    return db[db[TransDBSchema.ACCOUNT].isin(checking_accounts)][
            TransDBSchema.INFLOW].sum()


def _curr_expenses_from_budget_pct() -> Optional[float]:
    """ divide current month's expenses by current month's budget """
    current_budget = CAT_DB.get_total_budget()
    if current_budget == 0:
        return None
    else:
        return _calculate_outflow_total(last=True) * 100 / current_budget


def _curr_expenses_from_income_pct() -> Optional[float]:
    """ divide current month's expenses by current month's income """
    current_income = _calculate_checking_total(last=True)
    if current_income == 0:
        return None
    current_expenses = TRANS_DB.specific_month[TransDBSchema.OUTFLOW].sum()
    return current_expenses * 100 / current_income


def _pct_budget_used():
    curr_expenses = _calculate_checking_total(last=True)
    curr_budget = CAT_DB.get_budget()
    return curr_expenses * 100 / curr_budget


def _get_balance_per_account_for_popup():
    per_account = TRANS_DB.specific_month.groupby(TransDBSchema.ACCOUNT)[
        TransDBSchema.INFLOW].sum()
    checking_str = [acc.institution for acc in ACCOUNTS.values() if
                    acc.is_checking]
    checking_only = per_account[per_account.index.isin(checking_str)]
    string_rep = ''.join(
        f'**{account}**: {acc_sum}\n'
        for account, acc_sum in checking_only.items()
    )
    return string_rep[:-1]


def _get_income_per_account_popup():
    per_account = TRANS_DB.specific_month.groupby(TransDBSchema.ACCOUNT)[
        TransDBSchema.OUTFLOW].sum()
    non_checking_str = [acc.institution for acc in ACCOUNTS.values() if
                        acc.is_checking]
    non_checking_only = per_account[per_account.index.isin(non_checking_str)]
    string_rep = ''.join(
        f'**{account}**: {acc_sum}\n'
        for account, acc_sum in non_checking_only.items()
    )
    return string_rep[:-1]


def _create_stat_headings() -> Tuple[dmc.Group, Tuple[dbc.Popover, dbc.Popover]]:
    checking_card, checking_popover = _create_checking_card()
    income_card, income_popover = _create_income_card()
    expenses_card = _create_expenses_card()
    savings_card = _create_savings_card()
    group = dmc.Group([
        checking_card,
        income_card,
        expenses_card,
        savings_card,
    ], position='apart')

    return group, (checking_popover, income_popover)


def _create_banner_card(title: str,
                        value: float,
                        subtitle: str,
                        color: str,
                        id: str) -> dbc.Card:
    return dbc.Card([
        html.H2(title),
        html.H3(f"{format_currency_num(value)}"),
        html.P(subtitle, style={'color': color})],
        body=True,
        id=id,
        outline=True,
        color='light'
    )


def _create_checking_card():
    checking_total = _calculate_checking_total()

    checking_card = dbc.Card([
                    html.H2("Checking"),
                    html.H3(f"{checking_total:,.0f}{SHEKEL_SYM}"),
                    html.P("+12% MoM(?)", style={'color': 'green'})], # todo - think of what the subtitle needs to be
                    body=True,
                    id=MonthlyIDs.CHECKING_CARD,
                    color='light',
                    outline=True
    )

    checking_popover = dbc.Popover([
        dbc.PopoverHeader('Breakdown'),
        dbc.PopoverBody([
            dcc.Markdown(_get_balance_per_account_for_popup(),
                         style={'white-space': 'pre'})
        ])],
        target='checking-card',
        trigger='hover',
        placement='bottom',
        id=MonthlyIDs.CHECKING_POPOVER
    )

    return checking_card, checking_popover


def _create_income_card() -> Tuple[dbc.Card, dbc.Popover]:
    income = _calculate_checking_total(last=True)
    if income == 0:
        subtitle = 'No income this month'
        color = 'red'
    else:
        curr_expenses_pct = _curr_expenses_from_income_pct()
        subtitle = f"{curr_expenses_pct:.0f}% income used"
        color = conditional_coloring(curr_expenses_pct, {'green': (0, np.inf),
                                                         'red': (-np.inf, 0)})
    card = _create_banner_card(title='Last Income',
                               value=income,
                               subtitle=subtitle,
                               color=color,
                               id=MonthlyIDs.INCOME_CARD)

    income_popover = dbc.Popover([
        dbc.PopoverHeader('Breakdown'),
        dbc.PopoverBody([
            dcc.Markdown(_get_income_per_account_popup(),
                         style={'white-space': 'pre'})
        ])],
        target='income-card',
        trigger='hover',
        placement='bottom',
        id=MonthlyIDs.INCOME_POPOVER
    )
    return card, income_popover


def _create_expenses_card():
    expenses = _calculate_outflow_total(True)
    curr_expenses_pct = _curr_expenses_from_budget_pct()
    if curr_expenses_pct is None:
        color = 'red'
        subtitle = 'No budget this month'
    else:
        color = conditional_coloring(curr_expenses_pct, {
            'green': (0, np.inf),
            'red': (-np.inf, 0)
        })
        subtitle = f"{curr_expenses_pct:.0f}% budget used"

    return _create_banner_card(title="Expenses",
                               value=expenses,
                               subtitle=subtitle,
                               color=color,
                               id=MonthlyIDs.EXPENSES_CARD
                               )


def _create_savings_card():
    return _create_banner_card(
        title='Savings',
        value=2000,
        subtitle='Previous month 1000',
        color='green',
        id=MonthlyIDs.SAVINGS_CARD,
    )


def _create_notif_card():
    return dbc.Card([
        html.H2('Notifications')
    ])


"""
Categories
"""
# thresholds for coloring the category progress bar
LOW_USAGE_THR = 85
HIGH_USAGE_THR = 100


def _get_accordion_control_children(title, text_weight, usage, cat_budget, progress_val,
                                    size, color, usage_pct, num_green, num_yellow, num_red):
    shared_children = _get_shared_accordion_children(title, text_weight, usage, cat_budget,
                                                     progress_val, size, color, usage_pct)
    additional_children = [
        dmc.Col(dmc.Text(f'{num_green}', color='green'), span=1),
        dmc.Col(dmc.Text(f'{num_yellow}', color='yellow'), span=1),
        dmc.Col(dmc.Text(f'{num_red}', color='red'), span=1)
    ]

    return shared_children + additional_children


def _get_shared_accordion_children(title, text_weight, usage, cat_budget, progress_val, size, color, usage_pct):
    return [
            dmc.Col(dmc.Text(f"{title}", weight=text_weight), span=2),
            dmc.Col(
                dmc.Progress(value=progress_val, label=f"{usage}/{cat_budget}",
                             size=size, color=color, id=f'{title}-progress'), span=5),
            dmc.Col(dmc.Text(f"{usage_pct}%", align="center"), span=1),
            dmc.Col(dmc.Text(f'{format_currency_num(cat_budget-usage)}'), span=1),
            dbc.Tooltip(f"{usage}/{cat_budget}", target=f'{title}-progress', placement='bottom')
        ]


def cat_content(title: str,
                usage: float,
                cat_budget: float,
                button_id: Optional[dict] = None,
                size: str = 'lg',
                text_weight=500,
                num_colors: Optional[List[int]] = None
                ):
    """

    create content for category progress line
    :param title:
    :param usage:
    :param cat_budget:
    :param button_id:
    :param size:
    :param text_weight:
    :return:
    """
    usage_pct = int(usage*100/cat_budget) if cat_budget != 0 else 0
    color = conditional_coloring(usage_pct, {
        'green': (-np.inf, LOW_USAGE_THR),
        'yellow': (LOW_USAGE_THR, HIGH_USAGE_THR),
        'red': (HIGH_USAGE_THR, np.inf)
    })
    progress_val = min(100, usage_pct)
    if num_colors is None:
        grid_children = _get_shared_accordion_children(title, text_weight, usage, cat_budget,
                                                       progress_val, size, color, usage_pct)
    else:
        grid_children = _get_accordion_control_children(title, text_weight, usage, cat_budget,
                                                        usage_pct, size, color, usage_pct, *num_colors)

    if button_id is not None:
        grid_children.append(dmc.Col(dmc.Button('View',
                                                id=button_id,
                                                color='blue',
                                                variant='light',
                                                size='sm'),
                                     span=1)
                             )

    return dmc.Grid(grid_children, gutter="xs")


def accordion_item(group_title: str,
                   group_usage: int,
                   group_budget: float,
                   cat_stats: Dict[str, Tuple[float, float]]):
    """
    :param cat_stats: dictionary of cat_name: (usage, budget)
    :return:
    """
    num_green, num_yellow, num_red = 0, 0, 0
    for usage, budget in cat_stats.values():
        if safe_divide(usage, budget)*100 < LOW_USAGE_THR:
            num_green += 1
        elif safe_divide(usage, budget)*100 < HIGH_USAGE_THR:
            num_yellow += 1
        else:
            num_red += 1

    return dmc.AccordionItem([
        dmc.AccordionControl(cat_content(group_title, group_usage, group_budget,
                                         size='xl', text_weight=700,
                                         num_colors=[num_green, num_yellow, num_red])),
        dmc.AccordionPanel([
            cat_content(title, usage, budget,
                        button_id={'type': 'drawer-btn', 'index': title})
            for title, (usage, budget) in cat_stats.items()
        ])
    ],
        value=str(np.random.randint(1000))
    )


def create_cat_usage(group: pd.core.groupby.generic.DataFrameGroupBy):
    cat_dict = {}
    for ind, row in group.iterrows():
        cat_name = row[CatDBSchema.CAT_NAME]
        budget = row[CatDBSchema.BUDGET]
        specific_month = TRANS_DB.specific_month
        usage = specific_month[
                        specific_month[TransDBSchema.CAT] == cat_name][
                                                    TransDBSchema.AMOUNT].sum()

        cat_dict[cat_name] = (int(usage), budget)
    return cat_dict


def create_accordion_items():
    accordion_items = []
    item = dmc.AccordionItem([
        dmc.AccordionControl([
            dmc.Grid([
                dmc.Col(dmc.Text(""), span=2),
                dmc.Col(dmc.Text(""), span=5),
                dmc.Col([dmc.Text('Used(%)')], span=1),
                dmc.Col([dmc.Text(f'Left({SHEKEL_SYM})')], span=1),
                dmc.Col([dmc.Text('Under 85%')], span=1),
                dmc.Col([dmc.Text('85%-100%')], span=1),
                dmc.Col([dmc.Text('Over 100%')], span=1),
            ])
        ], disabled=True, chevron=DashIconify(icon="none")),
        dmc.AccordionPanel([])
    ], value=str(np.random.randint(1000)))

    accordion_items.append(item)
    for group_name, group in CAT_DB.get_groups_as_groupby():
        group_budget = group[CatDBSchema.BUDGET].sum()
        group_usage = TRANS_DB.specific_month.get_data_by_group(group_name)[
            TransDBSchema.AMOUNT].sum()
        group_usage = int(group_usage)

        categories = create_cat_usage(group)

        accordion_items.append(accordion_item(group_name, group_usage,
                                              group_budget, categories))

    return accordion_items


def _create_layout():
    stat_headings, popovers = _create_stat_headings()
    return dbc.Container([
        html.Div(id=MonthlyIDs.DUMMY_DIV),
        dcc.Store(id=MonthlyIDs.MONTH_STORE, data=get_current_year_month(),
                  storage_type='session'),
        dcc.Location(id=MonthlyIDs.URL, refresh=True),
        *popovers,
        dbc.Row([
            dmc.Group([
               dbc.Col([create_page_heading('Monthly Budget')], width=8),
               dbc.Col(id=MonthlyIDs.MONTHLY_DD_COL, width=2)],
                position='apart'),
            ]),
        dmc.Space(h=30),
        dbc.Row([
            stat_headings
        ]),
        html.Br(),
        dbc.Row([
            html.Div(
                dmc.Drawer(id=MonthlyIDs.TRANS_DRAWER, size='70%',
                           style={'overflowY': 'auto', 'height': '100%'})
            ),
            html.Div([
                dbc.Row([
                    dmc.AccordionMultiple(
                        children=create_accordion_items())
                ], style={'margin-top': '15px'})
            ], style={'position': 'relative'}),
        ])
    ], fluid=True)


layout = _create_layout


@dash.callback(
    Output(MonthlyIDs.MONTH_STORE, 'data'),
    Output(MonthlyIDs.URL, 'href'),
    Input(MonthlyIDs.MONTHLY_DD, 'value'),
    State(MonthlyIDs.MONTH_STORE, 'data'),
)
def _change_month(dd_value, month_store):
    year, month = dd_value.split('-')
    TRANS_DB.set_specific_month(year, month)

    if month_store == dd_value:
        raise PreventUpdate

    return dd_value, '/monthly'


@dash.callback(
    Output(MonthlyIDs.MONTHLY_DD_COL, 'children'),
    Input(MonthlyIDs.DUMMY_DIV, 'n_clicks'),
    State(MonthlyIDs.MONTH_STORE, 'data'),
)
def update_month_dd(_, month_store):
    dd = _create_month_dd()
    dd.value = month_store
    return [dd]


@dash.callback(
    Output(MonthlyIDs.TRANS_DRAWER, "opened"),
    Output(MonthlyIDs.TRANS_DRAWER, "children"),
    Input({'type': "drawer-btn", 'index': ALL},  "n_clicks"),
    prevent_initial_call=True,
)
def drawer_demo(_):
    selection = ctx.triggered_id['index']
    selection_trans = TRANS_DB.specific_month.get_data_by_cat(selection)
    selection_trans = _format_table_for_drawer(selection_trans)
    table_parts = create_table(selection_trans)
    table = dmc.Table(table_parts, striped=True, highlightOnHover=True)
    return True, table


def _format_table_for_drawer(selection_trans: pd.DataFrame):
    selection_trans = format_date_col_for_display(selection_trans,
                                                  TransDBSchema.DATE)
    selection_trans[TransDBSchema.INFLOW] = selection_trans[TransDBSchema.INFLOW].astype(int)
    selection_trans[TransDBSchema.OUTFLOW] = selection_trans[TransDBSchema.OUTFLOW].astype(int)
    selection_trans[TransDBSchema.OUTFLOW] = selection_trans[TransDBSchema.OUTFLOW].astype(str) + f' {SHEKEL_SYM}'
    selection_trans[TransDBSchema.INFLOW] = selection_trans[TransDBSchema.INFLOW].astype(str) + f' {SHEKEL_SYM}'
    selection_trans = selection_trans[TransDBSchema.get_cols_for_trans_drawer()]

    return selection_trans
