import dash
from dash import Dash, html
import dash_bootstrap_components as dbc


def setup_pages_container(app):
    app.layout = dbc.Container([
        dbc.NavbarSimple(brand='FinDash',
                         color='#b3ccf5',
                         links_left=True,
                         sticky='sticky',
                         style={'height': '5vh'},
                         children=[
                             dbc.NavItem(dbc.NavLink('Monthly', href='/monthly')),
                             dbc.NavItem(dbc.NavLink('Breakdown', href='/breakdown')),
                             dbc.NavItem(dbc.NavLink('Transactions', href='/transactions'))
                         ]),
        html.Br(),
        dash.page_container
    ])


def setup_app():
    app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], use_pages=True)
    setup_pages_container(app)
    return app


def run_frontend():
    app = setup_app()
    app.run_server(port=8001, debug=True)
