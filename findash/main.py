from transactions_db import TransactionsDBParquet

from frontend import run_frontend, setup_app
from utils import SETTINGS


def setup_trans_db():
    # trans_file_path = '/Users/amihaio/Documents/personal/cal_transactions/Transactions_01_04_2022_ami.csv'
    trans_db = TransactionsDBParquet()
    trans_db.connect(SETTINGS['db']['trans_db_path'])
    return trans_db


TRANS_DB = setup_trans_db()


if __name__ == "__main__":
    run_frontend()
