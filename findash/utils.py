import datetime
import uuid

import numpy as np
import pandas as pd
import yaml
from typing import Any, Dict, Tuple, Optional
from dash import html


def get_settings() -> Dict[str, Any]:
    return yaml.safe_load(open('settings.yaml'))


SETTINGS = get_settings()
SHEKEL_SYM = '₪'


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


def get_current_year_month():
    return f'{datetime.datetime.now().year}-{datetime.datetime.now().month}'


def conditional_coloring(value: float,
                         threshold_colors: Dict[str,
                                                Tuple[float, float]]) -> str:
    """
    return the text color based on the value and the threshold_colors
    :param value:
    :param threshold_colors: dict with colors as keys and tuples of (min, max)
                             as values
    :return:
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

