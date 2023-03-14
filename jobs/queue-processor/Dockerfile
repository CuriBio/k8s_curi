FROM python:3.9-slim as venv

WORKDIR /app

RUN python -m venv --copies /app/venv
RUN . /app/venv/bin/activate && pip install asyncpg asyncio kubernetes

FROM python:3.9-slim as prod

COPY --from=venv /app/venv /app/venv/
ENV PATH /app/venv/bin:$PATH

WORKDIR /app
COPY ./jobs/queue-processor/src/main.py ./

RUN useradd main_user && groupadd main_group
RUN chown -R main_user:main_group /app
USER main_user:main_group

CMD ["python", "main.py"]
