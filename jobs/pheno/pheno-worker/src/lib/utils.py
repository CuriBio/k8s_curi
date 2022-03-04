import boto3
import base64
import hashlib
import os

from psycopg2 import connect
from botocore.exceptions import ClientError

# ------------------------------------------ #
def get_db_params():
    try:
        params = {
            "database": os.environ.get("DB_NAME"),
            "user": os.environ.get("USER"),
            "password": os.environ.get("PASSWORD"),
            "host": os.environ.get("HOST"),
            "port": os.environ.get("PORT"),
        }
    except OSError:
        raise OSError()

    return params


# ------------------------------------------ #
def email_user(message):
    print(message)


# ------------------------------------------ #
def update_table_value(table, id, field, value, logger):
    update_query = f"UPDATE {table} SET {field}='{value}' WHERE id={str(id)};"
    try:
        params = get_db_params()
        with connect(**params) as conn:
            cur = conn.cursor()
            cur.execute(update_query)
            conn.commit()
            cur.close()
    except Exception as e:
        logger.error(f"Failed to update field ({field}) in table ({table}): {e}")


# ------------------------------------------ #
def upload_file_to_s3(bucket, key, file, logger):
    s3_client = boto3.client("s3")
    try:
        with open(f"{file}", "rb") as f:
            contents = f.read()
            md5 = hashlib.md5(contents).digest()
            md5s = base64.b64encode(md5).decode()
            s3_client.put_object(Body=f, Bucket=bucket, Key=key, ContentMD5=md5s)
        logger.info(f"Uploaded file: {bucket}/{key}")
    except ClientError as e:
        logger.error(f"Failed to upload file {bucket}/{key}: {e}")


# ------------------------------------------ #
def upload_directory_to_s3(bucket, key, dir, logger):
    for root, _, files in os.walk(dir):
        for file_name in files:
            # Create relative filepath to add to key prefix
            file_path = os.path.join(root, file_name)
            rel_path = os.path.relpath(file_path, dir)

            full_key = f"{key}/{rel_path}"
            upload_file_to_s3(bucket, full_key, file_path, logger)


# ------------------------------------------ #
def download_file_from_s3(bucket, key, file_path, logger):
    try:
        s3_client = boto3.client("s3")
        s3_client.download_file(Bucket=bucket, Key=key, Filename=file_path)
        logger.info(f"Downloaded file: {bucket}/{key} to {file_path}")
    except ClientError as e:
        logger.error(f"Failed to download file {bucket}/{key}: {e}")


# ------------------------------------------ #
def download_directory_from_s3(bucket, key, file_path, logger):
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
        logger.error(f"Failed to download directory {bucket}/{key}: {e}")


# ------------------------------------------ #
def upload_logfile_to_s3(bucket, file_path, params, logger):
    user_id = params["metadata"]["user_id"]
    name = params["metadata"]["name"]

    if params["type"] == "training":
        study = params["metadata"]["study"]
        key = f"trainings/{user_id}/{study}/{name}/{name}.log"
    else:
        key = f"classifications/{user_id}/{name}/{name}.log"

    upload_file_to_s3(bucket, key, file_path, logger)
