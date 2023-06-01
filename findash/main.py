import logging.config
import os
from dotenv import load_dotenv

import dash_bootstrap_components as dbc
from dash import Dash, html
import dash
import dash_mantine_components as dmc
from dash_iconify import DashIconify

from transactions_db import TransactionsDBParquet, TransDBSchema
from categories_db import CategoriesDB
from accounts import ACCOUNTS, init_accounts
import dash_auth

from file_io import Bucket, LocalIO

VALID_USERNAME_PASSWORD_PAIRS = {
    'hello': 'world'
}


def setup_logger():
    logging.config.fileConfig('../logger.ini')
    logger = logging.getLogger('Logger')
    logger.info('Logger initialized')
    return logger


logger = setup_logger()
server = None

ENV_NAME = 'stag'
load_dotenv(f'../.env.{ENV_NAME}')


def setup_trans_db(cat_db: CategoriesDB):
    """

    :param load_type: options are 'dummy', 'import', 'parquet'
                     if import - will import from trans files in tmp_trans
                     if parquet - will load from parquet files from existing db
    :param cat_db:
    :return:
    """
    trans_db = TransactionsDBParquet(file_io, cat_db, ACCOUNTS)

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
    trans_db.connect()

    return trans_db


def _create_nav_bar():
    return html.Div(
        [
            html.Div([html.H2("FinDash", style={"color": "darkgray"})],
                     className="sidebar-header",
            ),
            html.Hr(),
            dmc.NavLink(
                icon=DashIconify(icon='ic:twotone-calendar-month', width=30,
                                 color='gray'),
                label='Monthly',
                href='/monthly',
            ),
            dmc.NavLink(
                icon=DashIconify(icon='ic:outline-insert-chart-outlined', width=30,
                                 color='gray'),
                label='Breakdown',
                href='/breakdown',
            ),
            dmc.NavLink(
                icon=DashIconify(icon='ic:twotone-category', width=30,
                                 color='gray'),
                label='Categories',
                href='/categories',
            ),
            dmc.NavLink(
                icon=DashIconify(icon='material-symbols:table-rows-narrow-outline', width=30,
                                 color='gray'),
                label='Transactions',
                href='/transactions',
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

    auth = dash_auth.BasicAuth(
        app,
        VALID_USERNAME_PASSWORD_PAIRS
    )
    setup_pages_container(app)
    return app


def run_frontend():
    print('Running frontend')
    global server

    app = setup_app()
    server = app.server
    return app


def _create_file_io():
    if ENV_NAME == 'stag':
        return LocalIO(os.environ.get("DATA_PATH"))
    elif ENV_NAME == 'prod':
        return Bucket(os.environ.get("BUCKET_NAME"),
                      os.environ.get("APP_NAME"))



file_io = _create_file_io()
init_accounts(file_io)

# _validate_accounts(ACCOUNTS)
CAT_DB = CategoriesDB(file_io)
logger.info('Created cat db')


TRANS_DB = setup_trans_db(CAT_DB)
logger.info('Created trans db')
app = run_frontend()


if __name__ == "__main__":
    logger.info('Running app')
    app.run(port=8001, debug=True)
