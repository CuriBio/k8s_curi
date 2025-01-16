FROM python:3.11-alpine AS venv

WORKDIR /app

RUN python -m venv --copies /app/venv
RUN . /app/venv/bin/activate && pip install kopf kubernetes

FROM python:3.11-alpine AS prod

RUN addgroup -S main_group
RUN adduser -S main_user --ingroup main_group
USER main_user:main_group

COPY --chown=main_user:main_group --from=venv /app/venv /app/venv/
ENV PATH=/app/venv/bin:$PATH

WORKDIR /app
COPY --chown=main_user:main_group ./jobs/jobs-operator/jobs-operator/src/main.py ./

CMD kopf run -A --standalone main.py --verbose
