import json
import pickle
from collections import defaultdict
from io import BytesIO
from pathlib import Path
from typing import Optional, Dict, cast, List, Iterable, Union, Any
from abc import ABC, abstractmethod

import boto3
import pandas as pd
import yaml
from botocore.exceptions import ClientError


class Ftype:
    JSON = 'json'
    PICKLE = 'pickle'
    PARQUET = 'parquet'


class FileIO(ABC):
    def __init__(self, data_root: str):
        self._data_root = data_root

    def _add_root_prefix(self, path):
        return (
            path
            if path.startswith(self._data_root)
            else str(Path(self._data_root).joinpath(path))
        )

    def save_file(self, save_path: str, data: Any, ftype: Optional[Ftype] = None):
        save_path = self._add_root_prefix(save_path)
        if ftype == Ftype.JSON or save_path.endswith('.json'):
            self._save_json(data, save_path)
        elif ftype == Ftype.PARQUET or \
                save_path.endswith('.parquet') or \
                save_path.endswith('.pq'):
            self._save_parquet(data, save_path)
        else:
            raise ValueError(f'Unknown file type: {ftype} or file extension: {save_path}')

    def load_file(self, load_path: str, ftype: Optional[Ftype] = None) -> Any:
        load_path = self._add_root_prefix(load_path)
        if ftype == Ftype.JSON or load_path.endswith('.json'):
            return self._read_json(load_path)
        elif ftype == Ftype.PARQUET or \
                (load_path.endswith('.parquet') or load_path.endswith('.pq')):
            return self._read_parquet(load_path)
        else:
            raise ValueError(f'Unknown file type: {ftype} or file extension: {load_path}')

    @abstractmethod
    def get_dirs_in_dir(
            self,
            dir_path: str,
            full_paths: bool = False) -> Iterable[str]:
        pass

    @abstractmethod
    def get_files_in_dir(
            self,
            dir_path: str,
            including_subdirs=False,
            full_paths=False,
    ) -> List[str]:
        pass

    @abstractmethod
    def _read_json(self, load_path: str) -> Union[List, Dict[str, Any]]:
        pass

    @abstractmethod
    def _read_parquet(self, load_path: str) -> Any:
        pass

    @abstractmethod
    def _save_json(self, data: Any, save_path: str) -> None:
        pass

    @abstractmethod
    def _save_parquet(self, data: Any, save_path: str) -> None:
        pass

    @abstractmethod
    def read_yaml(self, load_path: str) -> Any:
        pass


class LocalIO(FileIO):
    def __init__(self, data_root: str):
        super().__init__(data_root)

    def read_yaml(self, load_path: str) -> Any:
        load_path = self._add_root_prefix(load_path)
        with open(load_path, 'r') as f:
            return yaml.safe_load(f)

    def _read_json(self, load_path: str) -> Union[List, Dict[str, Any]]:
        with open(load_path) as f:
            return json.load(f)

    def _read_parquet(self, load_path: str) -> Any:
        try:
            return pd.read_parquet(load_path)
        except Exception as e:
            raise ValueError(
                f'Unknown data type for ' f'parquet(only support pd.DataFrame: {e}'
            ) from e

    def _save_json(self, data: Any, save_path: str) -> None:
        with open(save_path, 'w') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def _save_parquet(self, data: Any, save_path: str) -> None:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(data, pd.DataFrame):
            data.to_parquet(save_path)
        else:
            raise ValueError(f'Unknown data type for parquet: {type(data)}')

    def get_dirs_in_dir(self,
                        dir_path: str,
                        full_paths: bool = False) -> Iterable[str]:
        dir_path = self._add_root_prefix(dir_path)
        path = Path(dir_path)
        if full_paths:
            return [str(f)[len(self._data_root)+1:] for f in path.iterdir() if f.is_dir()]
        else:
            return [f.name for f in path.iterdir() if f.is_dir()]

    def get_files_in_dir(self,
                         dir_path: str,
                         including_subdirs=False,
                         full_paths=False) -> List[str]:
        """
        get a list of files in a directory, excluding subdirectories unless specified by
        the including_subdirs argument
        :param dir_path:
        :param including_subdirs:
        :param full_paths:
        :return:
        """
        dir_path = self._add_root_prefix(dir_path)
        path = Path(dir_path)
        files = path.glob('*')
        if not including_subdirs:
            files = [f for f in files if f.is_file()]

        return [str(f)[len(self._data_root)+1:] for f in files] if full_paths else [f.name for f in files]


