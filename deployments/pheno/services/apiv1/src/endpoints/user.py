import logging
from fastapi import APIRouter, status, Depends
from fastapi.responses import JSONResponse

from lib.models import *
from lib.db import get_cur
from lib.utils import email_user
from lib.utils import RouteErrorHandler


logging.basicConfig(format="%(asctime)s %(message)s", level=logging.INFO, datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger(__name__)

router = APIRouter(tags=["user"], route_class=RouteErrorHandler)

# User-related
# @router.get("/logout")
# def logout():
#     pass


# @router.post("/login")
# def login(email: str, password: str):
#     return


# @router.post("/register")
# def register_new_user(name: str, email: str, password: str):
#     return


@router.post("/emailUserStatus")
async def email_training_status(body: Email_request_model, cur=Depends(get_cur)) -> JSONResponse:
    email = await cur.fetchrow("SELECT email FROM users WHERE id=$1", body.user_id)
    updated_params = {"email": email["email"], "message": body.message, "subject": body.name}

    logger.info("Awaiting email to be sent.")
    await email_user(Email_params_model(**updated_params))

    return JSONResponse(status_code=status.HTTP_200_OK, content={"message": "Email has been sent"})
