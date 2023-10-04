FROM python:3.11-alpine as venv

WORKDIR /app
COPY ./jobs/pulse3d/pulse3d-worker/src/requirements.txt ./
COPY ./core/lib/jobs ./lib/jobs
COPY ./core/lib/utils ./lib/utils

RUN python -m venv --copies /app/venv && \
    . /app/venv/bin/activate && \
    pip install -r ./requirements.txt && \
    pip install ./lib/jobs && \
    pip install ./lib/utils

FROM python:3.11-alpine as prod

ARG DEBIAN_FRONTEND=noninteractive

RUN addgroup -S main_group
RUN adduser -S main_user --ingroup main_group
USER main_user:main_group

COPY --from=venv --chown=main_user:main_group /app/venv /app/venv/
ENV PATH /app/venv/bin:$PATH

WORKDIR /app
COPY --chown=main_user:main_group ./jobs/pulse3d/pulse3d-worker/src/main.py ./
COPY --chown=main_user:main_group ./jobs/pulse3d/pulse3d-worker/src/lib ./lib

ENV PYTHONUNBUFFERED 1
CMD ["python", "main.py"]

