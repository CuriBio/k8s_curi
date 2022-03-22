from fastapi import APIRouter
from lib.db import database as db
router = APIRouter(tags=["dashboard"])


@router.get("/usage/{user_id}")
async def query_for_user_usage(user_id: int, month: int, year: int):
    response_dict = dict()
    values = {"id": user_id, "month": month, "year": year}

    count_query = """SELECT 
        (SELECT COUNT(*) FROM trainings WHERE user_id=:id AND EXTRACT(MONTH FROM created_at)=:month AND EXTRACT(YEAR FROM created_at)=:year) as trainings,
        (SELECT COUNT(*) FROM experiments WHERE user_id=:id AND EXTRACT(MONTH FROM created_at)=:month AND EXTRACT(YEAR FROM created_at)=:year) as experiments,
        (SELECT COUNT(*) FROM segtrainings WHERE user_id=:id AND EXTRACT(MONTH FROM created_at)=:month AND EXTRACT(YEAR FROM created_at)=:year) as segtrainings,
        (SELECT COUNT(*) FROM segmentations WHERE user_id=:id AND EXTRACT(MONTH FROM created_at)=:month AND EXTRACT(YEAR FROM created_at)=:year) as segmentations"""

    count_rows = await db.fetch_one(query=count_query, values=values)
    response_dict.update(count_rows)

    processtime_query = """SELECT(COALESCE(
        (SELECT SUM(CASE WHEN t.processingtime NOT LIKE '' THEN CAST(t.processingtime AS INT) ELSE 0 END) FROM
        (SELECT user_id, created_at, processingtime FROM trainings UNION SELECT user_id, created_at, processingtime FROM experiments)t
        WHERE t.user_id=:id AND EXTRACT(MONTH FROM t.created_at)=:month AND EXTRACT(YEAR FROM t.created_at)=:year), 0)) AS total_processingtime;"""

    processingtime_row = await db.fetch_one(query=processtime_query, values=values)
    response_dict["total_processingtime"] = (
        processingtime_row["total_processingtime"] / 60
    )  # convert to hours

    return response_dict


@router.get("/getStatus")
async def get_dashboard_status():
    return
