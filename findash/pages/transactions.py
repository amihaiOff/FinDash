from datetime import datetime
from typing import List, Optional, Tuple, Any, Union
import base64
import io

import dash
import dash_mantine_components as dmc
import pandas as pd
from dash import State, html, dash_table, dcc, Input, Output, ctx, ALL
import dash_bootstrap_components as dbc
from dash.dash_table.Format import Format, Symbol
from dash.exceptions import PreventUpdate
from dash_iconify import DashIconify


from main import CAT_DB, TRANS_DB
from accounts import ACCOUNTS
from transactions_db import TransDBSchema
from categories_db import CatDBSchema
from element_ids import TransIDs
from utils import format_date_col_for_display, SHEKEL_SYM
from transactions_importer import import_file

# for filtering the trans table
START_DATE_DEFAULT = '1900-01-01'
END_DATE_DEFAULT = '2100-01-01'

dash.register_page(__name__)


def setup_table_cols(cols_subset: Optional[List[str]] = None) -> List[dict]:
    def setup_col_order():
        col_order = TransDBSchema.get_col_order_for_table()
        num_cols = len(cols_subset) if cols_subset else len(col_order)
        trans_df_cols = [None] * num_cols
        if cols_subset is not None:
            col_order = [col for col in col_order if col in cols_subset]

        return col_order, trans_df_cols

    col_order, trans_df_cols = setup_col_order()
    col_dtypes = TransDBSchema.get_displayed_cols_by_type()
    for col_type, cols in col_dtypes.items():
        for col in cols:
            if cols_subset is not None and col not in cols_subset:
                continue  # we want a subset of the columns

            col_def = {'name': TransDBSchema.col_display_name_mapping()[col],
                       'id': col,
                       'renamable': False,
                       'hideable': True,
                       'deletable': False}

            if col_type == 'date':
                col_def['type'] = 'datetime'

            elif col_type == 'str':
                col_def['type'] = 'text'

            elif col_type == 'numeric':
                col_def['type'] = 'numeric'
                col_def['format'] = Format(group=',').symbol(Symbol.yes).symbol_suffix(SHEKEL_SYM)

            elif col_type == 'cat':
                col_def['presentation'] = 'dropdown'

            elif col_type == 'readonly':
                col_def['editable'] = False

            else:
                raise ValueError(f'Unknown column type: {col_type}')

            # trans_df_cols.append(col_def)
            trans_df_cols[col_order.index(col)] = col_def
    return trans_df_cols

# def _create_insert_file_modal() -> dbc.Modal:
#     """
#
#     :return:
#     """
#     return dbc.Modal(
#         title='Insert Transactions',
#         id=TransIDs.INSERT_FILE_MODAL,
#         children=[
#             dmc.Text()]
#     )


def _create_category_change_modal() -> dmc.Modal:
    """
    Creates a modal for changing the category of a transaction
    :return:
    """
    return dmc.Modal(
        title="Change Category",
        id=TransIDs.MODAL_CAT_CHANGE,
        children=[
            dmc.Text(f"Would you like to apply this change to all transactions of"
                     f"this payee?"),
            dmc.Space(h=20),
            dmc.Group(
                [
                    dmc.Button("Yes",
                               id=TransIDs.MODAL_CAT_CHANGE_YES,
                               color="primary"),
                    dmc.Button("No",
                               color="red",
                               variant="outline",
                               id=TransIDs.MODAL_CAT_CHANGE_NO
                    ),
                ],
                position="right",
            ),
        ],
    )


def _create_split_input(split_num) -> dmc.Group:
    icon = dmc.Tooltip(children=[DashIconify(icon="radix-icons:question-mark-circled")],
                       label='Must be less than original transaction',
                       withArrow=True,
                       position='top'
    )
    return dmc.Group([
            dmc.TextInput(id={'type': 'split_amount',
                              'index': f'{TransIDs.SPLIT_AMOUNT}-{split_num}'},
                          placeholder='Amount',
                          type='number',
                          label=dmc.Group(['Split amount', icon],
                                          spacing=5),
                          style={'width': '20%'}),
            dmc.TextInput(id={'type': 'split_memo',
                              'index': f'{TransIDs.SPLIT_MEMO}-{split_num}'},
                          placeholder='Memo',
                          label='Add memo',
                          style={'width': '40%'}),
            dmc.Select(
                id={'type': 'split_cat',
                    'index': f'{TransIDs.SPLIT_CAT}-{split_num}'},
                label='Category',
                searchable=True,
                nothingFound="No options found",
                data=_get_group_and_cat_for_dropdown(),
                style={'width': '30%'})
    ],
        align='flex-end')


