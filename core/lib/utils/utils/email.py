from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from pydantic import EmailStr


class FastMailClient:
    def __init__(self, *, mail_username: str, mail_password: str, template_folder: str):
        conf = ConnectionConfig(
            MAIL_USERNAME=mail_username,
            MAIL_PASSWORD=mail_password,
            MAIL_FROM=mail_username,
            MAIL_PORT=587,
            MAIL_SERVER="smtp.gmail.com",
            MAIL_FROM_NAME="Curi Bio Team",
            MAIL_STARTTLS=True,
            MAIL_SSL_TLS=False,
            USE_CREDENTIALS=True,
            TEMPLATE_FOLDER=template_folder,
        )

        self.fm = FastMail(conf)

    async def send_email(self, *, emails: list[EmailStr], subject: str, template: str, template_body: dict):
        if template_body.get("username") is None:
            template_body["username"] = "Admin"

        message = MessageSchema(
            subject=subject,
            recipients=emails,
            subtype=MessageType.html,
            template_body=template_body,
        )

        await self.fm.send_message(message, template_name=template)
