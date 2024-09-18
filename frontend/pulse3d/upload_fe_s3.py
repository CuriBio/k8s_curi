import os
import sys
import json
import mimetypes
import subprocess


"""
To use this independently, you'll still need to generate the static files for export manually before running this script.
"""


def get_fe_version():
    with open(os.path.join("src", "package.json")) as f:
        package_dict = json.loads(f.read())
        return package_dict["version"]


def upload_directory_to_s3(bucket, fe_version):
    for root, _, files in os.walk(os.path.join("src", "out")):
        for file_name in files:
            # Create relative filepath to add to key prefix
            file_path = os.path.join(root, file_name)
            rel_path_with_ext = os.path.relpath(file_path, os.path.join("src", "out"))
            rel_path_no_ext, file_ext = os.path.splitext(rel_path_with_ext)

            rel_path = rel_path_no_ext if "html" in file_ext else rel_path_with_ext
            obj_key = f"v{fe_version}/{rel_path}"

            upload_file_to_s3(bucket, obj_key, file_path)


def upload_file_to_s3(bucket, key, file) -> None:
    content_type = mimetypes.guess_type(file)[0]

    if content_type is None:  # sitemanifest returns None here in docker
        content_type = "application/manifest+json"

    # you have to add 'text/html' content-type to put_object when you remove the file extension
    # file extension for non-html files will get correct content-type without having to set it
    subprocess.run(["aws", "s3", "cp", file, f"s3://{bucket}/{key}", "--content-type", content_type])


if __name__ == "__main__":
    try:
        cluster = sys.argv[1].lower()
        assert cluster in ("test", "prod", "modl")
    except IndexError:
        print("Must provide a name for the cluster: 'python upload_fe_s3.py <test/prod/modl>'")  # allow-print
        sys.exit(1)
    except Exception:
        print("Invalid value for cluster, must be 'test', 'modl', or 'prod'")  # allow-print
        sys.exit(1)
    else:
        bucket = "dashboard.curibio.com" if cluster == "prod" else f"dashboard.curibio-{cluster}.com"

        # get frontend version from package.json
        fe_version = get_fe_version()
        # upload /out directory of static files
        upload_directory_to_s3(bucket, fe_version)
