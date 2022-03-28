import re

from .models import *
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from fastapi import HTTPException, Request, Response
from fastapi.routing import APIRoute

from typing import Callable
# import matplotlib.pyplot as plt

# ------------------------------------------ #


class RouteErrorHandler(APIRoute):
    """Custom APIRoute that handles application errors and exceptions"""

    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request) -> Response:
            try:
                return await original_route_handler(request)
            except Exception as err:
                if isinstance(err, HTTPException):
                    raise err
                # wrap error into 500 exception
                raise HTTPException(status_code=500, detail=f"Unable to process request: {err}")

        return custom_route_handler


# ------------------------------------------ #

# TODO consider adding templates, but current app uses templates with one line messages so didn't seem necessary for current useage
# only email to consider is the register "welcome" emails
async def email_user(params: Email_params_model) -> None:
    conf = ConnectionConfig(
        MAIL_USERNAME="tbd@gmail.com",
        MAIL_PASSWORD="tbd",
        MAIL_FROM="tbd@gmail.com",
        MAIL_PORT=587,
        MAIL_SERVER="smtp.gmail.com",
        MAIL_FROM_NAME="CuriBio Admin",
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
        raise Exception(f"Email failed to send with error: {e}")


# ------------------------------------------ #


def format_name(name: str):
    no_spaces = re.sub(r"\s+", "_", name)
    no_spec_chars = re.sub("[()./\-+]", "_", no_spaces)
    return no_spec_chars


# ------------------------------------------ #
# image conversion utils directly from old app under /image_conversion
# def readCSV(fileIn, header=1, dropCols=[0, 1]):
#     signals = pd.read_csv(fileIn, header=header)
#     signals = signals.drop(signals.columns[dropCols], axis=1)
#     signals = signals.astype(float)
#     return signals


# def makePNG(signals, fileOut, figsize=(3, 3), linewidth=2):
#     plt.figure(figsize=figsize)
#     for k in signals.columns:
#         sig = signals[k]
#         plt.plot(range(len(sig)), sig, linewidth=linewidth)

#     plt.axis("off")
#     plt.savefig(fileOut)
#     plt.close()


# async def is_image_file(filename: str):
#     IMG_EXTENSIONS = [
#         ".jpg",
#         ".JPG",
#         ".jpeg",
#         ".JPEG",
#         ".png",
#         ".PNG",
#         ".ppm",
#         ".PPM",
#         ".bmp",
#         ".BMP",
#     ]
#     IMG_EXTENSIONS_TIF = [
#         ".tif",
#         ".tiff",
#         ".TIF",
#         ".TIFF",
#     ]
#     return any(filename.endswith(extension) for extension in IMG_EXTENSIONS + IMG_EXTENSIONS_TIF)
