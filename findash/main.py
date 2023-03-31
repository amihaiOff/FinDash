import dash_bootstrap_components as dbc
from dash import Dash, html
import dash

from transactions_db import TransactionsDBParquet, TransDBSchema
from categories_db import CategoriesDB
from utils import SETTINGS
from accounts import ACCOUNTS


def setup_trans_db(cat_db: CategoriesDB):
    """

    :param load_type: options are 'dummy', 'import', 'parquet'
                     if import - will import from trans files in tmp_trans
                     if parquet - will load from parquet files from existing db
    :param cat_db:
    :return:
    """
    trans_db = TransactionsDBParquet(cat_db, ACCOUNTS)

    # if load_type == 'dummy':
    #     trans_gen = TransGenerator(60)
    #     transactions = trans_gen.generate()
    #     trans_db._db = transactions
    #
    # elif load_type == 'import':
    #     for file in Path(f'../dbs/{SETTINGS.vault_name}/tmp_trans').iterdir():
    #         trans = import_file(file, 'amihais cal', cat_db)
    #         trans_db.insert_data(trans)
    #
    # elif load_type == 'parquet':
    trans_db.connect(SETTINGS.trans_db_path)

    return trans_db


def make_card(coin):
    change = coin["price_change_percentage_24h"]
    price = coin["current_price"]
    color = "danger" if change < 0 else "success"
    icon = "bi bi-arrow-down" if change < 0 else "bi bi-arrow-up"
    return dbc.Card(
        html.Div(
            [
                html.H4(
                    [
                        html.Img(src=coin["image"], height=35, className="me-1"),
                        coin["name"],
                    ]
                ),
                html.H4(f"${price:,}"),
                html.H5(
                    [f"{round(change, 2)}%", html.I(className=icon), " 24hr"],
                    className=f"text-{color}",
                ),
            ],
            className=f"border-{color} border-start border-5",
        ),
        className="text-center text-nowrap my-2 p-2",
    )


def _create_nav_bar():
    return html.Div(
        [
            html.Div(
                [
                    html.H2("FinDash", style={"color": "white"}),
                ],
                className="sidebar-header",
            ),
            html.Hr(),
            dbc.Nav(
                [
                    dbc.NavLink(
                        [html.I(className="fas fa-home me-2"),
                         html.Span("Monthly")],
                        href="/monthly",
                        active="exact",
                    ),
                    dbc.NavLink(
                        [
                            html.I(className="fas fa-calendar-alt me-2"),
                            html.Span("Breakdown"),
                        ],
                        href="/breakdown",
                        active="exact",
                    ),
                    dbc.NavLink(
                        [
                            html.I(className="fas fa-envelope-open-text me-2"),
                            html.Span("Transactions"),
                        ],
                        href="/transactions",
                        active="exact",
                    ),
                    dbc.NavLink([
                        html.I(className="fas fa-chart-line me-2"),
                        html.Span("Categories"),
                        ],
                        href="/categories",
                        active="exact",
                    ),
                ],
                vertical=True,
                pills=True,
            ),
        ],
        className="sidebar",
    )


def setup_pages_container(app):
    app.layout = dbc.Container([
        _create_nav_bar(),
        # dbc.NavbarSimple(brand='FinDash',
        #                  color='#b3ccf5',
        #                  links_left=True,
        #                  sticky='sticky',
        #                  style={'height': '5vh'},
        #                  children=[
        #                      dbc.NavItem(dbc.NavLink('Monthly', href='/monthly')),
        #                      dbc.NavItem(dbc.NavLink('Breakdown', href='/breakdown')),
        #                      dbc.NavItem(dbc.NavLink('Categories', href='/categories')),
        #                      dbc.NavItem(dbc.NavLink('Transactions', href='/transactions'))
        #                  ]),
        html.Br(),
        html.Div(
            children=[dash.page_container],
            style={'margin-left': '5rem'}
        )
    ])


# def _validate_accounts(accounts):
#     for account in accounts.values():
#         account.validate_account(TransDBSchema.get_mandatory_col_sets())

# _validate_accounts(ACCOUNTS)
CAT_DB = CategoriesDB()


# if list(Path(f'../dbs/{SETTINGS.vault_name}/trans_db/2022').iterdir()):
#     load_type = 'parquet'
# else:
#     load_type = 'import'

TRANS_DB = setup_trans_db(CAT_DB)


def setup_app():
    app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP,
                                               dbc.themes.MATERIA,
                                               dbc.icons.FONT_AWESOME],
               use_pages=True, suppress_callback_exceptions=True,
               )
    setup_pages_container(app)
    return app


def run_frontend():
    app = setup_app()
    app.run(port=8001, debug=True)


if __name__ == "__main__":
    run_frontend()
