FROM python:3.9-slim as venv

RUN useradd main_user && groupadd main_group
USER main_user:main_group

WORKDIR /app
COPY ./deployments/apiv2/services/mantarray/src/requirements.txt ./
COPY ./core/lib/ ./lib/

RUN python -m venv --copies /app/venv
RUN . /app/venv/bin/activate && pip install -r ./requirements.txt && pip install ./lib/auth && pip install ./lib/utils

FROM python:3.9-slim as prod

COPY --from=venv /app/venv /app/venv/
ENV PATH /app/venv/bin:$PATH

WORKDIR /app
COPY ./deployments/apiv2/services/mantarray/src/main.py ./
COPY ./deployments/apiv2/services/mantarray/src/core ./core
COPY ./deployments/apiv2/services/mantarray/src/templates/ ./templates
COPY ./deployments/apiv2/services/mantarray/log_config.yaml ./

ENV PYTHONUNBUFFERED 1
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9000", "--reload", "--log-config", "log_config.yaml"]
