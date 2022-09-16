from typing import Any, Dict, Tuple


class TransCols:
    DATE = 'date'
    PAYEE = 'payee'
    SUB_CAT = 'sub_cat'
    MEMO = 'memo'
    ACCOUNT = 'account'
    INFLOW = 'inflow'
    OUTFLOW = 'outflow'
    RECONCILED = 'reconciled'
    AMOUNT = 'amount'

    @classmethod
    def get_mandatory_cols(cls) -> Tuple[str, str, str]:
        """
        madatory cols every raw transactions file must have
        """
        return cls.DATE, cls.PAYEE, cls.AMOUNT

    @classmethod
    def get_non_mandatory_cols(cls) -> Dict[str, Any]:
        """
        dictionary of non-mandatory cols (keys) to add to trans file to align with
        DB schema along with default values (values)
        """
        return {cls.SUB_CAT: '',
                cls.MEMO: '',
                cls.ACCOUNT: None,
                cls.INFLOW: 0,
                cls.OUTFLOW: 0,
                cls.RECONCILED: False}

    @classmethod
    def get_db_col_names(cls):
        return [cls.DATE, cls.PAYEE, cls.SUB_CAT, cls.MEMO, cls.ACCOUNT,
                cls.INFLOW, cls.OUTFLOW, cls.RECONCILED]


class TransactionsDBSchema:
    pass
