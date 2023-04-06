import base64
import io
from typing import List, Tuple, Union, Any, Optional

import pandas as pd
import dash
from dash import ctx, Output, Input, State, ALL
from dash.exceptions import PreventUpdate
import dash_mantine_components as dmc

from element_ids import TransIDs
from main import TRANS_DB, CAT_DB
from page_elements.transactions_layout_creators import _create_main_trans_table
from page_elements.transactions_split_window import _create_split_input_card, \
    _create_split_fail, _create_split_trans_table, _create_split_success
from transactions_db import TransDBSchema
from transactions_importer import import_file
from utils import detect_changes_in_table, Change, \
    get_add_row_change_obj, START_DATE_DEFAULT
from page_elements.transactions_layout_creators import create_trans_table


def _trans_table_callback_trigger(data: List[dict],
                                  data_prev: List[dict]) -> Tuple[bool, bool, Optional[Change]]:
    """
    logic for handling callbacks triggered by changes to trans table
    :param data:
    :param data_prev:
    :return:
    """
    to_open_modal = False
    row_del_cnf_diag = False
    data, data_prev = pd.DataFrame(data=data), pd.DataFrame(data_prev)
    changes: List[Change] = detect_changes_in_table(data, data_prev)
    if changes is None:
        return to_open_modal, row_del_cnf_diag, changes

    # remove row
    if len(data) < len(data_prev):
        row_del_cnf_diag = True
        change = changes[0]  # guaranteed only one change when deleting row
        change.prev_value = TRANS_DB.iloc[change.row_ind, :]
        return to_open_modal, row_del_cnf_diag, change

    # change data
    # todo submit changes to db
    for change in changes:
        if change['col_name'] not in TransDBSchema.get_categorical_cols():
            TRANS_DB._update_data(col_name=change.col_name, index=change.row_ind,
                                  value=change['current_value'])
        else:
            to_open_modal = change.prev_value is not None
            # if not to_open_modal:  # the change will happen after modal selection
            _apply_changes_to_trans_db_cat_col(change, all_trans=False,
                                               col=change['col_name'])

    return to_open_modal, row_del_cnf_diag, None


def _cat_change_modal_callback_trigger(data: List[dict],
                                       data_prev: List[dict]) -> None:
    """
    logic for handling callbacks triggered by changes to cat change modal
    :param data:
    :param data_prev:
    :return:
    """
    data, data_prev = pd.DataFrame(data=data), pd.DataFrame(data_prev)
    changes = detect_changes_in_table(data, data_prev)
    for change in changes:
        if ctx.triggered_id == TransIDs.MODAL_CAT_CHANGE_NO:
            all_trans = False
        elif ctx.triggered_id == TransIDs.MODAL_CAT_CHANGE_YES:
            all_trans = True
        else:
            raise ValueError("Invalid triggered id in cat change modal")
        _apply_changes_to_trans_db_cat_col(change, all_trans,
                                           col=change.col_name)


@dash.callback(
    Output(TransIDs.SPLIT_MODAL, 'opened'),
    Output(TransIDs.ADD_SPLIT_BTN, 'n_clicks'),
    Input(TransIDs.SPLIT_BTN, 'n_clicks'),
    Input(TransIDs.SPLIT_MODAL_CLOSE_BTN, 'n_clicks'),
    State(TransIDs.SPLIT_MODAL, 'opened'),
    config_prevent_initial_callbacks=True
)
def _open_split_trans_modal_callback(n_clicks_add_split, n_clicks_close, opened):
    n_clicks = 0
    return not opened, n_clicks


@dash.callback(
    Output(TransIDs.SPLITS_COL, 'children'),
    Input(TransIDs.ADD_SPLIT_BTN, 'n_clicks'),
    State(TransIDs.SPLITS_COL, 'children'),
    config_prevent_initial_callbacks=True
)
def _add_split(n_clicks, children):
    if len(children) == 9:
        raise PreventUpdate

    if n_clicks == 0:
        return [
            _create_split_input_card(1),
            dmc.Space(h=20),
            _create_split_input_card(2)]

    new_split = _create_split_input_card(n_clicks + 2)
    children.append(dmc.Space(h=20))
    children.append(new_split)
    return children


def split_amounts_eq_orig(row_amount, split_amounts):
    """ make sure the sum of split amounts equals the original transaction amount """
    split_amounts = [float(s) for s in split_amounts if s not in ['', 0]]
    split_amount = sum(split_amounts)
    return split_amount == row_amount


