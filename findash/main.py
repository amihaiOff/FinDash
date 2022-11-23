from pathlib import Path

from accounts import CAL
from transactions_db import TransactionsDBParquet, TransDBSchema
from categories_db import CategoriesDB

from frontend import run_frontend
from transactions_importer import import_file
from utils import SETTINGS
from dummy_data import TransGenerator, generate_catdb
from accounts import init_accounts


def setup_trans_db(load_type: str, cat_db: CategoriesDB):
    """

    :param trans_db: options are 'dummy', 'import', 'parquet'
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
            trans = import_file(file, CAL('amihai'))
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


CAT_DB = setup_cat_db()
load_type = 'import'
TRANS_DB = setup_trans_db(load_type, CAT_DB)

if __name__ == "__main__":
    general_setup()
    run_frontend()
