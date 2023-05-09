import logging.config

import dash_bootstrap_components as dbc
from dash import Dash, html
import dash
import dash_mantine_components as dmc
from dash_iconify import DashIconify

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
server = None

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
    setup_pages_container(app)
    return app


def run_frontend():
    global server

    app = setup_app()
    server = app.server
    logger.info('Running app')
    app.run(port=8001, debug=True)


# _validate_accounts(ACCOUNTS)
CAT_DB = CategoriesDB()
logger.info('Created cat db')


TRANS_DB = setup_trans_db(CAT_DB)
logger.info('Created trans db')


if __name__ == "__main__":
    run_frontend()
