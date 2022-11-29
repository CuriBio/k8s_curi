import hashlib
import base64
import os
import boto3
import json

"""
To use this independently, you'll still need to generate the static files for export manually before running this script.
"""

src_path = os.path.join("frontend", "pulse3d", "src")
bucket = "dashboard.curibio-test.com"


def upload_file_to_s3(bucket, key, file) -> None:
    s3_client = boto3.client("s3")
    with open(f"{file}", "rb") as f:
        contents = f.read()
        md5 = hashlib.md5(contents).digest()
        md5s = base64.b64encode(md5).decode()
        s3_client.put_object(Body=f, Bucket=bucket, Key=key, ContentMD5=md5s)


def get_fe_version():
    with open(os.path.join(src_path, "package.json")) as f:
        package_dict = json.loads(f.read())
        return package_dict["version"]


def upload_directory_to_s3(fe_version):
    for root, _, files in os.walk(os.path.join(src_path, "out")):
        for file_name in files:
            # Create relative filepath to add to key prefix
            file_path = os.path.join(root, file_name)
            rel_path = os.path.relpath(file_path, os.path.join(src_path, "out"))
            rel_path_no_ext, file_ext = os.path.splitext(rel_path)

            obj_key = (
                f"v{fe_version}/{rel_path}" if "html" not in file_ext else f"v{fe_version}/{rel_path_no_ext}"
            )
            print(f"Uploading {obj_key}")
            upload_file_to_s3(bucket, obj_key, file_path)


if __name__ == "__main__":
    # get frontend version from package.json
    fe_version = get_fe_version()
    # upload /out directory of static files
    upload_directory_to_s3(fe_version)
