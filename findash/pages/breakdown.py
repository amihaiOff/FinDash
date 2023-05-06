import dash
import dash_bootstrap_components as dbc
import numpy as np
import pandas as pd
from dash import dcc, Input, Output
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import dash_mantine_components as dmc

from main import TRANS_DB, CAT_DB
from shared_elements import create_page_heading
from transactions_db import TransDBSchema
from categories_db import CatDBSchema
from element_ids import BreakdownIDs
from dash_bootstrap_templates import load_figure_template


dash.register_page(__name__)

load_figure_template('bootstrap')

DEFAULT_GROUP = CAT_DB.get_group_names()[0]


def sort_by_date(df: pd.DataFrame):
    df['date_numeric'] = pd.to_datetime(df.index, format='%b-%y')
    return df.sort_values('date_numeric')


def _create_under_over_card():
    trans_db = TRANS_DB.copy()
    trans_db['month'] = trans_db[TransDBSchema.DATE].dt.strftime('%b-%y')
    month_in_out = trans_db.groupby('month').agg({TransDBSchema.INFLOW: 'sum',
                                                  TransDBSchema.OUTFLOW: 'sum'})
    month_in_out['diff'] = month_in_out[TransDBSchema.INFLOW] - \
                           month_in_out[TransDBSchema.OUTFLOW]

    month_in_out = sort_by_date(month_in_out)
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
    fig.update_layout(xaxis_title='Month',
                      xaxis=dict(
                          tickmode='array',
                          tickvals=list(range(len(month_in_out.index))),
                          ticktext=month_in_out.index
                      ),
                      margin_t=10)
    fig.update_yaxes(title_text="Amount", secondary_y=False)
    fig.update_yaxes(title_text="Difference", secondary_y=True)

    return fig


def _expenses_over_time_by_group(group: str):
    trans_db = TRANS_DB.copy()
    trans_db['month'] = trans_db[TransDBSchema.DATE].dt.strftime('%b-%y')
    trans_db = trans_db[trans_db[TransDBSchema.CAT_GROUP] == group]

    grouped = trans_db.groupby('month').agg({TransDBSchema.OUTFLOW: 'sum'})
    grouped = sort_by_date(grouped)

    fig = px.bar(data_frame=grouped, x=grouped.index, y=TransDBSchema.OUTFLOW)
    fig.update_yaxes(title_text='Amount')
    fig.update_xaxes(title_text='Month')

    return fig


def _create_groups_dd(id):
    options = CAT_DB.get_group_names()
    return dmc.Select(id=id,
                        data=[{'label': option, 'value': option} for option in options],
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
    budget = CAT_DB.get_group(group_name)
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

    fig.update_layout(barmode='stack',
                      margin_t=15,
                      margin_r=5)
    fig.update_yaxes(title_text='Percent from budget')
    return fig


def _create_layout():
    return dbc.Container([
        dbc.Row([
           create_page_heading('Breakdown')
        ]),
        dbc.Row([
            dmc.Text('Income vs. Outflow by Month', className='breakdown-fig-header')
        ]),
        dbc.Row([
           dbc.Col(dcc.Graph(figure=_create_under_over_card()), width=12),
        ]),
        dbc.Row([
            dmc.Group([
                dmc.Text('', className='breakdown-fig-header',
                         id=BreakdownIDs.EXPENSES_OVER_TIME_BY_GROUP_TITLE),
                _create_groups_dd(BreakdownIDs.EXPENSES_OVER_TIME_BY_GROUP_DD)
            ], position='apart'),
            dbc.Col(dcc.Graph(figure=_expenses_over_time_by_group(DEFAULT_GROUP),
                              id=BreakdownIDs.EXPENSES_OVER_TIME_BY_GROUP_FIG),
                    width=12),
        ]),
        dbc.Row([
          dmc.Group([
              dmc.Text('', className='breakdown-fig-header',
                       id=BreakdownIDs.BUDGET_USAGE_TITLE),
              _create_groups_dd(BreakdownIDs.BUDGET_USAGE_DD)
          ], position='apart')
        ]),
        dbc.Row([
            dbc.Col(dcc.Graph(figure=_create_budget_usage(DEFAULT_GROUP),
                              id=BreakdownIDs.BUDGET_USAGE_FIG),
                    width=12),
        ])
    ], fluid=True)


layout = _create_layout


@dash.callback(
    Output(BreakdownIDs.EXPENSES_OVER_TIME_BY_GROUP_FIG, 'figure'),
    Output(BreakdownIDs.EXPENSES_OVER_TIME_BY_GROUP_TITLE, 'children'),
    Input(BreakdownIDs.EXPENSES_OVER_TIME_BY_GROUP_DD, 'value')
)
def expenses_over_time_by_group_callback(dd_value: str):
    return _expenses_over_time_by_group(dd_value), f'Expenses by {dd_value} over time'


@dash.callback(
    Output(BreakdownIDs.BUDGET_USAGE_FIG, 'figure'),
    Output(BreakdownIDs.BUDGET_USAGE_TITLE, 'children'),
    Input(BreakdownIDs.BUDGET_USAGE_DD, 'value')
)
def expenses_over_time_by_group_callback(dd_value: str):
    return _create_budget_usage(dd_value), f'Percent from budget: {dd_value}'
