import dash
import dash_bootstrap_components as dbc
import numpy as np
from dash import html, dcc, Input, Output
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from main import TRANS_DB, CAT_DB
from transactions_db import TransDBSchema
from categories_db import CatDBSchema
from element_ids import BreakdownIDs
from utils import month_num_to_str

dash.register_page(__name__)

DEFAULT_GROUP = CAT_DB.get_group_names()[0]

def update_plots():
    """
    to be called from frontend callback to update plots when data changes
    :return:
    """
    pass


def _create_under_over_card():
    trans_db = TRANS_DB.copy()
    trans_db['month'] = trans_db[TransDBSchema.DATE].dt.strftime('%b-%y')
    month_in_out = trans_db.groupby('month').agg({TransDBSchema.INFLOW: 'sum',
                                                  TransDBSchema.OUTFLOW: 'sum'})
    month_in_out['diff'] = month_in_out[TransDBSchema.INFLOW] - \
                           month_in_out[TransDBSchema.OUTFLOW]

    month_in_out = month_in_out.iloc[::-1]
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=month_in_out.index,
                         y=month_in_out[TransDBSchema.INFLOW],
                            name='Inflow'),
                  secondary_y=False)
    fig.add_trace(go.Bar(x=month_in_out.index,
                         y=month_in_out[TransDBSchema.OUTFLOW],
                         name='Outflow'),
                  secondary_y=False)
    fig.add_trace(go.Scatter(x=month_in_out.index,
                                y=month_in_out['diff'],
                                name='Difference'),
                  secondary_y=True)
    fig.update_layout(title_text='Income vs. Outflow by Month',
                      xaxis_title='Month',
                      xaxis=dict(
                          tickmode='array',
                          tickvals=list(range(len(month_in_out.index))),
                          ticktext=month_in_out.index
                      ))
    fig.update_yaxes(title_text="Amount", secondary_y=False)
    fig.update_yaxes(title_text="Difference", secondary_y=True)

    return fig


def _expenses_over_time_by_group(group: str):
    trans_db = TRANS_DB.copy()
    trans_db['month'] = trans_db[TransDBSchema.DATE].dt.strftime('%b-%y')
    trans_db = trans_db[trans_db[TransDBSchema.CAT_GROUP] == group]

    grouped = trans_db.groupby('month').agg({TransDBSchema.OUTFLOW: 'sum'})
    grouped = grouped.iloc[::-1]
    fig = px.bar(data_frame=grouped, x=grouped.index, y=TransDBSchema.OUTFLOW)
    fig.update_layout(title_text=f'Expenses by {group} over time')
    fig.update_yaxes(title_text='Amount')
    fig.update_xaxes(title_text='Month')

    return fig


def _create_groups_dd(id):
    options = CAT_DB.get_group_names()
    return dcc.Dropdown(id=id,
                        options=[{'label': option, 'value': option} for option in options],
                        value=options[0])


def _create_budget_usage(group_name: str):
    """
    create a bar chart of budget usage by category
    :param group_name:
    :return:
    """
    trans_db = TRANS_DB.copy()
    trans_db = trans_db[trans_db[TransDBSchema.CAT_GROUP] == group_name]
    grouped = trans_db.groupby(TransDBSchema.CAT,
                               observed=True).agg({TransDBSchema.OUTFLOW: 'sum'}).reset_index()
    grouped = grouped.sort_values(by=TransDBSchema.OUTFLOW, ascending=False)
    budget = CAT_DB.get_group_budget(group_name)
    final_df = budget.merge(grouped, left_on='cat_name', right_on='cat', how='left')
    final_df = final_df.fillna({'outflow': 0}).reset_index()
    final_df['pct'] = final_df.outflow * 100 / final_df.budget
    final_df['trunc_100'] = np.minimum(final_df.pct, 100)
    final_df['over_100'] = np.maximum(final_df.pct - 100, 0)

    fig = go.Figure(data=[
        go.Bar(x=final_df[CatDBSchema.CAT_NAME], y=final_df.trunc_100,
               showlegend=False),
        go.Bar(x=final_df[CatDBSchema.CAT_NAME], y=final_df.over_100,
               showlegend=False)
    ])

    fig.update_layout(title_text=f'Percent from budget: {group_name}',
                      barmode='stack')
    fig.update_yaxes(title_text='Percent from budget')
    return fig


def _create_layout():
    return dbc.Container([
        dbc.Row([
           dbc.Col(dcc.Graph(figure=_create_under_over_card()), width=10),
        ]),
        dbc.Row([
            dbc.Col(dcc.Graph(figure=_expenses_over_time_by_group(DEFAULT_GROUP),
                              id=BreakdownIDs.EXPENSES_OVER_TIME_BY_GROUP_FIG),
                    width=10),
            dbc.Col(_create_groups_dd(BreakdownIDs.EXPENSES_OVER_TIME_BY_GROUP_DD,),
                    width=2)
        ]),
        dbc.Row([
            dbc.Col(dcc.Graph(figure=_create_budget_usage(DEFAULT_GROUP),
                              id=BreakdownIDs.BUDGET_USAGE_FIG),
                    width=10),
            dbc.Col(_create_groups_dd(BreakdownIDs.BUDGET_USAGE_DD), width=2)
        ])
    ], fluid=True)


layout = _create_layout


@dash.callback(
    Output(BreakdownIDs.EXPENSES_OVER_TIME_BY_GROUP_FIG, 'figure'),
    Input(BreakdownIDs.EXPENSES_OVER_TIME_BY_GROUP_DD, 'value')
)
def expenses_over_time_by_group_callback(dd_value: str):
    return _expenses_over_time_by_group(dd_value)


@dash.callback(
    Output(BreakdownIDs.BUDGET_USAGE_FIG, 'figure'),
    Input(BreakdownIDs.BUDGET_USAGE_DD, 'value')
)
def expenses_over_time_by_group_callback(dd_value: str):
    return _create_budget_usage(dd_value)
