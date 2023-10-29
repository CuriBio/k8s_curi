FROM python:3.11-slim as venv

WORKDIR /app
COPY ./core/lib/utils ./lib/utils

RUN python -m venv --copies /app/venv
RUN . /app/venv/bin/activate && pip install asyncpg asyncio kubernetes structlog && pip install ./lib/utils

FROM python:3.11-slim as prod

RUN useradd main_user && groupadd main_group
USER main_user:main_group

COPY --chown=main_user:main_group --from=venv /app/venv /app/venv/
ENV PATH /app/venv/bin:$PATH

WORKDIR /app
COPY --chown=main_user:main_group ./jobs/queue-processor/src/main.py ./

CMD ["python", "main.py"]
