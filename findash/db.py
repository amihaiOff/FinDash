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


class Record:
    def to_df(self):
        pass