class Bucket(FileIO):
    """
    Tools for environment-dependent file system operations on the cloud.
    """

    def __init__(self, bucket_name, data_root: str = ''):
        super().__init__(data_root)
        self._bucket_name = bucket_name
        self._s3 = boto3.client("s3")
        self._s3_res = boto3.resource("s3")

    def _save_json(self, data, save_path: str) -> None:
        self._s3_res.Object(self._bucket_name, save_path).put(
            Body=json.dumps(data).encode(), **Bucket._get_extra_args(save_path)
        )

    def _read_json(self, path: str) -> Union[List, Dict[str, Any]]:
        obj = self._s3.get_object(Bucket=self._bucket_name, Key=path)
        return cast(
            Union[List, Dict[str, Any]],
            json.loads(Bucket._read_bytes_from_s3_obj(obj).decode()),
        )

    def _save_parquet(self, data, save_path: str) -> None:
        if isinstance(data, pd.DataFrame):
            data.to_parquet(f's3://{self._bucket_name}/{save_path}')
        else:
            raise ValueError(f'Unknown data type for parquet: {type(data)}')

    def _read_parquet(self, load_path: str) -> Any:
        try:
            return pd.read_parquet(f's3://{self._bucket_name}/{load_path}')
        except Exception as e:
            raise ValueError(
                f'Unknown data type for ' f'parquet(only support pd.DataFrame: {e}'
            ) from e

    def write_pickle(self, data, path: str) -> None:
        self._s3_res.Object(self._bucket_name, path).put(
            Body=pickle.dumps(data, protocol=4)
        )

    def read_pickle(self, path: str) -> Any:
        obj = self._s3.get_object(Bucket=self._bucket_name, Key=path)
        return pickle.loads(Bucket._read_bytes_from_s3_obj(obj))

    def read_yaml(self, load_path: str) -> Any:
        load_path = self._add_root_prefix(load_path)
        return yaml.safe_load(self.read_str(load_path))

    def write_str(self, str_data: str, path: str) -> None:
        data_fileobj = BytesIO(str_data.encode())
        self._s3.upload_fileobj(
            data_fileobj,
            self._bucket_name,
            path,
            ExtraArgs=Bucket._get_extra_args(path),
        )

    def read_str(self, path: str) -> str:
        obj = self._s3.get_object(Bucket=self._bucket_name, Key=path)
        return Bucket._read_bytes_from_s3_obj(obj).decode()

    def write_binary(self, binary_data: Union[bytes, BytesIO], path: str) -> None:
        self._s3.put_object(
            Body=binary_data,
            Bucket=self._bucket_name,
            Key=path,
            **Bucket._get_extra_args(path),
        )

    def read_binary(self, path: str) -> bytes:
        obj = self._s3.get_object(Bucket=self._bucket_name, Key=path)
        return Bucket._read_bytes_from_s3_obj(obj)

    def write_from_local_file(self, local_file_path: str, path: str) -> None:
        self._s3.upload_file(
            local_file_path,
            self._bucket_name,
            path,
            ExtraArgs=Bucket._get_extra_args(path),
        )

    def copy_file(self, src_path: str, dst_path: str) -> None:
        self._s3_res.Object(self._bucket_name, dst_path).copy_from(
            CopySource=f"{self._bucket_name}/{src_path}"
        )
        self._s3_res.Object(self._bucket_name, src_path).delete()

    def delete_files(self, paths: Iterable[str]) -> None:
        self._s3.delete_objects(
            Bucket=self._bucket_name,
            Delete={"Objects": [{"Key": path} for path in paths]},
        )

    def get_files_in_dir(
        self,
        dir_path: str,
        including_subdirs=False,
        full_paths=False,
    ) -> List[str]:

        dir_path = self._add_root_prefix(dir_path)
        bucket = self._s3_res.Bucket(self._bucket_name)
        if not dir_path.endswith("/"):
            dir_path += "/"
        # Return all files under the dir, but not the dir itself
        filter_params = {"Prefix": dir_path}
        if not including_subdirs:
            filter_params["Delimiter"] = "/"
        files = [
            obj.key
            for obj in bucket.objects.filter(**filter_params)
            if not obj.key.endswith("/")
        ]
        if not full_paths:
            files = [f.replace(dir_path, "") for f in files]
        return files

    def get_dirs_in_dir(
        self,
        dir_path: str,
        full_paths=False,
    ) -> Iterable[str]:

        dir_path = self._add_root_prefix(dir_path)
        if dir_path != "" and not dir_path.endswith("/"):
            dir_path += "/"
        objs = self._s3.list_objects(
            Bucket=self._bucket_name, Prefix=dir_path, Delimiter="/"
        )
        subdirs = [prefix["Prefix"][:-1] for prefix in objs.get("CommonPrefixes", [])]
        if not full_paths:
            subdirs = [subdir.rsplit("/", 1)[-1] for subdir in subdirs]
        return subdirs

    def get_files_by_subdir(
        self,
        dir_path: str,
    ) -> Dict[str, List[str]]:
        files_by_subdir = defaultdict(list)
        bucket = self._s3_res.Bucket(self._bucket_name)
        for obj in bucket.objects.filter(Prefix=dir_path):
            if obj.key.endswith("/"):
                continue
            dir_name, file_name = obj.key.rsplit("/", 1)
            files_by_subdir[dir_name].append(file_name)
        return {k: v for k, v in files_by_subdir.items()}

    def path_exists(self, path: str) -> bool:
        try:
            self._s3.head_object(Bucket=self._bucket_name, Key=path)
            return True
        except ClientError as ce:
            if ce.response["Error"]["Code"] == "404":
                return False
            raise ce

    @property
    def path_sep(self) -> str:
        return "/"

    @staticmethod
    def _read_bytes_from_s3_obj(s3_obj) -> bytes:
        return cast(bytes, s3_obj["Body"].read())

    @staticmethod
    def _get_extra_args(path) -> Dict[str, str]:
        file_type = Bucket._mime_type(path)
        args = dict()
        if file_type is not None:
            args["ContentType"] = file_type
        return args

    @staticmethod
    def _mime_type(path: str) -> Optional[str]:
        types: Dict[str, str] = dict(
            html="text/html",
            json="application/json",
            csv="text/csv",
            pickle="binary/octet-stream",
            parquet="binary/octet-stream",
            png="image/png",
        )
        ext = path.rsplit(".", 1)[-1]
        return types.get(ext)
