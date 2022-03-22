import hashlib
import base64
import logging
import os
from typing import Any, List

import boto3
from botocore.exceptions import ClientError
from botocore.client import Config

logger = logging.getLogger(__name__)


def generate_presigned_url(bucket: str, key: str, exp: int = 3600) -> Any:
    s3 = boto3.resource("s3")
    s3_client = boto3.client("s3")

    # check if object exists
    try:
        s3.Object(bucket, key).load()
    except:
        return None

    # generate presigned url, if exists
    try:
        url = s3_client.generate_presigned_url(
            "get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=exp
        )
    except ClientError as e:
        raise ClientError(f"Failed to generate presigned url for {bucket}/{key}: {e}")

    return url


def generate_presigned_urls_for_dir(bucket: str, key_prefix: str, objs_only: bool = False) -> List[str]:
    try:
        s3 = boto3.resource("s3")
        bucket = s3.Bucket(bucket)
        objs = list(bucket.objects.filter(Prefix=key_prefix))

        if objs_only:
            return [obj.key for obj in objs]

        return [generate_presigned_url(obj.key) for obj in objs]

    except ClientError as e:
        raise ClientError(f"Failed to generate presigned urls for {bucket}/{key_prefix}: {e}")


def generate_presigned_post(bucket: str, key: str, file_path):
    s3_client = boto3.client("s3", config=Config(signature_version="s3v4"))
    try:
        with open(file_path, "rb") as file_to_read:
            # generate md5
            contents = file_to_read.read()
            md5 = hashlib.md5(contents).digest()
            md5s = base64.b64encode(md5).decode()

        # generate presigned post url
        fields = {"Content-MD5": md5s}
        conditions = [["starts-with", "$Content-MD5", ""]]

        params = s3_client.generate_presigned_post(
            bucket, key, Fields=fields, Conditions=conditions, ExpiresIn=3600
        )

        return params
    except ClientError as e:
        raise ClientError(f"Failed to upload {file_path} to {bucket}/{key} with error: {e}")


def copy_s3_file(bucket: str, source_key: str, target_key: str):
    try:
        s3 = boto3.resource("s3")
        copy_source = {"Bucket": bucket, "Key": source_key}
        s3.meta.client.copy(copy_source, bucket, target_key)
    except ClientError as e:
        raise ClientError(f"Failed to copy {source_key} to {target_key} with error: {e}")


def copy_s3_directory(bucket: str, key_prefix: str, target_prefix: str):
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
        raise ClientError(f"Failed to copy files from {source_key} to {target_key} with error: {e}")


def upload_file_to_s3(bucket, key, file):
    s3_client = boto3.client("s3")
    try:
        with open(f"{file}", "rb") as f:
            contents = f.read()
            md5 = hashlib.md5(contents).digest()
            md5s = base64.b64encode(md5).decode()
            s3_client.put_object(Body=f, Bucket=bucket, Key=key, ContentMD5=md5s)
        logger.info(f"Uploaded file: {bucket}/{key}")
    except ClientError as e:
        raise ClientError(f"Failed to upload file {bucket}/{key}: {e}")


def upload_directory_to_s3(bucket, key, dir):
    for root, _, files in os.walk(dir):
        for file_name in files:
            # Create relative filepath to add to key prefix
            file_path = os.path.join(root, file_name)
            rel_path = os.path.relpath(file_path, dir)

            full_key = f"{key}/{rel_path}"
            upload_file_to_s3(bucket, full_key, file_path)


def download_file_from_s3(bucket, key, file_path):
    try:
        s3_client = boto3.client("s3")
        s3_client.download_file(Bucket=bucket, Key=key, Filename=file_path)
        logger.info(f"Downloaded file: {bucket}/{key} to {file_path}")
    except ClientError as e:
        raise ClientError(f"Failed to download file {bucket}/{key}: {e}")


def download_directory_from_s3(bucket, key, file_path):
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
        raise ClientError(f"Failed to download directory {bucket}/{key}: {e}")
