import json
import pickle
from collections import defaultdict
from io import BytesIO
from typing import Optional, Dict, cast, List, Iterable, Union, Any

import boto3
from botocore.exceptions import ClientError


class Bucket:
    """
    Tools for environment-dependent file system operations on the cloud.
    """

    def __init__(self, bucket_name):
        self._bucket_name = bucket_name
        self._s3 = boto3.client("s3")
        self._s3_res = boto3.resource("s3")

    def write_json_data(self, json_data, path: str) -> None:
        self._s3_res.Object(self._bucket_name, path).put(
            Body=json.dumps(json_data).encode(), **Bucket._get_extra_args(path)
        )

    def read_json_data(self, path: str) -> Union[List, Dict[str, Any]]:
        obj = self._s3.get_object(Bucket=self._bucket_name, Key=path)
        return cast(
            Union[List, Dict[str, Any]],
            json.loads(Bucket._read_bytes_from_s3_obj(obj).decode()),
        )

    def write_pickle(self, data, path: str) -> None:
        self._s3_res.Object(self._bucket_name, path).put(
            Body=pickle.dumps(data, protocol=4)
        )

    def read_pickle(self, path: str) -> Any:
        obj = self._s3.get_object(Bucket=self._bucket_name, Key=path)
        return pickle.loads(Bucket._read_bytes_from_s3_obj(obj))

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
        get_full_paths=False,
    ) -> List[str]:
        bucket = self._s3_res.Bucket(self._bucket_name)
        if not dir_path.endswith("/"):
            dir_path = dir_path + "/"
        # Return all files under the dir, but not the dir itself
        filter_params = {"Prefix": dir_path}
        if not including_subdirs:
            filter_params["Delimiter"] = "/"
        files = [
            obj.key
            for obj in bucket.objects.filter(**filter_params)
            if not obj.key.endswith("/")
        ]
        if not get_full_paths:
            files = [f.replace(dir_path, "") for f in files]
        return files

    def get_dirs_in_dir(
        self,
        dir_path: str,
        get_full_paths=False,
    ) -> List[str]:
        if dir_path != "" and not dir_path.endswith("/"):
            dir_path = dir_path + "/"
        objs = self._s3.list_objects(
            Bucket=self._bucket_name, Prefix=dir_path, Delimiter="/"
        )
        subdirs = [prefix["Prefix"][:-1] for prefix in objs.get("CommonPrefixes", [])]
        if not get_full_paths:
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
