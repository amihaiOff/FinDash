from typing import List, Optional

import dash
import dash_mantine_components as dmc
import dash_bootstrap_components as dbc
import pandas as pd
from dash import html, dcc, Input, Output, dash_table, State, ALL, MATCH
import plotly.graph_objects as go
from dash.dash_table.Format import Format, Symbol
from dash.exceptions import PreventUpdate

from main import CAT_DB
from categories_db import CatDBSchema
from shared_elements import create_page_heading
from utils import format_currency_num, SHEKEL_SYM
from element_ids import CatIDs

dash.register_page(__name__)


class CatTableCols:
    CATEGORY = 'Category'
    BUDGET = 'Budget'


def create_cat_table(df: pd.DataFrame, for_id: Optional[str] = None):
    cat_col = {'name': CatTableCols.CATEGORY, 'id': CatTableCols.CATEGORY,
               'type': 'text', 'editable': True}
    budget_col = {'name': CatTableCols.BUDGET, 'id': CatTableCols.BUDGET,
                  'type': 'numeric', 'editable': True,
                  'format': Format(group=',').symbol(Symbol.yes).symbol_suffix(SHEKEL_SYM)}

    return dash_table.DataTable(
        id={'type': 'cat-table', 'index': for_id},
        data=df.to_dict('records'),
        columns=[cat_col, budget_col],
        style_cell={'textAlign': 'left',
                    'border-right': 'none',
                    'border-left': 'none'},
        style_header={'fontWeight': 'bold'}
    )


def _create_group_card(group_name: str,
                       group_budget: str,
                       categories: List[str],
                       categories_budgets: List[str]):
    cat_df = pd.DataFrame(dict(Category=categories,
                               Budget=categories_budgets))
    return dmc.Card([
        dmc.CardSection([
            dmc.Group([
                dmc.Text(group_name, size="md", style={'padding-left': '5px'}),
                dmc.Text(format_currency_num(group_budget), size="md", style={'padding-right': '5px'}),
            ], position='apart')
        ], withBorder=True, className="category-card-header"),
        html.Div(dmc.Table(create_cat_table(cat_df, for_id=group_name)), className='category-card')
    ], withBorder=True, shadow="md", radius="md")


def _create_category_card_grid():
    cards = []
    for group in CAT_DB.get_group_names():
        group_budget = CAT_DB.get_group_budget(group)[CatDBSchema.BUDGET].sum()
        categories = CAT_DB.get_categories_in_group(group)
        categories_budgets = [CAT_DB.get_category_budget(cat) for cat in categories]
        cards.append(dmc.Col([_create_group_card(group,
                                                 group_budget,
                                                 categories,
                                                 categories_budgets)], span=6))
    return cards


def _create_pie_chart(group_or_group_name: str):
    if group_or_group_name == 'group':
        budgets = [(name, CAT_DB.get_group_budget(name).budget.sum()) for name in CAT_DB.get_group_names()]
    else:
        budgets = [(name, CAT_DB.get_category_budget(name)) for name in
                   CAT_DB.get_categories_in_group(group_or_group_name)]

    chart = go.Pie(labels=[name for name, _ in budgets],
                   values=[budget for _, budget in budgets])

    return go.Figure(data=[chart])


def _create_category_pie_chart_col():
    groups_title = dmc.Title('Groups', align='center', className='section-title')
    graph_groups = _create_pie_chart('group')
    graph_groups_component = dcc.Graph(id=CatIDs.PIE_CHART_GROUPS, figure=graph_groups)
    cat_title = dmc.Title('Categories', style={'margin-top': '20px'}, align='center',
                          className='section-title')
    groups = CAT_DB.get_group_names()
    group_cat_dd = dcc.Dropdown(id=CatIDs.CHOOSE_GROUP, clearable=False,
                                options=groups,
                                value=groups[0],
                                style={'margin-top': '20px'})
    graph_categories = _create_pie_chart(groups[0])
    graph_categories_component = dcc.Graph(id=CatIDs.PIE_CHART_CAT, figure=graph_categories)

    return [groups_title, graph_groups_component,
            cat_title, group_cat_dd, graph_categories_component]


def _create_layout():
    return dbc.Container([
        html.Div(id=CatIDs.HIDDEN_DIV, style={'display': 'none'}),
        dbc.Row([
            create_page_heading('Spending Categories')
        ]),
        dbc.Row([
            dbc.Row([html.H1("Categories", className='section-title')]),
        ]),
        dbc.Row([
            dbc.Col([
                dmc.Grid(_create_category_card_grid(), gutter='xs')
            ], width=6, style={'max-height': '110vh', 'overflow-y': 'auto'}),
            dbc.Col(_create_category_pie_chart_col(), width=6)
        ]),
    ], fluid=True)


layout = _create_layout


@dash.callback(
    Output(CatIDs.PIE_CHART_CAT, "figure"),
    Input(CatIDs.CHOOSE_GROUP, "value"),
    config_prevent_initial_callbacks=True
)
def update_pie_chart(group_or_cat):
    return _create_pie_chart(group_or_cat)


@dash.callback(
    Output({'type': 'cat-table', 'index': MATCH}, "children"),  # this is never actually updated
    Input({'type': 'cat-table', 'index': MATCH}, "data"),
    Input({'type': 'cat-table', 'index': MATCH}, "data_previous"),
    config_prevent_initial_callbacks=True
)
def _change_cat_budget(data, data_previous):
    """
    this callback does NOT update its declared output
    """
    data = pd.DataFrame.from_records(data)
    data_previous = pd.DataFrame.from_records(data_previous)
    change_ind = data.index[data[CatTableCols.BUDGET] != data_previous[CatTableCols.BUDGET]]
    if len(change_ind) > 1:
        raise AssertionError('Only one category budget should be changed at a time')
    new_budget = data.loc[change_ind, CatTableCols.BUDGET].iloc[0]
    cat_name = data.loc[change_ind, CatTableCols.CATEGORY].iloc[0]
    CAT_DB.update_category_budget(cat_name, new_budget)
    raise PreventUpdate
