FROM python:3.9-slim as venv
RUN apt-get update; \
    apt-get install -y build-essential

WORKDIR /app
COPY ./deployments/apiv2/services/users/src/requirements.txt ./
COPY ./core/lib/auth ./lib/auth
COPY ./core/lib/utils ./lib/utils

RUN python -m venv --copies /app/venv
RUN . /app/venv/bin/activate && pip install -r ./requirements.txt && pip install ./lib/auth && pip install ./lib/utils


FROM python:3.9-slim as prod

COPY --from=venv /app/venv /app/venv/
ENV PATH /app/venv/bin:$PATH

WORKDIR /app
COPY ./deployments/apiv2/services/users/src/core/ ./core
COPY ./deployments/apiv2/services/users/src/templates/ ./templates
COPY ./deployments/apiv2/services/users/src/models/ ./models
COPY ./deployments/apiv2/services/users/src/main.py ./
COPY ./deployments/apiv2/services/users/log_config.yaml ./

ENV PYTHONUNBUFFERED 1
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9001", "--reload", "--log-config", "log_config.yaml"]

