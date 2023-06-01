import os

from hypothesis.stateful import Bundle, RuleBasedStateMachine, \
    rule, precondition, consumes
import hypothesis.strategies as st
from hypothesis import example, settings, Verbosity
import pytest
from tempfile import TemporaryDirectory

from findash.categories_db import CategoriesDB
from findash.file_io import LocalIO
from tests.create_dummy_data.dummy_cat_and_accounts_db import \
    create_dummy_cat_db

settings.register_profile("stag", max_examples=100,
                          verbosity=Verbosity.verbose)
settings.load_profile('stag')


class TestCatDB(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()
        self.cat_db = self._setup_cat_db()

    @staticmethod
    def _setup_cat_db():
        with TemporaryDirectory() as temp_dir:
            os.mkdir(f'{temp_dir}/cat_db')
            dummy_cat_db = create_dummy_cat_db()
            dummy_cat_db.to_parquet(f'{temp_dir}/cat_db/cat_db.pq')
            return CategoriesDB(LocalIO(temp_dir))

    categories_bundle = Bundle("categories")

    @rule(target=categories_bundle, category_group=st.text())
    def add_category(self, category_group: str) -> None:
        return self.cat_db.add_category(category_group)

    @example(old_name='test', new_name='test')
    @rule(old_name=categories_bundle, new_name=st.text())
    @precondition(lambda self: len(self.cat_db.get_categories()) > 0)
    def update_category_name(self, old_name: str, new_name: str) -> None:
        if new_name not in self.cat_db.get_categories():
            self.cat_db.update_category_name(old_name, new_name)
        else:
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

    @rule(category_name=categories_bundle)
    def category_exists(self, category_name: str):
        assert category_name in self.cat_db.get_categories()


TestDBComparison = TestCatDB.TestCase
