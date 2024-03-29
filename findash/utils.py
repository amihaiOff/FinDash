import datetime
import uuid
from dataclasses import dataclass
from enum import Enum

import numpy as np
import pandas as pd
from typing import Any, Dict, Tuple, Optional, List, Union
from dash import html


SHEKEL_SYM = '₪'
START_DATE_DEFAULT = pd.to_datetime('1900-01-01')
END_DATE_DEFAULT = pd.to_datetime('2100-01-01')



class ChangeType(Enum):
    CHANGE_DATA = 'change_data'
    ADD_ROW = 'add_row'
    DELETE_ROW = 'delete_row'

    def __str__(self):
        return self.value


@dataclass
class Change:
    ROW_IND = 'row_ind'
    TRANS_ID = 'trans_id'
    COL_NAME = 'col_name'
    CURRENT_VALUE = 'current_value'
    PREV_VALUE = 'prev_value'
    CHANGE_TYPE = 'change_type'

    row_ind: Optional[int]
    trans_id: Optional[str]
    col_name: Optional[str]
    current_value: Optional[str]
    prev_value: Optional[str]
    change_type: ChangeType

    def __getitem__(self, item):
        attr_names = [self.ROW_IND, self.COL_NAME, self.CURRENT_VALUE,
                      self.PREV_VALUE, self.TRANS_ID]
        attr_vals = [self.row_ind, self.col_name, self.current_value,
                     self.prev_value, self.trans_id]
        attr_dict = dict(zip(attr_names, attr_vals))
        val = attr_dict.get(item, 'null')  # cannot use None since this might be the value of the field
        if val == 'null':
            raise ValueError(f'Change object has no attribute {item}')
        return val

    def to_json(self):
        curr_val = self.current_value.to_json() if isinstance(self.current_value, pd.Series) else self.current_value
        prev_val = self.prev_value.to_json() if isinstance(self.prev_value, pd.Series) else self.current_value
        return {
            self.ROW_IND: self.row_ind,
            self.COL_NAME: self.col_name,
            self.CHANGE_TYPE: str(self.change_type),
            self.CURRENT_VALUE: curr_val,
            self.PREV_VALUE: prev_val,
            self.TRANS_ID: self.trans_id
        }

    @classmethod
    def from_dict(cls, change_dict: dict):
        curr_val, prev_val = change_dict[cls.CURRENT_VALUE], change_dict[cls.PREV_VALUE]
        curr_val = (
            pd.Series(curr_val)
            if isinstance(curr_val, dict)
            else change_dict[cls.CURRENT_VALUE]
        )
        prev_val = (
            pd.Series(prev_val)
            if isinstance(prev_val, dict)
            else change_dict[cls.PREV_VALUE]
        )
        return cls(
            row_ind=change_dict[cls.ROW_IND],
            col_name=change_dict[cls.COL_NAME],
            change_type=ChangeType(change_dict[cls.CHANGE_TYPE]),
            prev_value=prev_val,
            current_value=curr_val,
            trans_id=change_dict[cls.TRANS_ID]
        )


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


def format_date_col_for_display(trans_df: pd.DataFrame, date_col: str) \
        -> pd.DataFrame:
    """ format the date column for display. Creates a copy of the df for display """
    df_copy = trans_df.copy()
    df_copy[date_col] = df_copy[date_col].dt.strftime('%Y-%m-%d')
    return df_copy


def check_null(value: Any) -> bool:
    """ check if a value is null """
    if value is None:
        return True
    if isinstance(value, str) and value == '':
        return True
    return bool(isinstance(value, float) and np.isnan(value))


def create_table(df: pd.DataFrame):
    columns, values = df.columns, df.values
    header = [html.Tr([html.Th(col) for col in columns])]
    rows = [html.Tr([html.Td(cell) for cell in row]) for row in values]
    table = [html.Thead(header), html.Tbody(rows)]
    return table


# def create_cat_table(df: pd.DataFrame, for_id: Optional[str] = None):
#     cat_col = {'name': 'Category', 'id': 'Category', 'type': 'text', 'editable': True}
#     budget_col = {'name': 'Budget', 'id': 'Budget', 'type': 'numeric', 'editable': True,
#                   'format': Format(group=',').symbol(Symbol.yes).symbol_suffix(SHEKEL_SYM)}
#
#     return dash_table.DataTable(
#         id={'type': 'cat-table', 'index': for_id},
#         data=df.to_dict('records'),
#         columns=[cat_col, budget_col],
#         style_cell={'textAlign': 'left',
#                     'border-right': 'none',
#                     'border-left': 'none'},
#         style_header={'fontWeight': 'bold'}
#     )


def get_change_type(df: pd.DataFrame, df_prev: pd.DataFrame):
    if len(df) > len(df_prev):
        return ChangeType.ADD_ROW
    elif len(df) < len(df_prev):
        return ChangeType.DELETE_ROW
    else:
        return ChangeType.CHANGE_DATA


def get_add_row_change_obj():
    return Change(
            row_ind=None,
            col_name=None,
            prev_value=None,
            current_value=None,
            change_type=ChangeType.ADD_ROW,
            trans_id=None
        )


def _get_removed_row(df: pd.DataFrame, df_prev: pd.DataFrame):
    m = df_prev.merge(df.drop_duplicates(), on=list(df.columns), how='left',
                      indicator=True)
    left_only = m['_merge'] == 'left_only'
    if left_only.sum() == 0:
        if df.duplicated().sum() < df_prev.duplicated().sum():
            return df_prev[df_prev.duplicated()].iloc[0]
        else:
            raise ValueError('Removed row undetected')
    elif left_only.sum() > 1:
        raise ValueError('More than one row detected as removed')
    return df_prev[left_only].iloc[0]  # using iloc to get back a series


def detect_changes_in_table(df: pd.DataFrame,
                            df_previous: pd.DataFrame,
                            ) -> Optional[List[Change]]:
    """
     Modified from: https://community.plotly.com/t/detecting-changed-cell-in-editable-datatable/26219/2
    :param df:
    :param df_previous:
    :param row_id_name:
    :return:
    """
    if len(df.columns) != len(df_previous.columns):
        """
        This case is when deleting a row and not confirming the deletion, so the
        the new data is the records from the TRANS_TBL (which has the deleted row we 
        want to put back) which includes all the columns and not just the visible ones. 
        In this case we know we don't want to change anything
        """
        return []

    change_type = get_change_type(df, df_previous)
    if change_type == ChangeType.ADD_ROW:
        return [get_add_row_change_obj()]

    if change_type == ChangeType.DELETE_ROW:
        removed_row = _get_removed_row(df, df_previous)
        return [Change(
            row_ind=removed_row.name,
            trans_id=removed_row['id'],
            col_name=None,
            current_value=None,
            prev_value=removed_row,
            change_type=change_type
        )]

    # if row_id_name is not None:
    #    # If using something other than the index for row id's, set it here
    #    for _df in [df, df_previous]:
    #        _df = _df.set_index(row_id_name)
    # else:
    #    row_id_name = "index"

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
                       change_type=change_type,
                       trans_id=df.at[row_id, 'id']
                       # we can use row index here since it is one to one with what's on screen
                       )
            )

    return changes


def format_currency_num(num: Union[int, float, str]):
    return f'{num:,.0f}{SHEKEL_SYM}'


def safe_divide(numerator, denominator):
    return 0 if denominator == 0 else numerator / denominator
