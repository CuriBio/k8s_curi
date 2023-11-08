FROM python:3.11-alpine as venv

WORKDIR /app
COPY ./deployments/apiv2/services/mantarray/src/requirements.txt ./
COPY ./core/lib/ ./lib/

RUN python -m venv --copies /app/venv
RUN . /app/venv/bin/activate && pip install -r ./requirements.txt && pip install ./lib/auth && pip install ./lib/utils

FROM python:3.11-alpine as prod

RUN addgroup -S main_group
RUN adduser -S main_user --ingroup main_group
USER main_user:main_group

COPY --chown=main_user:main_group --from=venv /app/venv /app/venv/
ENV PATH /app/venv/bin:$PATH

WORKDIR /app
COPY --chown=main_user:main_group ./deployments/apiv2/services/mantarray/src/main.py ./
COPY --chown=main_user:main_group ./deployments/apiv2/services/mantarray/src/models/ ./models
COPY --chown=main_user:main_group ./deployments/apiv2/services/mantarray/src/core ./core
COPY --chown=main_user:main_group ./deployments/apiv2/services/mantarray/disable_log_config.yaml ./

ENV PYTHONUNBUFFERED 1
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9000", "--reload", "--log-config", "disable_log_config.yaml","--header", "X-Content-Type-Options:nosniff", "--header", "Strict-Transport-Security:max-age=31536000"]
