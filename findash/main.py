from accounts import CAL
from transactions_db import TransactionsDBParquet, TransDBSchema
from categories_db import CategoriesDB

from frontend import run_frontend
from transactions_importer import import_file
from utils import SETTINGS
from dummy_data import TransGenerator, generate_catdb
from accounts import init_accounts


def setup_trans_db(cat_db: CategoriesDB):
    trans_db = TransactionsDBParquet(cat_db)
    # trans_db.connect(SETTINGS['db']['trans_db_path'])
    trans_gen = TransGenerator(60)
    transactions = trans_gen.generate()
    trans_db._db = transactions

    # trans_db[TransDBSchema.DATE] = trans_db[TransDBSchema.DATE].dt.strftime('%Y-%m-%d')
    return trans_db


def setup_cat_db():
    cat_db = CategoriesDB()
    # cat_db.load_db(SETTINGS['db']['cat_db_path'])
    cat_db._db = generate_catdb()
    return cat_db


def general_setup():
    init_accounts()


CAT_DB = setup_cat_db()
TRANS_DB = setup_trans_db(CAT_DB)

if __name__ == "__main__":
    general_setup()
    run_frontend()
