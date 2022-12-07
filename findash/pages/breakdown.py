import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from main import TRANS_DB, CAT_DB
from transactions_db import TransDBSchema
from element_ids import BreakdownIDs
from utils import month_num_to_str

dash.register_page(__name__)


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


def _create_dropdown_for_expenses_over_time_by_group():
    options = CAT_DB.get_group_names()
    return dcc.Dropdown(id=BreakdownIDs.EXPENSES_OVER_TIME_BY_GROUP_DD,
                        options=[{'label': option, 'value': option} for option in options],
                        value=options[0])


def _create_layout():
    return dbc.Container([
        dbc.Row([
           dbc.Col(dcc.Graph(figure=_create_under_over_card()), width=8),
           # dbc.Col(_create_income_over_time_card(), width=2)
        ]),
        dbc.Row([
            dbc.Col(dcc.Graph(figure=_expenses_over_time_by_group(
                                                CAT_DB.get_group_names()[0]),
                              id=BreakdownIDs.EXPENSES_OVER_TIME_BY_GROUP_FIG),
                    width=8),
            dbc.Col(_create_dropdown_for_expenses_over_time_by_group(), width=2)
        ])
    ], fluid=True)


layout = _create_layout


@dash.callback(
    Output(BreakdownIDs.EXPENSES_OVER_TIME_BY_GROUP_FIG, 'figure'),
    Input(BreakdownIDs.EXPENSES_OVER_TIME_BY_GROUP_DD, 'value')
)
def expenses_over_time_by_group_callback(dd_value: str):
    return _expenses_over_time_by_group(dd_value)
