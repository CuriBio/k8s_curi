import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass
from uuid import UUID
import json

from fastapi import FastAPI, Request, Depends, status, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
import structlog
import uvicorn

from auth import ProtectedAny, Token, decode_token
from utils.db import AsyncpgPoolDep
from utils.logging import setup_logger
from core.config import DATABASE_URL, DASHBOARD_URL

setup_logger()
logger = structlog.stdlib.get_logger("api.access")

asyncpg_pool = AsyncpgPoolDep(dsn=DATABASE_URL)


MESSAGE_RETRY_TIMEOUT = 15000


# TODO split up this file into multiple files


class UserNotConnectedError(Exception):
    pass


@dataclass
class UserInfo:
    token: Token
    token_update_event: asyncio.Event
    queue: asyncio.Queue


class UserManager:
    def __init__(self) -> None:
        self._users: dict[UUID, UserInfo] = {}
        self._lock = asyncio.Lock()

    async def add(self, token: Token) -> UserInfo:
        # TODO how to handle multiple connections for the same user?
        user_info = UserInfo(token=token, token_update_event=asyncio.Event(), queue=asyncio.PriorityQueue())
        async with self._lock:
            self._users[token.account_id] = user_info
        return user_info

    async def remove(self, token: Token) -> None:
        async with self._lock:
            self._users.pop(token.account_id, None)

    async def update(self, token: Token) -> None:
        async with self._lock:
            try:
                user_info = self._users[token.account_id]
            except KeyError as e:
                logger.error(f"User {token.account_id} is not currently connected, cannot update token")
                raise UserNotConnectedError() from e
            else:
                user_info.token = token
                user_info.token_update_event.set()

    async def send(self, account_id: UUID, msg: str) -> None:
        async with self._lock:
            if user_info := self._users.get(account_id):
                await user_info.queue.put(msg)

    async def broadcast_to_customer(self, customer_id: UUID, msg: str):
        async with self._lock:
            for user_info in self._users.values():
                if user_info.token.customer_id == customer_id:
                    await user_info.queue.put(msg)

    async def broadcast_all(self, msg: str) -> None:
        async with self._lock:
            for user_info in self._users.values():
                await user_info.queue.put(msg)


USER_MANAGER = UserManager()


async def event_generator(request, user_info):
    account_id = user_info.token.account_id

    try:
        while True:
            msg = await user_info.queue.get()
            try:
                decode_token(user_info.token)
            except Exception:
                logger.info(f"User {account_id} token has expired, prompting update")
                yield {"event": "token_expired"}
                # TODO send message to client instructing it to hit the token update route
                await asyncio.wait_for(user_info.token_update_event.wait(), timeout=60)
            yield msg
    except asyncio.CancelledError:
        logger.info(f"event generator for user {account_id} cancelled")
    except asyncio.TimeoutError:
        logger.info(f"User {account_id} failed to update token before timeout, event generator exiting")
    except Exception:
        logger.exception(f"ERROR - {account_id=}")

    await USER_MANAGER.remove(user_info.token)


async def handle_notification(connection, pid, channel, payload):
    payload = json.loads(payload)
    info_to_log = {
        k: payload.get(k) for k in ["type", "table", "upload_id", "job_id", "customer_id", "recipients"]
    }
    logger.info(f"Notification received from DB: {info_to_log}")

    payload["usage_type"] = "jobs" if "job" in payload.pop("table") else "uploads"
    payload["product"] = payload.pop("type")

    # send update to anyone who has access to this upload/job
    data_update_msg = json.dumps({"event": "data_update", "data": payload, "retry": MESSAGE_RETRY_TIMEOUT})
    for recipient_id in payload["recipients"]:
        await USER_MANAGER.send(UUID(recipient_id), data_update_msg)

    # tell any connected user under this customer ID that the upload/job usage has increased for the given product
    usage_update_msg = json.dumps(
        {
            "event": "usage_update",
            "data": {k: payload[k] for k in ("usage_type", "product")},
            "retry": MESSAGE_RETRY_TIMEOUT,
        }
    )
    await USER_MANAGER.broadcast_to_customer(payload["customer_id"], usage_update_msg)


async def listen_to_queue(con):
    """Listen for notifications until the connection closes."""
    await con.add_listener("events", handle_notification)

    db_con_termination_event = asyncio.Event()

    def cancel_listen(connection):
        # TODO also log some info about the connection / why it was closed?
        logger.error("DB CONNECTION TERMINATED")
        db_con_termination_event.set()

    con.add_termination_listener(cancel_listen)

    await db_con_termination_event.wait()


async def run_listener():
    while True:
        try:
            async with asyncpg_pool.acquire() as con:
                await listen_to_queue(con)
        except Exception:
            logger.exception("Error in listener")

        # wait 1 minute before retrying connection
        await asyncio.sleep(60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await asyncpg_pool()

    listener_task = asyncio.create_task(run_listener())

    yield

    listener_task.cancel()
    await listener_task


app = FastAPI(openapi_url=None, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[DASHBOARD_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/public/stream")
async def add_event_source(request: Request, token=Depends(ProtectedAny("TODO scopes"))):
    logger.info(f"User {token.account_id} connected")

    user_info = await USER_MANAGER.add(token)

    return EventSourceResponse(event_generator(request, user_info), send_timeout=5)


@app.post("/public/token")
async def update_token(request: Request, token=Depends(ProtectedAny("TODO scopes"))):
    try:
        await USER_MANAGER.update(token)
    except UserNotConnectedError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)


# TODO remove this
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=1738)
