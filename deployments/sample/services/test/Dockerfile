#FROM ubuntu:22.04 as venv
FROM python:3.9-slim as venv
RUN apt-get update; \
    apt-get install -y build-essential

#RUN apt-get -y update && apt-get -y install build-essentials python3.9 python3-pip
WORKDIR /app
COPY ./deployments/sample/services/test/src/requirements.txt ./
COPY ./core/lib/jobs ./lib/jobs

RUN python -m venv --copies /app/venv
RUN . /app/venv/bin/activate && pip install -r ./requirements.txt && pip install ./lib/jobs



FROM python:3.9-slim as prod

COPY --from=venv /app/venv /app/venv/
ENV PATH /app/venv/bin:$PATH

WORKDIR /app
#COPY ./src/main.py ./
COPY ./deployments/sample/services/test/src/main.py ./

ENV PYTHONUNBUFFERED 1
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

