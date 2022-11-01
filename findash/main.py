from transactions_db import TransactionsDBParquet
from categories import CategoriesDB
from transactions_importer import import_file
from accounts import CAL


def main():
    trans_file_path = '/Users/amihaio/Documents/personal/cal_transactions/Transactions_01_04_2022_ami.csv'
    trans_file = import_file(trans_file_path, account=CAL('test'))
    trans_db = TransactionsDBParquet()
    trans_db.insert_data(trans_file)


if __name__ == "__main__":
    main()
