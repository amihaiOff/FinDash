from accounts import CAL
from transactions_db import TransactionsDBParquet, TransDBSchema

from frontend import run_frontend
from transactions_importer import import_file
from utils import SETTINGS


def setup_trans_db():
    # trans_file_path = '/Users/amihaio/Documents/personal/cal_transactions/Transactions_19_12_2021_ami.csv'
    # trans_file = import_file(trans_file_path, account=CAL('test'))
    trans_db = TransactionsDBParquet()
    # trans_db.insert_data(trans_file)
    trans_db.connect(SETTINGS['db']['trans_db_path'])

    trans_db[TransDBSchema.DATE] = trans_db[TransDBSchema.DATE].dt.date
    return trans_db


TRANS_DB = setup_trans_db()


if __name__ == "__main__":
    run_frontend()
