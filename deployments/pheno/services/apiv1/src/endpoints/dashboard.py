import logging

from fastapi import APIRouter, Depends

from lib.db import get_cur
from lib.models import *
from lib.utils import RouteErrorHandler

logging.basicConfig(format="%(asctime)s %(message)s", level=logging.INFO, datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger(__name__)

router = APIRouter(tags=["dashboard"], route_class=RouteErrorHandler)


@router.get("/usage/{user_id}")
async def query_for_user_usage(user_id: int, month: int, year: int, cur=Depends(get_cur)):
    response_dict = dict()

    # query for count of each individual table
    count_query = """SELECT
        (SELECT COUNT(*) FROM trainings WHERE user_id=$1 AND EXTRACT(MONTH FROM created_at)=$2 AND EXTRACT(YEAR FROM created_at)=$3) as trainings,
        (SELECT COUNT(*) FROM experiments WHERE user_id=$1 AND EXTRACT(MONTH FROM created_at)=$2 AND EXTRACT(YEAR FROM created_at)=$3) as experiments,
        (SELECT COUNT(*) FROM segtrainings WHERE user_id=$1 AND EXTRACT(MONTH FROM created_at)=$2 AND EXTRACT(YEAR FROM created_at)=$3) as segtrainings,
        (SELECT COUNT(*) FROM segmentations WHERE user_id=$1 AND EXTRACT(MONTH FROM created_at)=$2 AND EXTRACT(YEAR FROM created_at)=$3) as segmentations"""
    count_rows = await cur.fetchrow(count_query, user_id, month, year)
    response_dict.update(dict(count_rows))

    # query for sum of all processingtimes
    processtime_query = """SELECT(COALESCE(
        (SELECT SUM(CASE WHEN t.processingtime NOT LIKE '' THEN CAST(t.processingtime AS INT) ELSE 0 END) FROM
        (SELECT user_id, created_at, processingtime FROM trainings UNION SELECT user_id, created_at, processingtime FROM experiments)t
        WHERE t.user_id=$1 AND EXTRACT(MONTH FROM t.created_at)=$2 AND EXTRACT(YEAR FROM t.created_at)=$3), 0)) AS total_processingtime;"""
    processingtime_row = await cur.fetchrow(processtime_query, user_id, month, year)

    response_dict["total_processingtime"] = (
        processingtime_row["total_processingtime"] / 60
    )  # convert to hours

    return Usage_res_model(**response_dict)


# @router.get("/getStatus")
# async def get_dashboard_status():
#     return
