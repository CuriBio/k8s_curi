FROM python:3.11-alpine as venv

WORKDIR /app
COPY ./jobs/pheno/pheno-worker/src/requirements.txt ./

RUN python -m venv --copies /app/venv
RUN . /app/venv/bin/activate && pip install -r ./requirements.txt


FROM nvidia/cuda:11.3.1-base-ubuntu20.04 as prod
ARG DEBIAN_FRONTEND=noninteractive


RUN apt-get update && apt-get install -y --no-install-recommends build-essential libglib2.0-0 libgtk2.0-dev libexpat-dev libgl1 libpython3.9-dev python3.9

COPY --from=venv /app/venv /app/venv/
ENV PATH /app/venv/bin:$PATH

WORKDIR /app
COPY ./jobs/pheno/pheno-worker/src/main.py ./
COPY ./jobs/pheno/pheno-worker/src/lib ./lib
COPY ./jobs/pheno/pheno-worker/src/pytorch ./pytorch
COPY ./core/lib/utils/s3.py ./lib/

RUN addgroup -S main_group
RUN adduser -S main_user --ingroup main_group
USER main_user:main_group

ENV PYTHONUNBUFFERED 1
CMD ["python", "main.py"]

