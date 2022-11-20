import dash
import dash_bootstrap_components as dbc
from dash import html, dcc
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from main import TRANS_DB, CAT_DB
from transactions_db import TransDBSchema
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


def _create_income_over_time_card():
    pass


layout = dbc.Container([
    dbc.Row([
       dbc.Col(dcc.Graph(figure=_create_under_over_card()), width=8),
       # dbc.Col(_create_income_over_time_card(), width=2)
    ]),
], fluid=True)
