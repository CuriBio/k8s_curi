FROM python:3.9-slim as venv

WORKDIR /app
COPY ./src/requirements.txt ./

RUN python -m venv --copies /app/venv
RUN . /app/venv/bin/activate && pip install -r ./requirements.txt


FROM nvidia/cuda:11.3.1-base-ubuntu20.04 as prod

RUN apt-get update && apt-get install -y --no-install-recommends libexpat-dev python3.9 python3.9-dev

COPY --from=venv /app/venv /app/venv/
ENV PATH /app/venv/bin:$PATH

WORKDIR /app
COPY ./src/main.py ./
COPY ./src/lib ./
COPY ./src/pytorch ./

ENV PYTHONUNBUFFERED 1
CMD ["python", "main.py"]