def _create_split_input_card(split_num: int):
    return dmc.Card([
        dmc.CardSection([
            dmc.Text(f'Split {split_num}', weight=500)],
            inheritPadding=True,
            py='xs',
            withBorder=True),
        _create_split_input(split_num)],
        withBorder=True,
        style={'z-index': 999, 'overflow': 'visible'},
        shadow="sm",
        radius="md",
    )


def _create_split_trans_table(records: Optional[List[dict]] = None) -> dash_table.DataTable:
    return _create_trans_table(id=TransIDs.SPLIT_TBL,
                               records=records,
                               row_selectable='single',
                               rows_deletable=False,
                               filter_action='native',
                               subset_cols=[TransDBSchema.DATE,
                                            TransDBSchema.PAYEE,
                                            TransDBSchema.AMOUNT],
                               export_format=None,
                               editable=False)


def _create_split_trans_modal():
    table = _create_split_trans_table()
    split_alert = dmc.Alert(
        'Sum of amounts in split must equal amount of original transaction',
        id=TransIDs.SPLIT_ALERT,
        color='red',
        withCloseButton=True,
        title='Split error',
        hide=True
    )
    return dmc.Modal(
        title='Split Transaction',
        id=TransIDs.SPLIT_MODAL,
        children=[
            split_alert,
            html.Div(dmc.Button(id=TransIDs.ADD_SPLIT_BTN,
                                children=['+'],
                                radius='xl',
                                size='lg',
                                compact=True),
                     style={'position': 'fixed', 'bottom': '50px', 'right': '50px'}),
            html.Div(dmc.Button(id=TransIDs.APPLY_SPLIT_BTN,
                                children=['Apply'],
                                size='md'),
                        style={'position': 'fixed', 'bottom': '50px', 'right': '550px'}
                     ),
            html.Div(dmc.Button(id=TransIDs.SPLIT_MODAL_CLOSE_BTN,
                                children=['Cancel'],
                                size='md'),
                     style={'position': 'fixed', 'bottom': '50px',
                            'right': '400px'}
                     ),
            dmc.Grid([
                dmc.Col([html.Div(table, id='split_tbl_div')],
                        style={'overflowY': 'auto'},
                        span=5),
                dmc.Col([
                    _create_split_input_card(1)
                ],
                    id=TransIDs.SPLITS_COL,
                    span=6),
            ])
        ],
        size='90%',
        overflow='inside'
    )


def _create_file_uploader():
    uploader = dcc.Upload(
        id='file_uploader',
        multiple=True,
        children=[dbc.Button('Upload File')]
    )
    acc_names = [acc_name for acc_name, _ in ACCOUNTS.items()]
    dropdown = dcc.Dropdown(id=TransIDs.FILE_UPLOADER_DROPDOWN,
                            placeholder='Select account',
                            clearable=False,
                            options=[{'label': f'{account}',
                                      'value': f'{account}'} for
                                            account in acc_names],
                            )
    return dbc.Card([
                dbc.CardHeader('Upload Transactions'),
                dropdown,
                dmc.Space(h=8),
                uploader,
                ],
            )


def _get_group_and_cat_for_dropdown():
    options = []
    for name, group in CAT_DB.get_groups_as_groupby():
        options.extend(
            [{'label': f'{name}: {cat}', 'value': f'{cat}'} for cat in
             group[CatDBSchema.CAT_NAME]])
    return options


