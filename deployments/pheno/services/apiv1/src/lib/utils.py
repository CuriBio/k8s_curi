from botocore.exceptions import ClientError
import boto3
from typing import Any
from models import *
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from fastapi import HTTPException
import re
import os
import hashlib
import base64
from botocore.client import Config
import requests
import pandas as pd
import matplotlib.pyplot as plt

PHENO_BUCKET = "phenolearn"

def generate_presigned_get(key: str, exp: int) -> Any:
    s3 = boto3.resource("s3")
    s3_client = boto3.client("s3")

    # check if object exists
    try:
        s3.Object(PHENO_BUCKET, key).load()
    except:
        return None

    # generate presigned url, if exists
    try:
        url = s3_client.generate_presigned_url(
            "get_object", Params={"Bucket": PHENO_BUCKET, "Key": key}, ExpiresIn=exp
        )
    except ClientError as e:
        raise ClientError(f"Failed to generate presigned url for {PHENO_BUCKET}/{key}: {e}")

    return url


# ------------------------------------------ #


async def email_user(params: Email_params_model) -> None:
    conf = ConnectionConfig(
        MAIL_USERNAME="luciypak@gmail.com",
        MAIL_PASSWORD="Qqq30916.",
        MAIL_FROM="luciypak@gmail.com",
        MAIL_PORT=587,
        MAIL_SERVER="smtp.gmail.com",
        MAIL_FROM_NAME="CuriBio team",
        MAIL_TLS=True,
        MAIL_SSL=False,
        USE_CREDENTIALS=True,
    )

    try:
        message = MessageSchema(
            subject=params.subject,
            recipients=[params.email],  # List of recipients, as many as you can pass
            body=params.message,
        )

        fm = FastMail(conf)
        await fm.send_message(message)
    except Exception as e:
        raise HTTPException(status_code=400, detail={"message": f"Email failed to send with error: {e}"})


# ------------------------------------------ #


def upload_file_to_s3(key: str, file):
    s3_client = boto3.client("s3", config=Config(signature_version="s3v4"))
    try:
        with open(file, "rb") as file_to_read:
            # generate md5
            contents = file_to_read.read()
            md5 = hashlib.md5(contents).digest()
            md5s = base64.b64encode(md5).decode()
            # generate presigned post url
            fields = {"Content-MD5": md5s}
            conditions = [["starts-with", "$Content-MD5", ""]]
            params = s3_client.generate_presigned_post(
                PHENO_BUCKET, key, Fields=fields, Conditions=conditions, ExpiresIn=3600
            )
            # upload file to s3
            response = requests.post(
                params["url"],
                data=params["fields"],
                files={"file": (file, file)},
            )
            if response.status_code != 200:
                raise Exception(
                    f"Failed to upload {file} to {PHENO_BUCKET}/{key} with error: {response.status_code} {response.content}"
                )
            else:
                return response.status_code
    except Exception as e:
        raise Exception(f"Failed to upload {file} to {PHENO_BUCKET}/{key} with error: {e}")


# ------------------------------------------ #


def copy_s3_file(source_key: str, target_key: str):
    try:
        s3 = boto3.resource("s3")
        copy_source = {"Bucket": PHENO_BUCKET, "Key": source_key}
        s3.meta.client.copy(copy_source, "phenolearn", target_key)
    except ClientError as e:
        raise ClientError(f"Failed to copy {source_key} to {target_key} with error: {e}")


# ------------------------------------------ #


def copy_s3_directory(key_prefix: str, target_prefix: str):
    try:
        s3 = boto3.resource("s3")
        bucket = s3.Bucket(PHENO_BUCKET)
        objs = list(bucket.objects.filter(Prefix=key_prefix))

        for obj in objs:
            # get relative path to keep subdirectory structure
            source_key = obj.key
            target_key = source_key.replace(key_prefix, target_prefix)
            copy_s3_file(source_key, target_key)

    except ClientError as e:
        raise ClientError(f"Failed to copy files from {source_key} to {target_key} with error: {e}")


# ------------------------------------------ #


async def is_image_file(filename: str):
    IMG_EXTENSIONS = [
        ".jpg",
        ".JPG",
        ".jpeg",
        ".JPEG",
        ".png",
        ".PNG",
        ".ppm",
        ".PPM",
        ".bmp",
        ".BMP",
    ]
    IMG_EXTENSIONS_TIF = [
        ".tif",
        ".tiff",
        ".TIF",
        ".TIFF",
    ]
    return any(filename.endswith(extension) for extension in IMG_EXTENSIONS + IMG_EXTENSIONS_TIF)


# ------------------------------------------ #


def format_name(name: str):
    no_spaces = re.sub(r"\s+", "_", name)
    no_spec_chars = re.sub("[()./\-+]", "_", no_spaces)
    return no_spec_chars


# ------------------------------------------ #
# image conversion
def readCSV(fileIn, header=1, dropCols=[0, 1]):
    signals = pd.read_csv(fileIn, header=header)
    signals = signals.drop(signals.columns[dropCols], axis=1)
    signals = signals.astype(float)
    return signals


def makePNG(signals, fileOut, figsize=(3, 3), linewidth=2):
    plt.figure(figsize=figsize)
    for k in signals.columns:
        sig = signals[k]
        plt.plot(range(len(sig)), sig, linewidth=linewidth)

    plt.axis("off")
    plt.savefig(fileOut)
    plt.close()
