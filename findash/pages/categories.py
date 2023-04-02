from typing import List

import dash
import dash_mantine_components as dmc
import dash_bootstrap_components as dbc
import pandas as pd
from dash import html
from dash_iconify import DashIconify

from main import CAT_DB
from categories_db import CatDBSchema
from utils import create_table

dash.register_page(__name__)


def _create_group_card(group_name: str,
                       group_budget: str,
                       categories: List[str],
                       categories_budgets: List[str]):
    cat_df = pd.DataFrame(dict(Category=categories,
                               Budget=categories_budgets))
    return dmc.Card([
        dmc.CardSection([
            dmc.Group([
                dmc.Text(group_name, size="md", style={'padding-left': '5px'}),
                dmc.Text(group_budget, size="md", style={'padding-right': '5px'}),
                # dmc.ActionIcon(
                #     DashIconify(icon="carbon:overflow-menu-horizontal"),
                #     color="gray",
                #     variant="transparent",
                # )
            ], position='apart')
        ], withBorder=True, className="category-card-header"),
        dmc.Table(create_table(cat_df))
    ], withBorder=True, shadow="md", radius="md", className="category-card")


def _create_category_card_grid():
    cards = []
    for group in CAT_DB.get_group_names():
        group_budget = CAT_DB.get_group_budget(group)[CatDBSchema.BUDGET].sum()
        categories = CAT_DB.get_categories_in_group(group)
        categories_budgets = [CAT_DB.get_category_budget(cat) for cat in categories]
        cards.append(dmc.Col([_create_group_card(group,
                                                 group_budget,
                                                 categories,
                                                 categories_budgets)], span=4))
    return cards


def _create_layout():
    return dbc.Container([
        dbc.Row([
            dbc.Row([html.H1("Categories")]),
        ]),
        dbc.Row([
            dbc.Col([
                dmc.Grid(_create_category_card_grid(), gutter='xs')
            ], width=6),
            dbc.Col([], width=6)
        ]),
    ], fluid=True)


layout = _create_layout