def _setup_table_cell_dropdowns():
    account_names = [acc_name for acc_name, _ in ACCOUNTS.items()]

    dropdown_options = {
        TransDBSchema.CAT: {
            'options': _get_group_and_cat_for_dropdown(),
        },
        TransDBSchema.ACCOUNT: {
            'options': [{'label': f'{account}', 'value': f'{account}'} for
                        account in account_names]
        },
    }
    return dropdown_options


def _create_add_row_split_buttons() -> Tuple[dbc.Col, dbc.Col]:
    """
    Creates the add row and split transaction buttons
    :return:
    """
    add_row_btn = dbc.Col([dbc.Button('Add row',
                                      id=TransIDs.ADD_ROW_BTN,
                                      n_clicks=0,
                                      style=({'font-size': '14px'}))])
    split_btn = dbc.Col([dbc.Button('Split',
                                    id=TransIDs.SPLIT_BTN,
                                    style=({'font-size': '14px'}))])

    return add_row_btn, split_btn


def _create_trans_table(id: str = TransIDs.TRANS_TBL,
                        records: Optional[List[dict]] = None,
                        row_selectable: Union[str, bool, float] = False,
                        rows_deletable: bool = True,
                        filter_action: str = 'none',
                        subset_cols: Optional[List[str]] = None,
                        export_format: str = 'xlsx',
                        editable: bool = True) -> dash_table.DataTable:
    """
    Creates the transaction table
    :param row_selectable: Whether the table rows are selectable,
                           Options: 'single', 'multi', False
    :return:
    """
    trans_db_formatted = format_date_col_for_display(TRANS_DB,
                                                     TransDBSchema.DATE)
    col_defs = setup_table_cols(subset_cols)

    if subset_cols is not None:
        trans_db_formatted = trans_db_formatted[subset_cols]
        col_defs = setup_table_cols(subset_cols)

    tooltip_data = None
    if subset_cols is None or TransDBSchema.MEMO in subset_cols:
        tooltip_data = [{column: {'value': str(value), 'type': 'markdown'}
                           for column, value in row.items()} for row in
                        trans_db_formatted[TransDBSchema.MEMO].to_frame().to_dict('records')]

    data = trans_db_formatted.to_dict('records') if records is None else records
    return dash_table.DataTable(data=data,
                                id=id,
                                editable=editable,
                                filter_action=filter_action,
                                export_format=export_format,
                                export_headers='display',
                                row_selectable=row_selectable,
                                sort_by=[{'column_id': TransDBSchema.DATE,
                                          'direction': 'desc'}],
                                page_size=50,
                                row_deletable=rows_deletable,
                                fill_width=False,
                                style_table={'overflowX': 'auto'},
                                columns=col_defs,
                                dropdown=_setup_table_cell_dropdowns(),
                                style_data_conditional=[
                                    {'if': {'row_index': 'odd'},
                                        'backgroundColor': 'rgb(240, 246, 255)'},
                                    {'if': {'column_id': TransDBSchema.MEMO},
                                        'textOverflow': 'ellipsis',
                                        'maxWidth': 200,
                                        'overflow': 'hidden'},
                                    {'if': {'column_id': TransDBSchema.DATE},
                                        'color': 'gray'},
                                    {'if': {
                                        'filter_query': f'{{{TransDBSchema.SPLIT}}} is nil'},
                                        'color': 'lightblue',
                                    }
                                ],
                                tooltip_data=tooltip_data,
                                tooltip_duration=20000,
                                style_data={
                                    'border': 'none',
                                    },
                                style_cell={
                                    'textAlign': 'center',
                                    'font-family': 'sans-serif',
                                    'font-size': '12px',
                                    'padding-right': '5px',
                                    'padding-left': '5px'
                                }
                                )


def _create_main_trans_table() -> dash_table.DataTable:
    """
    Creates the main transaction table
    :return:
    """
    col_subset = [TransDBSchema.DATE, TransDBSchema.PAYEE, TransDBSchema.INFLOW,
                 TransDBSchema.OUTFLOW, TransDBSchema.CAT, TransDBSchema.MEMO,
                 TransDBSchema.ACCOUNT]
    return _create_trans_table(subset_cols=col_subset)


