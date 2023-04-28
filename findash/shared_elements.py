from functools import partial

import dash_mantine_components as dmc
from dash import html
from dash_iconify import DashIconify


def create_page_heading(title):
    return html.H1(
        title,
        className='page-heading'
    )


def _create_split_notif(msg: str, color: str, title: str, action: str, **kwargs) -> dmc.Notification:
    return dmc.Notification(
        title=title,
        message=msg,
        color=color,
        action=action,
        **kwargs
    )


create_error_notif = partial(_create_split_notif, color='red', action='show',
                             title='Error', id='error-notif',
                             icon=DashIconify(icon="akar-icons:circle-x"))


create_split_fail = partial(_create_split_notif, color='red',
                            title='Split error', action='show',
                            id='split-fail-notif',
                            icon=DashIconify(icon="akar-icons:circle-x"))

create_split_success = partial(_create_split_notif, color='green',
                               title='Split success', action='show',
                               id='split-success-notif',
                               icon=DashIconify(icon="akar-icons:circle-check"))
