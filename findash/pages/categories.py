import dash
from dash import html

dash.register_page(__name__)


def _create_layout():
    return html.Div([
        html.H1('Categories'),
        html.H2('This is a page'),
        html.P('This is a page'),
    ])


layout = _create_layout
