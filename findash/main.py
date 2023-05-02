import logging.config

import dash_bootstrap_components as dbc
from dash import Dash, html
import dash
import dash_mantine_components as dmc

from transactions_db import TransactionsDBParquet, TransDBSchema
from categories_db import CategoriesDB
from utils import SETTINGS
from accounts import ACCOUNTS


def setup_logger():
    logging.config.fileConfig('logger.ini')
    logger = logging.getLogger('Logger')
    logger.info('Logger initialized')
    return logger


logger = setup_logger()


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


def _create_nav_bar():
    return html.Div(
        [
            html.Div([html.H2("FinDash", style={"color": "white"})],
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
    app.layout = dmc.NotificationsProvider(
        dbc.Container([
            _create_nav_bar(),
            html.Br(),
            html.Div(
                children=[dash.page_container],
                style={'margin-left': '5rem'}
            )
        ])
    )


def _validate_accounts(accounts):
    for account in accounts.values():
        account.validate_account(TransDBSchema.get_mandatory_col_sets())


def setup_app():
    app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP,
                                               # dbc.themes.MATERIA,
                                               # dbc.icons.FONT_AWESOME,
                                               ],
               use_pages=True, suppress_callback_exceptions=True,
               )
    setup_pages_container(app)
    return app


def run_frontend():
    app = setup_app()
    logger.info('Running app')
    app.run(port=8002, debug=True)


# _validate_accounts(ACCOUNTS)
CAT_DB = CategoriesDB()
logger.info('Created cat db')


TRANS_DB = setup_trans_db(CAT_DB)
logger.info('Created trans db')


if __name__ == "__main__":
    run_frontend()
