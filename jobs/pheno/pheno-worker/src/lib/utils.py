import os

from psycopg2 import connect

from .s3 import upload_file_to_s3

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
def upload_logfile_to_s3(bucket, file_path, params):
    user_id = params["metadata"]["user_id"]
    name = params["metadata"]["name"]

    if params["type"] == "training":
        study = params["metadata"]["study"]
        key = f"trainings/{user_id}/{study}/{name}/{name}.log"
    else:
        key = f"classifications/{user_id}/{name}/{name}.log"

    upload_file_to_s3(bucket, key, file_path)
