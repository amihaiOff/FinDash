from pathlib import Path

from transactions_db import TransactionsDBParquet
from categories_db import CategoriesDB

from transactions_importer import import_file
from utils import SETTINGS
from dummy_data import TransGenerator, generate_catdb
from accounts import init_accounts
import dash_bootstrap_components as dbc
from dash import Dash, html
import dash


def setup_trans_db(load_type: str, cat_db: CategoriesDB):
    """

    :param load_type: options are 'dummy', 'import', 'parquet'
                     if import - will import from trans files in tmp_trans
                     if parquet - will load from parquet files from existing db
    :param cat_db:
    :return:
    """
    trans_db = TransactionsDBParquet(cat_db)

    if load_type == 'dummy':
        trans_gen = TransGenerator(60)
        transactions = trans_gen.generate()
        trans_db._db = transactions

    elif load_type == 'import':
        for file in Path('../dbs/tmp_trans').iterdir():
            trans = import_file(file, 'amihais cal', cat_db)
            trans_db.insert_data(trans)

    elif load_type == 'parquet':
        trans_db.connect(SETTINGS['db']['trans_db_path'])

    return trans_db


def setup_cat_db():
    cat_db = CategoriesDB()
    # cat_db.load_db(SETTINGS['db']['cat_db_path'])
    cat_db._db = generate_catdb()
    return cat_db


def general_setup():
    init_accounts()


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


init_accounts()
CAT_DB = setup_cat_db()

if len(list(Path('../dbs/trans_db/2022').iterdir())) > 0:
    load_type = 'parquet'
else:
    load_type = 'import'

TRANS_DB = setup_trans_db(load_type, CAT_DB)


def setup_app():
    app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], use_pages=True)
    setup_pages_container(app)
    return app


def run_frontend():
    app = setup_app()
    app.run(port=8001, debug=True)


if __name__ == "__main__":
    # general_setup()
    run_frontend()
