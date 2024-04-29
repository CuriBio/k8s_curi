import asyncio
from calendar import timegm
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import itertools
import json
import time
from uuid import UUID

from fastapi import FastAPI, Request, Depends, status, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from starlette_context import context, request_cycle_context
import structlog
from structlog.contextvars import bind_contextvars, clear_contextvars
from uvicorn.protocols.utils import get_path_with_query_string

from auth import ProtectedAny, Token, ScopeTags
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
        user_info = UserInfo(token=token, token_update_event=asyncio.Event(), queue=asyncio.Queue())
        async with self._lock:
            self._users[UUID(token.account_id)] = user_info
        return user_info

    async def remove(self, token: Token) -> None:
        async with self._lock:
            self._users.pop(UUID(token.account_id), None)

    async def update(self, token: Token) -> None:
        account_id = UUID(token.account_id)
        async with self._lock:
            try:
                user_info = self._users[account_id]
            except KeyError as e:
                logger.error(f"User {account_id} is not currently connected, cannot update token")
                raise UserNotConnectedError() from e
            else:
                user_info.token = token
                user_info.token_update_event.set()

    async def send(self, account_id: UUID, msg: dict[str, str]) -> None:
        async with self._lock:
            if user_info := self._users.get(account_id):
                await user_info.queue.put(msg)

    async def broadcast_to_customer(self, customer_id: UUID, msg: dict[str, str]):
        async with self._lock:
            for user_info in self._users.values():
                if UUID(user_info.token.customer_id) == customer_id:
                    await user_info.queue.put(msg)

    async def broadcast_all(self, msg: str) -> None:
        async with self._lock:
            for user_info in self._users.values():
                await user_info.queue.put(msg)


USER_MANAGER = UserManager()


async def event_generator(request, user_info):
    account_id = UUID(user_info.token.account_id)

    id_iter = itertools.count()

    try:
        while True:
            msg = await user_info.queue.get()
            # TODO fix this, can't use decode_token
            if timegm(datetime.now(tz=timezone.utc).utctimetuple()) > user_info.token.exp:
                yield {
                    "event": "token_expired",
                    "id": next(id_iter),
                    "data": "",
                    "retry": MESSAGE_RETRY_TIMEOUT,
                }
                logger.info(f"User {account_id} token has expired, prompting update")
                await asyncio.wait_for(user_info.token_update_event.wait(), timeout=60)
            yield msg | {"id": next(id_iter), "retry": MESSAGE_RETRY_TIMEOUT}
    except asyncio.CancelledError:
        logger.info(f"event generator for user {account_id} cancelled")
    except asyncio.TimeoutError:
        logger.info(f"User {account_id} failed to update token before timeout, event generator exiting")
    except Exception:
        logger.exception(f"ERROR - {account_id=}")

    await USER_MANAGER.remove(user_info.token)


async def handle_notification(connection, pid, channel, payload):
    try:
        payload = json.loads(payload)
        info_to_log = {
            k: payload.get(k)
            for k in [
                "user_id",
                "type",
                "table",
                "status",
                "upload_id",
                "job_id",
                "customer_id",
                "recipients",
                "usage",
            ]
        }
        logger.info(f"Notification received from DB: {info_to_log}")

        if "job" in payload.pop("table"):
            payload["usage_type"] = "jobs"
            payload["id"] = payload.pop("job_id")
        else:
            payload["usage_type"] = "uploads"
        payload["product"] = payload.pop("type")

        # send update to anyone who has access to this upload/job
        data_update_msg = {"event": "data_update", "data": json.dumps(payload)}
        for recipient_id in payload.pop("recipients"):
            await USER_MANAGER.send(UUID(recipient_id), data_update_msg)

        # send the new job or upload count to any connected user under this customer ID
        usage_update_msg = {
            "event": "usage_update",
            "data": json.dumps({k: payload[k] for k in ("usage_type", "product", "usage")}),
        }
        await USER_MANAGER.broadcast_to_customer(UUID(payload["customer_id"]), usage_update_msg)
    except Exception:
        logger.exception("ERROR")


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
            pgpool = await asyncpg_pool()
            async with pgpool.acquire() as con:
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


@app.middleware("http")
async def middleware(request: Request, call_next) -> Response:
    # clear previous request variables
    clear_contextvars()
    # get request details for logging
    if (client_ip := request.headers.get("X-Forwarded-For")) is None:
        client_ip = f"{request.client.host}:{request.client.port}"

    url = get_path_with_query_string(request.scope)
    http_method = request.method
    http_version = request.scope["http_version"]
    start_time = time.perf_counter_ns()

    bind_contextvars(url=str(request.url), method=http_method, client_ip=client_ip)

    with request_cycle_context({}):
        response = await call_next(request)

        process_time = time.perf_counter_ns() - start_time
        status_code = response.status_code

        logger.info(
            f"""{client_ip} - "{http_method} {url} HTTP/{http_version}" {status_code}""",
            status_code=status_code,
            duration=process_time / 10**9,
            **context,
        )

    return response


@app.get("/public/stream")
async def add_event_source(request: Request, token=Depends(ProtectedAny(tag=ScopeTags.PULSE3D_READ))):
    logger.info(f"User {token.account_id} connected")

    user_info = await USER_MANAGER.add(token)

    return EventSourceResponse(event_generator(request, user_info), send_timeout=5)


@app.post("/public/token")
async def update_token(request: Request, token=Depends(ProtectedAny(tag=ScopeTags.PULSE3D_READ))):
    try:
        await USER_MANAGER.update(token)
    except UserNotConnectedError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
