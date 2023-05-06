from typing import List, Optional

import dash
import dash_mantine_components as dmc
import dash_bootstrap_components as dbc
import pandas as pd
from dash import html, dcc, Input, Output, dash_table, State, ALL, MATCH, ctx
import plotly.graph_objects as go
from dash.dash_table.Format import Format, Symbol
from dash.exceptions import PreventUpdate
from dash_iconify import DashIconify

from main import CAT_DB
from categories_db import CatDBSchema
from shared_elements import create_page_heading
from utils import format_currency_num, SHEKEL_SYM
from element_ids import CatIDs

dash.register_page(__name__)


class CatTableSchema:
    CATEGORY = 'Category'
    BUDGET = 'Budget'

    @classmethod
    def get_new_row(cls):
        return {cls.CATEGORY: CAT_DB.get_new_category_name(),
                cls.BUDGET: 0}


def create_cat_table(df: pd.DataFrame, group_name: str, index: int):
    cat_col = {'name': CatTableSchema.CATEGORY, 'id': CatTableSchema.CATEGORY,
               'type': 'text', 'editable': True}
    budget_col = {'name': CatTableSchema.BUDGET, 'id': CatTableSchema.BUDGET,
                  'type': 'numeric', 'editable': True,
                  'format': Format(group=',').symbol(Symbol.yes).symbol_suffix(SHEKEL_SYM)}

    return dash_table.DataTable(
        id={'type': 'cat-table', 'index': index, 'group_name': group_name},
        data=df.to_dict('records'),
        row_deletable=True,
        columns=[cat_col, budget_col],
        style_cell={'textAlign': 'left',
                    'border-right': 'none',
                    'border-left': 'none'},
        style_header={'fontWeight': 'bold',
                      'border-top': 'none'}
    )


def _create_group_card(group_name: str,
                       group_budget: str,
                       categories: List[str],
                       categories_budgets: List[str],
                       index: int):
    cat_df = pd.DataFrame(dict(Category=categories,
                               Budget=categories_budgets))
    return dmc.Card([
        dmc.CardSection([
            dmc.Group([
                dmc.Text(group_name, size="md", style={'padding-left': '5px'}),
                dmc.Text(format_currency_num(group_budget), size="md", style={'padding-right': '5px'},
                         id={'type': 'group-budget', 'group_name': group_name, 'index': index})
            ], position='apart')
        ], withBorder=True, className="category-card-header"),
        html.Div(dmc.Table(create_cat_table(cat_df, group_name=group_name, index=index)),
                 className='category-card'),
        dmc.CardSection([
            dmc.Group([
                dmc.ActionIcon(DashIconify(icon='mdi:delete-forever-outline',
                                           className='delete-group', width=20),
                               id={'type': 'delete-group', 'group_name': group_name, 'index': index},
                               size='lg'),
                dmc.ActionIcon(DashIconify(icon='mdi:plus', width=20),
                               id={'type': 'add-category', 'group_name': group_name, 'index': index},
                               size='lg')
            ], position='apart')
        ])
    ], withBorder=True, shadow="md", radius="md")


def _create_category_card_grid():
    cards = []
    for i, group in enumerate(CAT_DB.get_group_names()):
        group_budget = CAT_DB.get_group_budget(group)
        categories = CAT_DB.get_categories_in_group(group)
        categories_budgets = [CAT_DB.get_category_budget(cat) for cat in categories]
        cards.append(dmc.Col([_create_group_card(group,
                                                 group_budget,
                                                 categories,
                                                 categories_budgets,
                                                 index=i)], span=6))
    return cards


def _create_pie_chart(group_or_group_name: str, id: str):
    if group_or_group_name == 'group':
        budgets = [(name, CAT_DB.get_group_budget(name)) for name in CAT_DB.get_group_names()]
    else:
        budgets = [(name, CAT_DB.get_category_budget(name)) for name in
                   CAT_DB.get_categories_in_group(group_or_group_name)]

    chart = go.Pie(labels=[name for name, _ in budgets],
                   values=[budget for _, budget in budgets])

    return dcc.Graph(figure=go.Figure(data=[chart]), id=id)


def _create_category_pie_chart_col():
    groups_title = dmc.Title('Groups', align='center', className='section-title')
    graph_groups_component = html.Div([_create_pie_chart('group', CatIDs.PIE_CHART_GROUPS)],
                                      id='group_pie_div')
    cat_title = dmc.Title('Categories', style={'margin-top': '20px'}, align='center',
                          className='section-title')
    groups = CAT_DB.get_group_names()
    group_cat_dd = dcc.Dropdown(id=CatIDs.CHOOSE_GROUP, clearable=False,
                                options=groups,
                                value=groups[0],
                                style={'margin-top': '20px'})
    graph_categories_component = html.Div([_create_pie_chart(groups[0], CatIDs.PIE_CHART_CAT)],
                                          id='cat_pie_div')

    return [groups_title, graph_groups_component,
            cat_title, group_cat_dd, graph_categories_component]


