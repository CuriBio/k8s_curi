FROM python:3.9-slim as venv

WORKDIR /app

RUN python -m venv --copies /app/venv
RUN . /app/venv/bin/activate && pip install kopf kubernetes

FROM python:3.9-slim as prod

RUN useradd main_user && groupadd main_group
USER main_user:main_group

COPY --chown=main_user:main_group --from=venv /app/venv /app/venv/
ENV PATH /app/venv/bin:$PATH

WORKDIR /app
COPY --chown=main_user:main_group ./jobs/jobs-operator/jobs-operator/src/main.py ./

CMD kopf run -A --standalone main.py --verbose
