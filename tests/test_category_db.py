from hypothesis.stateful import Bundle, RuleBasedStateMachine, \
    rule, precondition, consumes
import hypothesis.strategies as st
from hypothesis import example
import pytest

from findash.categories_db import CategoriesDB


class TestCatDB(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()
        self.cat_db = CategoriesDB()

    categories_bundle = Bundle("categories")

    @rule(category_group=st.text())
    def add_category(self, category_group: str) -> None:
        self.cat_db.add_category(category_group)

    @example(old_name='test', new_name='test')
    @rule(old_name=st.text(), new_name=st.text())
    def update_category_name(self, old_name: str, new_name: str) -> None:
        with pytest.raises(ValueError):
            self.cat_db.update_category_name(old_name, new_name)

    @precondition(lambda self: len(self.cat_db.get_categories()) > 0)
    @rule(category_name=consumes(categories_bundle))
    def delete_category(self, category_name: str) -> None:
        self.cat_db.delete_category(category_name)

    @rule(category_name=categories_bundle, budget=st.floats())
    def update_category_budget(self,
                               category_name: str,
                               budget: float) -> None:
        self.cat_db.update_category_budget(category_name, budget)

    @precondition(lambda self: len(self.cat_db.get_categories()) > 0)
    @rule(payee=st.text(), cat=categories_bundle)
    def update_payee_to_cat_mapping(self, payee: str, cat: str):
        self.cat_db.update_payee_to_cat_mapping(payee, cat)


TestDBComparison = TestCatDB.TestCase