# insert_file_modal = _create_insert_file_modal()

category_picker = dbc.Card(
    children=[
        dbc.CardHeader('Category'),
        dcc.Dropdown(
            id=TransIDs.CAT_PICKER,
            options=CAT_DB.get_categories())
    ])

group_picker = dbc.Card([
    dbc.CardHeader('Group'),
    dcc.Dropdown(CAT_DB.get_group_names(),
                 placeholder='Select a group',
                 id=TransIDs.GROUP_PICKER)
])

account_picker = dbc.Card([
    dbc.CardHeader('Account'),
    dcc.Dropdown(
        options=TRANS_DB[TransDBSchema.ACCOUNT].unique().tolist(),
        placeholder='Select an account',
        id=TransIDs.ACC_PICKER)
])

date_picker = dbc.Card([
    dbc.CardHeader('Date Range'),
    dcc.DatePickerRange(
        id=TransIDs.DATE_PICKER,
        clearable=True,
        stay_open_on_select=False,  # doesn't work
        start_date_placeholder_text='Pick a date',
        end_date_placeholder_text='Pick a date'
    )
])


def _create_layout():
    return dbc.Container([
        cat_change_modal := _create_category_change_modal(),
        split_trans_modal := _create_split_trans_modal(),
        html.Div(id=TransIDs.PLACEDHOLDER,
                 style={'display': 'none'}),
        dbc.Row([
            dbc.Col([
                category_picker,
                html.Br(),
                group_picker,
                html.Br(),
                account_picker,
                html.Br(),
                date_picker,
                html.Br(),
                dmc.Divider(variant='dashed', size='lg'),
                dmc.Space(h=20),
                dbc.Row(_create_add_row_split_buttons()),
                dmc.Space(h=20),
                upload_file_section := _create_file_uploader(),
                # insert_file_modal
            ], width=2),
            dbc.Col([
                trans_table := _create_main_trans_table()
            ], width=10),
            dcc.Store(id=TransIDs.INSERT_FILE_SUMMARY_STORE)
        ])
])


layout = _create_layout


"""
Callbacks
"""

def _detect_changes_in_table(df: pd.DataFrame,
                             df_previous: pd.DataFrame,
                             row_id_name: Optional[str] = None) \
        -> Optional[List[dict]]:
    """
     Modified from: https://community.plotly.com/t/detecting-changed-cell-in-editable-datatable/26219/2
    :param df:
    :param df_previous:
    :param row_id_name:
    :return:
    """
    if row_id_name is not None:
       # If using something other than the index for row id's, set it here
       for _df in [df, df_previous]:
           _df = _df.set_index(row_id_name)
    else:
       row_id_name = "index"

    # todo make more efficient since we know there is only one change
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
                {
                    row_id_name: row_id,
                    "column_name": change[0],
                    "current_value": df.at[row_id, change[0]],
                    "previous_value": df_previous.at[row_id, change[0]],
                }
            )

    return changes


def _trans_table_callback_trigger(data: List[dict],
                                  data_prev: List[dict]) -> bool:
    """
    logic for handling callbacks triggered by changes to trans table
    :param data:
    :param data_prev:
    :return:
    """
    to_open_modal = False
    data, data_prev = pd.DataFrame(data=data), pd.DataFrame(data_prev)
    if len(data) != len(data_prev):
        _remove_row(data, data_prev)
        return to_open_modal

    changes = _detect_changes_in_table(data, data_prev)
    if changes is None:
        return to_open_modal

    for change in changes:
        if change['column_name'] not in TransDBSchema.get_categorical_cols():
            _apply_changes_to_trans_db_no_cat(change)
        else:
            to_open_modal = change['previous_value'] is not None
            # if not to_open_modal:  # the change will happen after modal selection
            _apply_changes_to_trans_db_cat_col(change, all_trans=False,
                                               col=change['column_name'])

    return to_open_modal


