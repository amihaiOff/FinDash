import dash
from dash import Dash, dcc, html, dash_table
import dash_bootstrap_components as dbc


app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], use_pages=True)


app.layout = dbc.Container([
    dbc.NavbarSimple(brand='FinDash',
                     color='#b3ccf5',
                     links_left=True,
                     sticky='sticky',
                     style={'height': '5vh'},
                     children=[
                         dbc.NavItem(dbc.NavLink('Main', href='/monthly')),
                         dbc.NavItem(dbc.NavLink('Breakdown', href='/breakdown')),
                         dbc.NavItem(dbc.NavLink('Transactions', href='/transactions'))
                     ]),
    html.Br(),
    dash.page_container

])


if __name__ == '__main__':
    app.run_server(port=8001, debug=True)
