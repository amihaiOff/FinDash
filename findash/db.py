from abc import ABC, abstractmethod
from typing import List

import pandas as pd


class DB(ABC):

    @abstractmethod
    def connect(self, db_path: str):
        pass

    @abstractmethod
    def disconnect(self):
        pass

    @abstractmethod
    def get_data_by_id(self, uuid_list: List[str]) -> pd.DataFrame:
        pass

    @abstractmethod
    def insert_data(self, df: pd.DataFrame) -> None:
        pass

    @abstractmethod
    def update_data(self):
        pass

    @abstractmethod
    def delete_data(self, uuid_list: List[str]) -> None:
        pass


class Record(ABC):
    def to_df(self):
        return pd.DataFrame([self.to_dict()], index=[0])

    @property
    @abstractmethod
    def schema_cols(self):
        pass

    def to_list(self):
        return self.schema_cols

    def to_dict(self):
        """
        convert to dict of form {col_name: value}
        :return:
        """
        return {field_name: field_val for field_name, field_val in self.__dict__.items() if
                field_val in self.schema_cols}