def _cat_change_modal_callback_trigger(data: List[dict],
                                       data_prev: List[dict]) -> None:
    """
    logic for handling callbacks triggered by changes to cat change modal
    :param data:
    :param data_prev:
    :return:
    """
    data, data_prev = pd.DataFrame(data=data), pd.DataFrame(data_prev)
    changes = _detect_changes_in_table(data, data_prev)
    for change in changes:
        if ctx.triggered_id == TransIDs.MODAL_CAT_CHANGE_NO:
            all_trans = False
        elif ctx.triggered_id == TransIDs.MODAL_CAT_CHANGE_YES:
            all_trans = True
        else:
            raise ValueError("Invalid triggered id in cat change modal")
        _apply_changes_to_trans_db_cat_col(change, all_trans,
                                           col=change['column_name'])


@dash.callback(
    Output(TransIDs.SPLIT_MODAL, 'opened'),
    Input(TransIDs.SPLIT_BTN, 'n_clicks'),
    Input(TransIDs.SPLIT_MODAL_CLOSE_BTN, 'n_clicks'),
    State(TransIDs.SPLIT_MODAL, 'opened'),
    config_prevent_initial_callbacks=True
)
def _open_split_trans_modal_callback(n_clicks_add_split, n_clicks_close, opened):
    return not opened


@dash.callback(
    Output(TransIDs.SPLITS_COL, 'children'),
    Input(TransIDs.ADD_SPLIT_BTN, 'n_clicks'),
    State(TransIDs.SPLITS_COL, 'children'),
    config_prevent_initial_callbacks=True
)
def _add_split(n_clicks, children):
    if len(children) == 9:
        raise PreventUpdate

    new_split = _create_split_input_card(n_clicks + 1)
    children.append(dmc.Space(h=20))
    children.append(new_split)
    return children


@dash.callback(
    Output('split_tbl_div', 'children'),
    Output(TransIDs.SPLIT_ALERT, 'hide'),
    Output(TransIDs.SPLIT_ALERT, 'children'),
    Input(TransIDs.APPLY_SPLIT_BTN, 'n_clicks'),
    State(TransIDs.SPLIT_TBL, 'derived_virtual_data'),
    State(TransIDs.SPLIT_TBL, 'derived_virtual_selected_rows'),
    State(TransIDs.SPLIT_TBL, 'selected_rows'),
    State({'type': 'split_amount', 'index': ALL}, 'value'),
    State({'type': 'split_memo', 'index': ALL}, 'value'),
    State({'type': 'split_cat', 'index': ALL}, 'value'),
    config_prevent_initial_callbacks=True
)
def _apply_splits_callback(n_clicks,
                           filtered_data: List[dict],
                           selected_row_filtered: List[int],
                           selected_row_original: List[int],
                           split_amounts: List[Union[str, float]],
                           split_memos: List[str],
                           split_cats: List[str]):
    if selected_row_original is None:
        return dash.no_update,  False, "No transaction selected"

    row = TRANS_DB.iloc[selected_row_original[0]]
    row_id = row[TransDBSchema.ID]
    row_amount = row[TransDBSchema.AMOUNT]

    split_amounts = [float(s) for s in split_amounts if s != '' and s != 0]
    split_amount = sum(split_amounts)
    if split_amount != row_amount:
        return dash.no_update, False, \
            f"Split amount must equal original amount ({row_amount})"

    new_rows = TRANS_DB.apply_split(row_id, split_amounts, split_memos,
                                    split_cats)

    # update split tbl
    split_tbl_cols = list(filtered_data[0].keys())
    records = pd.concat(new_rows)[split_tbl_cols].to_dict('records')
    for rec in records:
        filtered_data.insert(selected_row_filtered[0], rec)
    return [_create_split_trans_table(records=filtered_data)], True, ''

    # todo update TRANS_TBL and SPLIT_TBL
    #   split_tbl - works, need to remove original row and format the new rows (make sure that the table
    #      is not too convoluted)
    #   trans_tbl - have the table inside a div and a callback that updates the div
    #       with a new table. the callback will be triggered by an invisible component that will get the
    #      new table data as an input. the callback will be the only place where the div is updated.