def _create_layout():
    return dbc.Container([
        dcc.Store(id=CatIDs.CAT_CHANGE_BUDGET_STORE),
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
    Output('cat_pie_div', "children"),
    Input(CatIDs.CHOOSE_GROUP, "value"),
    config_prevent_initial_callbacks=True
)
def update_pie_chart(group_or_cat):
    return _create_pie_chart(group_or_cat, CatIDs.PIE_CHART_CAT)


@dash.callback(
    Output({'type': 'group-budget', 'group_name': ALL, 'index': ALL}, "children"),
    Input(CatIDs.CAT_CHANGE_BUDGET_STORE, "data"),
    State({'type': 'group-budget', 'group_name': ALL, 'index': ALL}, 'children'),
    config_prevent_initial_callbacks=True
)
def update_group_budget(group_name_and_ind, children):
    group_name = group_name_and_ind['group_name']
    ind = group_name_and_ind['index']
    updated_sum = format_currency_num(CAT_DB.get_group_budget(group_name))
    children[ind] = updated_sum
    return children


@dash.callback(
    Output('group_pie_div', 'children'),
    Output(CatIDs.CAT_CHANGE_BUDGET_STORE, "data"),
    Input({'type': 'cat-table', 'group_name': ALL, 'index': ALL}, "data"),
    Input({'type': 'cat-table', 'group_name': ALL, 'index': ALL}, "data_previous"),
    config_prevent_initial_callbacks=True
)
def _update_group_table(data, data_previous):
    """
    adding category logic does not run thru this callback since the data_previous
    is not updated when data is changed via callback
    """
    changed_ind = ctx.triggered_id.index
    changed_group_name = ctx.triggered_id['group_name']

    if data_previous[changed_ind] is None or \
            len(data[changed_ind]) > len(data_previous[changed_ind]):
        # when adding a new category, the data_previous is not updated so
        # it is either None or, if there was a different change before adding
        # the row, the length is greater than the new data, and we don't deal
        # with new categories in this callback
        raise PreventUpdate

    data = pd.DataFrame.from_records(data[changed_ind])
    data_previous = pd.DataFrame.from_records(data_previous[changed_ind])

    if len(data) < len(data_previous):  # delete category
        deleted_idx = data_previous.loc[~data_previous[CatTableSchema.CATEGORY].isin(data[CatTableSchema.CATEGORY])].index
        CAT_DB.delete_category(data_previous.loc[deleted_idx, CatTableSchema.CATEGORY].iloc[0])

        fig = _create_pie_chart('group', CatIDs.PIE_CHART_GROUPS)
        return [fig], dict(group_name=changed_group_name, index=changed_ind)

    changed_name_idx = data.index[data[CatTableSchema.CATEGORY] !=
                                  data_previous[CatTableSchema.CATEGORY]]
    changed_budget_idx = data.index[data[CatTableSchema.BUDGET] !=
                                    data_previous[CatTableSchema.BUDGET]]
    if len(changed_budget_idx) > 1 or len(changed_name_idx) > 1:
        raise ValueError('Only one category can be changed at a time')

    if len(changed_name_idx) == 1:
        CAT_DB.update_category_name(
            data_previous.loc[changed_name_idx, CatTableSchema.CATEGORY].iloc[0],
            data.loc[changed_name_idx, CatTableSchema.CATEGORY].iloc[0])

        fig = _create_pie_chart('group', CatIDs.PIE_CHART_GROUPS)
        return fig, dash.no_update

    if len(changed_budget_idx) == 1:
        new_budget = data.loc[changed_budget_idx, CatTableSchema.BUDGET].iloc[0]
        cat_name = data.loc[changed_budget_idx, CatTableSchema.CATEGORY].iloc[0]
        CAT_DB.update_category_budget(cat_name, new_budget)

        fig = _create_pie_chart('group', CatIDs.PIE_CHART_GROUPS)
        return [fig], dict(group_name=changed_group_name, index=changed_ind)


@dash.callback(
    Output({'type': 'cat-table', 'group_name': MATCH, 'index': MATCH}, "data"),
    Input({'type': 'add-category', 'group_name': MATCH, 'index': MATCH}, "n_clicks"),
    State({'type': 'cat-table', 'group_name': MATCH, 'index': MATCH}, "data"),
    config_prevent_initial_callbacks=True
)
def _add_category(_, datas):
    changed_group_name = ctx.triggered_id['group_name']
    CAT_DB.add_category(changed_group_name)
    datas.append(CatTableSchema.get_new_row())
    return datas
