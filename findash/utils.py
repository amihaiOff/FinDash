import datetime
import uuid
from dataclasses import dataclass
from enum import Enum, auto

import numpy as np
import pandas as pd
import yaml
from typing import Any, Dict, Tuple, Optional, List
from dash import html


def get_settings() -> Dict[str, Any]:
    return yaml.safe_load(open('settings.yaml'))


SETTINGS = get_settings()
SHEKEL_SYM = '₪'


class ChangeType(Enum):
    CHANGE_DATA = auto()
    ADD_ROW = auto()
    DELETE_ROW = auto()


@dataclass
class Change:
    ROW_IND = 'row_ind'
    COL_NAME = 'col_name'
    CURRENT_VALUE = 'current_value'
    PREV_VALUE = 'prev_value'
    CHANGE_TYPE = 'change_type'

    row_ind: int
    col_name: str
    current_value: str
    prev_value: str
    change_type: ChangeType
# todo change literal strings in code with the constants above

    def __getitem__(self, item):
        attr_names = [self.ROW_IND, self.COL_NAME, self.CURRENT_VALUE,
                      self.PREV_VALUE]
        attr_vals = [self.row_ind, self.col_name, self.current_value,
                     self.prev_value]
        attr_dict = dict(zip(attr_names, attr_vals))
        val = attr_dict.get(item)
        if val is None:
            raise ValueError(f'Change object has no attribute {item}')
        return val


class MappingDict(dict):
    """
    class for using in ps.Series mapping that keeps the original value if not
    found in the mapping
    example: pd.Series(['a', 'b', 'c']).map(MappingDict({'a': 'A'}))
    """
    def __missing__(self, key):
        return key


def create_uuid():
    return uuid.uuid4().hex


def get_current_year():
    return str(datetime.datetime.now().year)


def get_current_month():
    """
    get current month in 2 digits format
    """
    month = str(datetime.datetime.now().month)
    if len(month) == 1:
        month = '0' + month
    return month


def get_current_year_month():
    """ get current year and month in one str (YYYY-MM) """
    return f'{get_current_year()}-{get_current_month()}'


def get_current_year_and_month():
    """ get current year and month in a tuple (YYYY, MM) """
    return get_current_year(), get_current_month()


def conditional_coloring(value: float,
                         threshold_colors: Dict[str,
                                                Tuple[float, float]]) -> str:
    """
    return the text color based on the value and the threshold_colors
    :param value:
    :param threshold_colors: dict with colors as keys and tuples of (min, max)
                             as values
    :return
    """
    for color, (lower, upper) in threshold_colors.items():
        if lower <= value < upper:
            return color
    raise ValueError(f'Value {value} not in any range')


def validate_date(date: str) -> bool:
    if date == '':
        return False
    sep = '-' if '-' in date else '/'
    date_parts = date.split(sep)
    if len(date_parts) < 3:
        return False

    try:
        datetime.datetime(year=int(date_parts[0]),
                          month=int(date_parts[1]),
                          day=int(date_parts[2]))
        return True

    except:
        return False


def month_num_to_str(month_num: int) -> str:
    """ convert month number to month name """
    return datetime.date(1900, month_num, 1).strftime('%B')


def format_date_col_for_display(trans_df: pd.DataFrame, date_col: datetime) \
        -> pd.DataFrame:
    """ format the date column for display """
    df_copy = trans_df.copy()
    df_copy[date_col] = df_copy[date_col].dt.strftime('%Y-%m-%d')
    return df_copy


def set_cat_col_categories(df: pd.DataFrame,
                           cat_vals: Dict[str, Any]) -> pd.DataFrame:
    """
    given a dict of col_name: cat_vals, set the categorical values of col_name
    to cat_val, in df
    :return: df with set categoricals
    """
    for col_name, cat_vals in cat_vals.items():
        df[col_name] = df[col_name].cat.set_categories(cat_vals)

    return df


def check_null(value: Any) -> bool:
    """ check if a value is null """
    if value is None:
        return True
    if isinstance(value, str) and value == '':
        return True
    if isinstance(value, float) and np.isnan(value):
        return True
    return False


def create_table(df: pd.DataFrame):
    columns, values = df.columns, df.values
    header = [html.Tr([html.Th(col) for col in columns])]
    rows = [html.Tr([html.Td(cell) for cell in row]) for row in values]
    table = [html.Thead(header), html.Tbody(rows)]
    return table


def get_change_type(df: pd.DataFrame, df_prev: pd.DataFrame):
    if len(df) > len(df_prev):
        change_type = ChangeType.ADD_ROW
    elif len(df) < len(df_prev):
        change_type = ChangeType.DELETE_ROW
    else:
        change_type = ChangeType.CHANGE_DATA
    return change_type


def detect_changes_in_table(df: pd.DataFrame,
                            df_previous: pd.DataFrame,
                            row_id_name: Optional[str] = None) \
        -> Optional[Tuple[List[Change], ChangeType]]:
    """
     Modified from: https://community.plotly.com/t/detecting-changed-cell-in-editable-datatable/26219/2
    :param df:
    :param df_previous:
    :param row_id_name:
    :return:
    """

    change_type = get_change_type(df, df_previous)
    if row_id_name is not None:
       # If using something other than the index for row id's, set it here
       for _df in [df, df_previous]:
           _df = _df.set_index(row_id_name)
    else:
       row_id_name = "index"

    # Pandas/Numpy says NaN != NaN, so we cannot simply compare the dataframes.  Instead we can either replace the
    # NaNs with some unique value (which is fastest for very small arrays, but doesn't scale well) or we can do
    # (from https://stackoverflow.com/a/19322739/5394584):
    # Mask of elements that have changed, as a dataframe.  Each element indicates True if df!=df_prev
    df_mask = ~((df == df_previous) | (
                (df != df) & (df_previous != df_previous)))

    # ...and keep only rows that include a changed value
    df_mask = df_mask.loc[df_mask.any(axis=1)]
    changes = []
    for idx, row in df_mask.iterrows():
        row_id = row.name

        # Act only on columns that had a change
        row = row[row.eq(True)]
        for change in row.iteritems():
            changes.append(
                Change(row_ind=row_id,
                       col_name=change[0],
                       current_value=df.at[row_id, change[0]],
                       prev_value=df_previous.at[row_id, change[0]],
                       change_type=change_type)
            )
            # todo when deleting\adding row the current\prev data need to be
            #   the whole deleted\added row

    return changes