@dash.callback(
    Output(TransIDs.TRANS_TBL, 'data'),
    Output(TransIDs.MODAL_CAT_CHANGE, 'opened'),
    Input(TransIDs.CAT_PICKER, 'value'),
    Input(TransIDs.GROUP_PICKER, 'value'),
    Input(TransIDs.ACC_PICKER, 'value'),
    Input(TransIDs.DATE_PICKER, 'start_date'),
    Input(TransIDs.DATE_PICKER, 'end_date'),
    Input(TransIDs.ADD_ROW_BTN, 'n_clicks'),
    State(TransIDs.TRANS_TBL, 'data'),
    State(TransIDs.TRANS_TBL, 'columns'),
    Input(TransIDs.TRANS_TBL, "data"),
    Input(TransIDs.TRANS_TBL, "data_previous"),
    Input(TransIDs.MODAL_CAT_CHANGE_YES, 'n_clicks'),
    Input(TransIDs.MODAL_CAT_CHANGE_NO, 'n_clicks'),
    State(TransIDs.MODAL_CAT_CHANGE, 'opened'),
    config_prevent_initial_callbacks=True
)
def _update_table_callback(cat: str,
                           group: str,
                           account: str,
                           start_date: str,
                           end_date: str,
                           n_clicks: int,
                           rows: list,
                           columns: list,
                           data: list,
                           data_prev: list,
                           yes_clicks: int,
                           no_clicks: int,
                           opened: bool) -> Tuple[list, bool]:
    """
    This is the main callback for updating the table since each id can only
    have one callback that uses it as output. This function calls helper
    functions based on the triggering element
    :param cat: chosen category in filter dropdown
    :param account: chosen account in filter dropdown
    :param start_date: chosen start date in filter date picker
    :param end_date: chosen end date in filter date picker
    :param n_clicks: property of add row button
    :param rows: rows list of table to append a new row to
    :param columns: columns list of table to provide values for new row
    :param data: current data in trans table
    :param data_prev: previous data in trans table
    :param yes_clicks: property of yes button in change cat modal
    :param no_clicks: property of no button in change cat modal
    :param opened: property of change cat modal - if it is opened
    :return: changes to table data and if the change cat modal should be opened
    """
    to_open_modal = False
    if dash.callback_context.triggered_id == TransIDs.ADD_ROW_BTN:
        return _add_row(n_clicks, rows, columns), to_open_modal

    elif dash.callback_context.triggered_id in [TransIDs.CAT_PICKER,
                                                TransIDs.GROUP_PICKER,
                                                TransIDs.ACC_PICKER,
                                                TransIDs.DATE_PICKER,
                                                TransIDs.DATE_PICKER]:
        return _filter_table(cat, group, account, start_date, end_date), \
               to_open_modal

    elif dash.callback_context.triggered_id == TransIDs.TRANS_TBL:
        to_open_modal = _trans_table_callback_trigger(data, data_prev)

    elif dash.callback_context.triggered_id in [TransIDs.MODAL_CAT_CHANGE_YES,
                                                TransIDs.MODAL_CAT_CHANGE_NO]:
        _cat_change_modal_callback_trigger(data, data_prev)
    else:
        raise ValueError('Unknown trigger')

    return TRANS_DB.get_records(), to_open_modal


def _filter_table(cat: str,
                  group: str,
                  account: str,
                  start_date: str, end_date: str):
    """
    Filters the table based on the chosen filters
    :return: dict of filtered df
    """
    def create_conditional_filter(col, val):
        return TRANS_DB[col] == val if val is not None else True

    def create_date_cond_filter(col, start_date, end_date):
        # todo raise error when start_date > end_date
        start_date = pd.to_datetime(
            start_date) if start_date is not None else pd.to_datetime(
            START_DATE_DEFAULT)
        end_date = pd.to_datetime(
            end_date) if end_date is not None else pd.to_datetime(
            END_DATE_DEFAULT)
        return (start_date <= TRANS_DB[col]) & (TRANS_DB[col] <= end_date)

    cat_cond = create_conditional_filter(TransDBSchema.CAT, cat)
    account_cond = create_conditional_filter(TransDBSchema.ACCOUNT, account)
    date_cond = create_date_cond_filter(TransDBSchema.DATE, start_date,
                                        end_date)
    group_cond = create_conditional_filter(TransDBSchema.CAT_GROUP, group)

    table = TRANS_DB[(cat_cond) &
                     (group_cond) &
                     (account_cond) &
                     (date_cond)]

    return table.get_records()


