import base64
import datetime
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
    _create_split_fail, _create_split_trans_table, _create_split_success, \
    create_split_trans_modal
from transactions_db import TransDBSchema
from transactions_importer import import_file
from utils import detect_changes_in_table, Change, \
    get_add_row_change_obj, START_DATE_DEFAULT, ChangeType
from page_elements.transactions_layout_creators import create_trans_table


@dash.callback(
    Output(TransIDs.SPLIT_TBL_DIV, 'children', allow_duplicate=True),
    Output(TransIDs.SPLIT_MODAL, 'opened'),
    Output(TransIDs.ADD_SPLIT_BTN, 'n_clicks'),
    Input(TransIDs.SPLIT_ICON, 'n_clicks'),
    State(TransIDs.SPLIT_MODAL, 'opened'),
    # State('trans_cont', 'children'),
    config_prevent_initial_callbacks=True
)
def _open_split_trans_modal_callback(_, opened):
    n_clicks = 0
    # modal = create_split_trans_modal(create_trans_table),
    # children.append(modal)
    table = _create_split_trans_table(create_trans_table)
    return [table], not opened, n_clicks


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


def _split_amounts_eq_orig(row_amount, split_amounts):
    """ make sure the sum of split amounts equals the original transaction amount """
    split_amounts = [float(s) for s in split_amounts if s not in ['', 0]]
    split_amount = sum(split_amounts)
    return split_amount == row_amount


@dash.callback(
    Output(TransIDs.TRANS_TBL_DIV, 'children'),
    Output(TransIDs.SPLIT_TBL_DIV, 'children'),
    Output(TransIDs.SPLIT_NOTIF_DIV, 'children'),
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
    if not _split_amounts_eq_orig(row_amount, split_amounts):
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
    Output(TransIDs.TRANS_TBL, 'data', allow_duplicate=True),
    Input(TransIDs.ADD_ROW_BTN, 'n_clicks'),
    config_prevent_initial_callbacks=True
)
def _add_row_callback(n_clicks):
    change = get_add_row_change_obj()  # todo define the change obj here
    TRANS_DB.submit_change(change)
    return TRANS_DB.get_records()


@dash.callback(
    Output(TransIDs.ROW_DEL_CONFIRM_DIALOG, 'displayed'),
    Output(TransIDs.CHANGE_STORE, 'data', allow_duplicate=True),
    Input(TransIDs.TRANS_TBL, 'data'),
    Input(TransIDs.TRANS_TBL, "data_previous"),
    config_prevent_initial_callbacks=True
)
def _delete_row_callback(data, data_prev):
    if data is None or data_prev is None:
        raise PreventUpdate

    data = pd.DataFrame.from_records(data)
    data_prev = pd.DataFrame.from_records(data_prev)
    changes: List[Change] = detect_changes_in_table(data, data_prev)
    if len(changes) == 1 and changes[0].change_type == ChangeType.DELETE_ROW:
        return True, changes[0].to_json() # guaranteed only one change when deleting row
    else:
        return False, dash.no_update


@dash.callback(
    Output(TransIDs.TRANS_TBL, 'data', allow_duplicate=True),
    Input(TransIDs.ROW_DEL_CONFIRM_DIALOG, 'submit_n_clicks'),
    Input(TransIDs.ROW_DEL_CONFIRM_DIALOG, 'cancel_n_clicks'),
    State(TransIDs.CHANGE_STORE, 'data'),
    config_prevent_initial_callbacks=True
)
def row_del_confirm_dialog_callback(submit_n_clicks: int,
                                    cancel_n_clicks: int,
                                    change: dict):
    triggered_props = list(ctx.triggered_prop_ids.keys())[0]
    if 'submit_n_clicks' in triggered_props:
        TRANS_DB.submit_change(Change.from_dict(change))
        raise PreventUpdate
    elif 'cancel_n_clicks' in triggered_props:
        return TRANS_DB.get_records()
    else:
        raise ValueError('Invalid trigger id when deleting row')


@dash.callback(
    Output(TransIDs.TRANS_TBL, 'data', allow_duplicate=True),
    Input(TransIDs.TRANS_TBL, "data"),
    Input(TransIDs.TRANS_TBL, "data_previous"),
    config_prevent_initial_callbacks=True
)
def change_table_callback(data, data_prev):
    if data is None or data_prev is None:
        raise PreventUpdate

    if len(data) != len(data_prev):
        raise PreventUpdate

    data = pd.DataFrame(data)
    data_prev = pd.DataFrame(data_prev)

    if len(data.columns) != len(data_prev.columns):
        raise PreventUpdate

    changes: List[Change] = detect_changes_in_table(data, data_prev)

    for change in changes:
        TRANS_DB.submit_change(change)

    return TRANS_DB.get_records()


@dash.callback(
    Output(TransIDs.TRANS_TBL, 'data', allow_duplicate=True),
    Input(TransIDs.CAT_PICKER, 'value'),
    Input(TransIDs.GROUP_PICKER, 'value'),
    Input(TransIDs.ACC_PICKER, 'value'),
    Input(TransIDs.DATE_PICKER, 'value'),
    config_prevent_initial_callbacks=True
)
def filter_table(cat: str,
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


def _get_removed_row_id(df: pd.DataFrame, df_previous: pd.DataFrame):
    """
    The users added or removed a row from the trans table -> update the db
    :param df:
    :param df_previous:
    :return:
    """
    assert len(df) < len(df_previous)
    return (set(df_previous.id) - set(df.id)).pop()


@dash.callback(Output(TransIDs.UPLOAD_FILE_SUMMARY_LABEL, 'children'),
               Output(TransIDs.UPLOAD_FILE_SUMMARY_MODAL, 'opened'),
               Output(TransIDs.FILE_UPLOAD_MODAL, 'opened', allow_duplicate=True),
               Output(TransIDs.TRANS_TBL, 'data', allow_duplicate=True),
               Output(TransIDs.FILE_UPLOADER, 'contents'),
               Input(TransIDs.FILE_UPLOADER, 'contents'),
               State(TransIDs.FILE_UPLOADER, 'filename'),
               State(TransIDs.FILE_UPLOADER_DROPDOWN, 'value'),
               config_prevent_initial_callbacks=True)
def _upload_file_callback(list_of_contents: List[Any],
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
        insert_summary = TRANS_DB.insert_data(trans_file)
        open_upload_summary = True
        open_upload_modal = False
        uploader_contents = None  # reset it to be able to upload the same file again
        return _create_upload_summary_label(insert_summary), \
            open_upload_summary, \
            open_upload_modal, \
            TRANS_DB.get_records(), \
            uploader_contents


def _create_upload_summary_label(summary: dict):
    return dmc.Stack([
        dmc.Text(f'Inserted {summary["added"]} transactions'),
        dmc.Text(f'skipped {summary["skipped"]} transactions'),
    ])


@dash.callback(
    Output(TransIDs.FILE_UPLOAD_MODAL, 'opened'),
    Input(TransIDs.UPLOAD_FILE_ICON, 'n_clicks'),
    config_prevent_initial_callbacks=True
)
def _upload_file_modal_callback(_: int):
    return True