@dash.callback(
    Output(TransIDs.TRANS_TBL_DIV, 'children'),
    Output(TransIDs.SPLIT_TBL_DIV, 'children'),
    Output(TransIDs.SPLIT_NOTIF, 'children'),
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
        return \
            dash.no_update,\
            dash.no_update, \
            _create_split_fail("No transaction selected")

    row = TRANS_DB.iloc[selected_row_original[0]]
    row_id = row[TransDBSchema.ID]
    row_amount = row[TransDBSchema.AMOUNT]

    # validate split amounts
    if not split_amounts_eq_orig(row_amount, split_amounts):
        return dash.no_update, dash.no_update, \
            _create_split_fail(f"Split amount must equal original amount "
                               f"({row_amount})")

    new_rows = TRANS_DB.apply_split(row_id, split_amounts, split_memos,
                                    split_cats)

    table = _create_new_split_table(filtered_data, new_rows,
                                    selected_row_filtered)
    main_table = [_create_main_trans_table()]
    split_trans_table = [_create_split_trans_table(
        table=table,
        table_creation_func=create_trans_table)]
    split_success_banner = _create_split_success('Transaction '
                                                 'split successfully')

    return main_table, split_trans_table, split_success_banner


def _create_new_split_table(filtered_data: List[dict],
                            new_rows: List[pd.Series],
                            selected_row_filtered: List[int]) -> pd.DataFrame:
    """
    create new split table after appending new splits of original transaction
    :param filtered_data: data after potential filtering
    :param new_rows: new splits of original transaction
    :param selected_row_filtered: selected
    :return:
    """
    split_tbl_cols = list(filtered_data[0].keys())
    new_rows_df = pd.concat(new_rows)[split_tbl_cols]
    table = pd.DataFrame.from_records(filtered_data)
    table.date = pd.to_datetime(table.date)
    table.drop(index=selected_row_filtered[0], inplace=True)
    table = table.append(new_rows_df, ignore_index=True).sort_values(
        TransDBSchema.DATE, ascending=False)
    return table


@dash.callback(
    Output(TransIDs.TRANS_TBL, 'data'),
    Output(TransIDs.MODAL_CAT_CHANGE, 'opened'),
    Output(TransIDs.ROW_DEL_CONFIRM_DIALOG, 'displayed'),
    Output(TransIDs.CHANGE_STORE, 'data'),
    Input(TransIDs.CAT_PICKER, 'value'),
    Input(TransIDs.GROUP_PICKER, 'value'),
    Input(TransIDs.ACC_PICKER, 'value'),
    Input(TransIDs.DATE_PICKER, 'value'),
    Input(TransIDs.ADD_ROW_BTN, 'n_clicks'),
    Input(TransIDs.TRANS_TBL, "data"),
    Input(TransIDs.TRANS_TBL, "data_previous"),
    Input(TransIDs.MODAL_CAT_CHANGE_YES, 'n_clicks'),
    Input(TransIDs.MODAL_CAT_CHANGE_NO, 'n_clicks'),
    Input(TransIDs.ROW_DEL_PLACEDHOLDER, 'children'),
    State(TransIDs.MODAL_CAT_CHANGE, 'opened'),
    config_prevent_initial_callbacks=True
)
def _update_table_callback(cat: str,
                           group: str,
                           account: str,
                           date_values: List[str],
                           n_clicks: int,
                           data: list,
                           data_prev: list,
                           yes_clicks: int,
                           no_clicks: int,
                           row_del_placeholder: int,
                           opened: bool):
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
    if dash.callback_context.triggered_id == TransIDs.ADD_ROW_BTN:
        records = _add_row(n_clicks)
        return records, dash.no_update, dash.no_update, dash.no_update

    if ctx.triggered_id == TransIDs.ROW_DEL_PLACEDHOLDER:
        # this is only true when confirmed delete row
        return TRANS_DB.get_records(), dash.no_update, dash.no_update, dash.no_update

    to_open_modal = False
    row_del_cnf_diag = False

    if dash.callback_context.triggered_id in [TransIDs.CAT_PICKER,
                                              TransIDs.GROUP_PICKER,
                                              TransIDs.ACC_PICKER,
                                              TransIDs.DATE_PICKER]:

        records = _filter_table(cat, group, account, date_values)
        return records, dash.no_update, dash.no_update, dash.no_update

    elif dash.callback_context.triggered_id == TransIDs.TRANS_TBL:
        if data is None or data_prev is None:
            raise PreventUpdate
        to_open_modal, row_del_cnf_diag, change = _trans_table_callback_trigger(data, data_prev)
        if change is not None:
            # this is only true when deleting row.
            # row_del_cnf_diag is True only when changes are not None
            # so row_del_cnf_diag is redundant.
            # also we have to return records here which don't include the deleted row
            # but we don't wait for the user to confirm the deletion.
            return TRANS_DB.get_records(), False, True, change.to_json()

    elif dash.callback_context.triggered_id in [TransIDs.MODAL_CAT_CHANGE_YES,
                                                TransIDs.MODAL_CAT_CHANGE_NO]:
        _cat_change_modal_callback_trigger(data, data_prev)
    else:
        raise ValueError('Unknown trigger')

    return TRANS_DB.get_records(), to_open_modal, row_del_cnf_diag, dash.no_update


def _filter_table(cat: str,
                  group: str,
                  account: str,
                  date_values: List[str]) -> List[dict]:
    """
    Filters the table based on the chosen filters
    :return: dict of filtered df
    """
    def create_conditional_filter(col, val):
        return TRANS_DB[col] == val if val is not None else True

    def create_date_cond_filter(col, date_values: list):
        if date_values is None:
            return START_DATE_DEFAULT < TRANS_DB[col]

        start_date = pd.to_datetime(date_values[0])
        end_date = pd.to_datetime(date_values[1])
        return (start_date <= TRANS_DB[col]) & (TRANS_DB[col] <= end_date)

    cat_cond = create_conditional_filter(TransDBSchema.CAT, cat)
    account_cond = create_conditional_filter(TransDBSchema.ACCOUNT, account)
    date_cond = create_date_cond_filter(TransDBSchema.DATE, date_values)
    group_cond = create_conditional_filter(TransDBSchema.CAT_GROUP, group)

    table = TRANS_DB[(cat_cond) &
                     (group_cond) &
                     (account_cond) &
                     (date_cond)]

    TRANS_DB.set_filters({'cat': cat_cond, 'group': group_cond, 'account': account_cond, 'date': date_cond})

    return table.get_records()


def _add_row(n_clicks):
    """
    Adds a new row to the table
    :return: list of rows with new row appended
    """
    if n_clicks > 0:
        change = get_add_row_change_obj()  # todo define the change obj here
        TRANS_DB.submit_change(change)
    return TRANS_DB.get_records()


def _get_removed_row_id(df: pd.DataFrame, df_previous: pd.DataFrame):
    """
    The users added or removed a row from the trans table -> update the db
    :param df:
    :param df_previous:
    :return:
    """
    assert len(df) < len(df_previous)
    return (set(df_previous.id) - set(df.id)).pop()


def _apply_changes_to_trans_db_cat_col(change: Change,
                                       all_trans: bool,
                                       col: str):
    """
    change a categorical col in trans db. If all_trans - change
    all transactions of given payee
    :param all_trans: if True change all transactions of given payee
    :return:
    """
    if change.current_value == change.prev_value:
        return

    if change['current_value'] is None:
        # None is not a valid category
        change.current_value = ''

    if all_trans:  # todo move logic into trans_db
        payee = TRANS_DB.loc[change['row_ind'], TransDBSchema.PAYEE]
        TRANS_DB.loc[TRANS_DB[TransDBSchema.PAYEE] == payee, col]\
            = change['current_value']
        if change['col_name'] == TransDBSchema.CAT:
            CAT_DB.update_payee_to_cat_mapping(payee, cat=change['current_value'])
        uuids = TRANS_DB.loc[TRANS_DB[TransDBSchema.PAYEE] == payee,
                             TransDBSchema.ID].to_list()
        TRANS_DB.save_db_from_uuids(uuids)
    else:
        TRANS_DB.submit_change(change)
        # TRANS_DB.update_cat_col_data(col, change['index'], change['current_value'])


@dash.callback(Output(TransIDs.INSERT_FILE_SUMMARY_STORE, 'data'),
               Input(TransIDs.FILE_UPLOADER, 'contents'),
               State(TransIDs.FILE_UPLOADER, 'filename'),
               State(TransIDs.FILE_UPLOADER_DROPDOWN, 'value'),
               config_prevent_initial_callbacks=True)
def _update_output(list_of_contents: List[Any],
                   list_of_names: List[str],
                   dd_val: str):
    if dd_val is None:
        raise PreventUpdate  # todo open err modal

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
        return TRANS_DB.insert_data(trans_file)


@dash.callback(
    Output(TransIDs.INSERT_FILE_SUMMARY_MODAL, 'is_open'),
    Output(TransIDs.INSERT_FILE_SUMMARY_LABEL, 'children'),
    Input(TransIDs.INSERT_FILE_SUMMARY_STORE, 'data'),
    State(TransIDs.INSERT_FILE_SUMMARY_MODAL, 'is_open'),
    config_prevent_initial_callbacks=True
)
def _insert_file_summary_modal_callback(data: dict, is_open: bool):
    return data, not is_open


@dash.callback(
    Output(TransIDs.ROW_DEL_PLACEDHOLDER, 'children'),
    Input(TransIDs.ROW_DEL_CONFIRM_DIALOG, 'submit_n_clicks'),
    State(TransIDs.CHANGE_STORE, 'data')
)
def row_del_confirm_dialog_callback(submit_n_clicks: int, change: dict):
    if submit_n_clicks:
        TRANS_DB.submit_change(Change.from_dict(change))
        return [1]
