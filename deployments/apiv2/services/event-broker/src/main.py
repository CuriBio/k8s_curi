import logging
import datetime
import sys

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
import asyncio
import uvicorn

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
stream_handler = logging.StreamHandler(sys.stdout)
log_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
stream_handler.setFormatter(log_formatter)
logger.addHandler(stream_handler)

app = FastAPI()

# TODO update this
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"]
)


# TODO could move this into psql
class QueueManager:
    def __init__(self):
        self._queues: dict[int, asyncio.Queue] = {}
        self._lock = asyncio.Lock()

    async def add(self, uid, queue):
        async with self._lock:
            self._queues[uid] = queue

    async def remove(self, uid):
        async with self._lock:
            self._queues.pop(uid, None)

    async def broadcast(self, msg):
        async with self._lock:
            for queue in self._queues.values():
                await queue.put({"event": "new_message", "id": "message_id", "retry": 15000, "data": msg})


QUEUE_MANAGER = QueueManager()


async def event_generator(request, uid, msg_queue):
    tasks = {
        asyncio.create_task(periodic_msg(msg_queue, uid))
        # TODO listen to psql
    }

    try:
        while True:
            msg = await msg_queue.get()
            # TODO make sure token isn't expired, if so, send a message to client instructing it to reconnect with a new token
            yield msg
    except asyncio.CancelledError:
        logger.info(f"event generator for ID={uid} cancelled")
    except Exception:
        logger.exception(f"ERROR - ID: {uid}")

    await QUEUE_MANAGER.remove(uid)

    for task in tasks:
        if not task.done():
            task.cancel()

            try:
                await task
            except asyncio.CancelledError:
                pass
            except BaseException:
                logger.exception("ERROR")


async def periodic_msg(msg_queue, uid):
    try:
        while True:
            await msg_queue.put(
                {
                    "event": "new_message",
                    "id": "message_id",
                    "retry": 15000,
                    "data": f"Counter value {datetime.datetime.utcnow()}",
                }
            )

            await asyncio.sleep(5)
    except Exception:
        logger.exception(f"ERROR - ID: {uid}")


# TODO protect with token
@app.get("/stream/{uid}")
async def add_event_source(request: Request, uid: int):
    logger.info(f"ID={uid} connected")

    # TODO store token along with queue, also don't create a new queue if one already exists
    msg_queue = asyncio.Queue()
    await QUEUE_MANAGER.add(uid, msg_queue)

    return EventSourceResponse(event_generator(request, uid, msg_queue), send_timeout=5)


# TODO make this only available internally
@app.post("/stream/{msg}")
async def broadcast_msg(request: Request, msg: str):
    logger.info(f"Broadcasting msg: {msg}")

    await QUEUE_MANAGER.broadcast(msg)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=1738)
