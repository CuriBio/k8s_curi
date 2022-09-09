import hashlib
import base64
import os
from typing import Any, List, Dict

import boto3
from botocore.exceptions import ClientError
from botocore.client import Config


class S3Error(Exception):
    """Raise instead of a ClientError"""


def generate_presigned_url(bucket: str, key: str, exp: int = 3600) -> Any:
    s3 = boto3.resource("s3")
    s3_client = boto3.client("s3", config=Config(signature_version="s3v4"))

    # check if object exists
    try:
        s3.Object(bucket, key).load()
    except:
        # there's probably a better error type that could be raised here
        raise ValueError(f"{key} not found in {bucket}")

    # generate presigned url, if exists
    try:
        url = s3_client.generate_presigned_url(
            "get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=exp
        )
    except ClientError as e:
        raise S3Error(f"Failed to generate presigned url for {bucket}/{key}: {repr(e)}")

    return url


def generate_presigned_urls_for_dir(bucket: str, key_prefix: str, objs_only: bool = False) -> List[str]:
    try:
        s3 = boto3.resource("s3")
        bucket = s3.Bucket(bucket)
        objs = list(bucket.objects.filter(Prefix=key_prefix))

        if objs_only:
            return [obj.key for obj in objs]

        return [generate_presigned_url(bucket, obj.key) for obj in objs]

    except (ClientError, S3Error) as e:
        raise S3Error(f"Failed to generate presigned urls for {bucket}/{key_prefix}: {repr(e)}")
    

def generate_presigned_post(bucket: str, key: str, md5s: str) -> Dict[Any, Any]:
    s3_client = boto3.client("s3", config=Config(signature_version="s3v4"))

    try:
        fields = {"Content-MD5": md5s}
        conditions = [["starts-with", "$Content-MD5", ""]]

        return s3_client.generate_presigned_post(
            bucket, key, Fields=fields, Conditions=conditions, ExpiresIn=3600
        )
    except ClientError as e:
        raise S3Error(f"Failed to generate presigned post for {bucket}/{key} with error: {repr(e)}")


def copy_s3_file(bucket: str, source_key: str, target_key: str) -> None:
    try:
        s3 = boto3.resource("s3")
        copy_source = {"Bucket": bucket, "Key": source_key}
        s3.meta.client.copy(copy_source, bucket, target_key)
        
    except ClientError as e:
        raise S3Error(f"Failed to copy {source_key} to {target_key} with error: {repr(e)}")


def copy_s3_directory(bucket: str, key_prefix: str, target_prefix: str) -> None:
    try:
        s3 = boto3.resource("s3")
        bucket = s3.Bucket(bucket)
        objs = list(bucket.objects.filter(Prefix=key_prefix))

        for obj in objs:
            # get relative path to keep subdirectory structure
            source_key = obj.key
            target_key = source_key.replace(key_prefix, target_prefix)
            copy_s3_file(source_key, target_key)

    except ClientError as e:
        raise S3Error(f"Failed to copy files from {source_key} to {target_key} with error: {repr(e)}")


def upload_file_to_s3(bucket, key, file) -> None:
    s3_client = boto3.client("s3")
    try:
        with open(f"{file}", "rb") as f:
            contents = f.read()
            md5 = hashlib.md5(contents).digest()
            md5s = base64.b64encode(md5).decode()
            s3_client.put_object(Body=f, Bucket=bucket, Key=key, ContentMD5=md5s)
    except ClientError as e:
        raise S3Error(f"Failed to upload file {bucket}/{key}: {repr(e)}")


def upload_directory_to_s3(bucket, key, dir) -> None:
    for root, _, files in os.walk(dir):
        for file_name in files:
            # Create relative filepath to add to key prefix
            file_path = os.path.join(root, file_name)
            rel_path = os.path.relpath(file_path, dir)

            full_key = f"{key}/{rel_path}"
            upload_file_to_s3(bucket, full_key, file_path)


def download_file_from_s3(bucket, key, file_path) -> None:
    try:
        s3_client = boto3.client("s3")
        s3 = boto3.resource("s3")

        # check if object exists
        try:
            s3.Object(bucket, key).load()
        except:
            raise Exception(f"Object at {key} was not found.")

        s3_client.download_file(Bucket=bucket, Key=key, Filename=file_path)
        
    except ClientError as e:
        raise S3Error(f"Failed to download file {bucket}/{key}: {repr(e)}")


def download_directory_from_s3(bucket, key, file_path) -> None:
    try:
        s3_client = boto3.resource("s3")
        bucket = s3_client.Bucket(bucket)
        objs = list(bucket.objects.filter(Prefix=key))
        for obj in objs:
            # get relative path to keep subdirectory structure
            rel_path = os.path.relpath(obj.key, key)
            target_dir = os.path.join(file_path, rel_path)

            # make subdirectories if they don't exist, remove filename from path
            os.makedirs(os.path.dirname(target_dir), exist_ok=True)

            # download to target directory with filename
            bucket.download_file(obj.key, target_dir)
    except Exception as e:
        raise S3Error(f"Failed to download directory {bucket}/{key}: {repr(e)}")