def _add_row(n_clicks, rows, columns):
    """
    Adds a new row to the table
    :return: list of rows with new row appended
    """
    if n_clicks > 0:
        new_row = {col['id']: None for col in columns}
        date = datetime.now().strftime('%Y-%m-%d')
        new_row['date'] = date
        rows.insert(0, new_row)
        TRANS_DB.add_new_row(date)
    return rows


def _remove_row(df: pd.DataFrame, df_previous: pd.DataFrame):
    """
    The users added or removed a row from the trans table -> update the db
    :param df:
    :param df_previous:
    :return:
    """
    assert len(df) < len(df_previous)
    removed_id = (set(df_previous.id) - set(df.id)).pop()
    TRANS_DB.remove_row_with_id(removed_id)


def _apply_changes_to_trans_db_no_cat(change: dict):
    """
    given a dict of changes the user made in trans table. apply them to trans
    db
    :param change: dict with keys: index, column_name, previous_value,
                                    current_value
    :return:
    """
    # todo - is this func needed?
    ind, col_name = change['index'], change['column_name']
    # prev_val = change['previous_value']
    # db_val = TRANS_DB[col_name].iloc[ind]
    # if col_name == TransDBSchema.DATE:
    #     db_val = str(db_val.date())
    # db_val = None if pd.isna(db_val) else db_val
    # if db_val != prev_val:
    #     raise ValueError('mismatch between prev_value and db value when'
    #                      'trying to apply changes')

    TRANS_DB.update_data(col_name=col_name, index=ind,
                         value=change['current_value'])


def _apply_changes_to_trans_db_cat_col(change: dict, all_trans: bool,
                                       col: str):
    """
    change a categorical col in trans db. If all_trans - change
    all transactions of given payee
    :param all_trans: if True change all transactions of given payee
    :return:
    """
    if change['current_value'] == change['previous_value']:
        return

    if change['current_value'] is None:
        # None is not a valid category
        change['current_value'] = ''

    if all_trans:
        payee = TRANS_DB.loc[change['index'], TransDBSchema.PAYEE]
        TRANS_DB.loc[TRANS_DB[TransDBSchema.PAYEE] == payee, col]\
            = change['current_value']
        if change['column_name'] == TransDBSchema.CAT:
            CAT_DB.update_payee_to_cat_mapping(payee, cat=change['current_value'])
        uuids = TRANS_DB.loc[TRANS_DB[TransDBSchema.PAYEE] == payee,
                             TransDBSchema.ID].to_list()
        TRANS_DB.save_db_from_uuids(uuids)
    else:
        TRANS_DB.update_cat_col_data(col, change['index'], change['current_value'])


@dash.callback(Output(TransIDs.INSERT_FILE_SUMMARY_STORE, 'data'),
               Input(TransIDs.FILE_UPLOADER, 'contents'),
               State(TransIDs.FILE_UPLOADER, 'filename'),
               State(TransIDs.FILE_UPLOADER_DROPDOWN, 'value'),
               config_prevent_initial_callbacks=True)
def _update_output(list_of_contents: List[Any],
                   list_of_names: List[str],
                   dd_val: str):
    if dd_val is None:
        return None  # todo open err modal

    for file, f_name in zip(list_of_contents, list_of_names):
        content_type, content_string = file.split(',')
        decoded = base64.b64decode(content_string)
        if f_name.endswith('csv'):
            file = io.StringIO(decoded.decode('utf-8'))
        elif f_name.endswith('xlsx') or f_name.endswith('xls'):
            file = io.BytesIO(decoded)
        else:
            raise ValueError(f'Unknown file type {f_name} for import')

        trans_file = import_file(file, account_name=dd_val, cat_db=CAT_DB)
        insert_summary = TRANS_DB.insert_data(trans_file)
        return insert_summary
