FROM python:3.9-slim as venv

WORKDIR /app
COPY ./deployments/pulse3d/services/pulse3d/src/requirements.txt ./
COPY ./core/lib/auth ./lib/auth
COPY ./core/lib/utils ./lib/utils
COPY ./core/lib/jobs ./lib/jobs

RUN python -m venv --copies /app/venv
RUN . /app/venv/bin/activate && pip install -r ./requirements.txt && pip install ./lib/auth && pip install ./lib/utils && pip install ./lib/jobs


FROM python:3.9-slim as prod

RUN useradd -ms /bin/bash main_user && groupadd main_group
USER main_user:main_group

COPY --chown=main_user:main_group --from=venv /app/venv /app/venv/
ENV PATH /app/venv/bin:$PATH

WORKDIR /app
COPY --chown=main_user:main_group ./deployments/pulse3d/services/pulse3d/src/main.py ./
COPY --chown=main_user:main_group ./deployments/pulse3d/services/pulse3d/src/core/ ./core
COPY --chown=main_user:main_group ./deployments/pulse3d/services/pulse3d/src/models/ ./models
COPY --chown=main_user:main_group ./deployments/pulse3d/services/pulse3d/log_config.yaml ./


RUN useradd main_user && groupadd main_group
USER main_user:main_group

ENV PYTHONUNBUFFERED 1
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--log-config", "log_config.yaml"]
