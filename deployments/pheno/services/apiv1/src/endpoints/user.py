from fastapi import APIRouter, status
from lib.models import *
import main
from lib.utils import email_user
from fastapi.responses import JSONResponse

router = APIRouter(tags=["user"])

# User-related
@router.get("/logout")
def logout():
    pass


@router.post("/login")
def login(email: str, password: str):
    return


@router.post("/register")
def register_new_user(name: str, email: str, password: str):
    return


@router.post("/emailUserStatus")
async def email_training_status(body: Email_request_model) -> JSONResponse:
    get_email_query = "SELECT email FROM users WHERE id=:user_id"
    email = await main.db.fetch_one(query=get_email_query, values={"user_id": body.user_id})
    updated_params = {"email": email["email"], "message": body.message, "subject": body.name}

    await email_user(Email_params_model(**updated_params))

    return JSONResponse(status_code=status.HTTP_200_OK, content={"message": "Email has been sent"})
