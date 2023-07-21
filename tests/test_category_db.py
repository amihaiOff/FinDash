import os

from dotenv import load_dotenv
from hypothesis.stateful import Bundle, RuleBasedStateMachine, \
    rule, precondition, consumes, invariant
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

ENV_NAME = 'stag'
load_dotenv(f'../.env.{ENV_NAME}')


class TestCatDB(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()
        self.cat_db = self._setup_cat_db()
        print('db', self.cat_db._db)
        self.cat_groups_to_cat = {}

    @staticmethod
    def _setup_cat_db():
        with TemporaryDirectory() as temp_dir:
            os.mkdir(f'{temp_dir}/cat_db')
            dummy_cat_db = create_dummy_cat_db(is_empty=True)
            dummy_cat_db.to_parquet(f'{temp_dir}/cat_db/cat_db.pq')
            return CategoriesDB(LocalIO(temp_dir))

    categories_bundle = Bundle("categories")
    cat_groups_bundle = Bundle("cat_groups")

    @rule(target=cat_groups_bundle, category_group=st.text())
    def add_cat_group(self, category_group: str) -> str:
        if category_group not in self.cat_db.get_group_names():
            group_name, new_cat_name = self.cat_db.add_category_group(category_group)
            self.cat_groups_to_cat[category_group] = [new_cat_name]
            print('add_g', category_group)
        else:
            with pytest.raises(ValueError):
                self.cat_db.add_category_group(category_group)
        return category_group

    @precondition(lambda self: len(self.cat_db.get_group_names()) > 0)
    @rule(target=categories_bundle, category_group=cat_groups_bundle)
    def add_category(self, category_group: str) -> str:
        new_cat_name = self.cat_db.add_category(category_group)
        self.cat_groups_to_cat[category_group].append(new_cat_name)
        print('add_c', new_cat_name, category_group)
        return new_cat_name

    @precondition(lambda self: len(self.cat_db.get_categories()) > 0)
    @rule(old_name=categories_bundle, new_name=st.text())
    def update_category_name(self, old_name: str, new_name: str) -> None:
        if new_name not in self.cat_db.get_categories():
            self.cat_db.update_category_name(old_name, new_name)
            for group, cats in self.cat_groups_to_cat.items():
                if old_name in cats:
                    cats.remove(old_name)
                    cats.append(new_name)
        else:
            with pytest.raises(ValueError):
                self.cat_db.update_category_name(old_name, new_name)
        print('upd', old_name, new_name)

    @precondition(lambda self: len(self.cat_db.get_categories()) > 0)
    @rule(category_name=consumes(categories_bundle))
    def delete_category(self, category_name: str) -> None:
        self.cat_db.delete_category(category_name)
        for group, cats in self.cat_groups_to_cat.items():
            if category_name in cats:
                cats.remove(category_name)
        print('del', category_name)

    @invariant()
    @settings(print_blob=True)
    def check_equivalence(self):
        # test same cat groups
        test_groups = list(self.cat_groups_to_cat.keys())
        db_groups = self.cat_db.get_group_names()
        # print(test_groups)
        # print(db_groups)
        # print('--------------------')
        assert test_groups == db_groups

        # test same categories
        for group in test_groups:
            test_cats = self.cat_groups_to_cat[group]
            db_cats = self.cat_db.get_cats_in_group_list(group)
            print(group)
            print(test_cats)
            print(db_cats)
            print('--------------------')
            assert set(test_cats) == set(db_cats)

    # @rule(category_name=categories_bundle, budget=st.floats())
    # def update_category_budget(self,
    #                            category_name: str,
    #                            budget: float) -> None:
    #     self.cat_db.update_category_budget(category_name, budget)
    #
    # @precondition(lambda self: len(self.cat_db.get_categories()) > 0)
    # @rule(payee=st.text(), cat=categories_bundle)
    # def update_payee_to_cat_mapping(self, payee: str, cat: str):
    #     self.cat_db.update_payee_to_cat_mapping(payee, cat)
    #
    # @rule(category_name=categories_bundle)
    # def category_exists(self, category_name: str):
    #     assert category_name in self.cat_db.get_categories()


TestDBComparison = TestCatDB.TestCase
