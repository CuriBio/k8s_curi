#FROM python:3.9-slim as venv
#RUN apt update -y && apt install -y git jq
FROM alpine:latest as venv
RUN apk add --no-cache --update python3 py3-pip git

WORKDIR /builder
COPY ./setup.py /builder
COPY ./builder /builder/builder

RUN python3 -m venv --copies /venv
RUN . /venv/bin/activate && pip3 install -e .

ENV PATH /venv/bin:$PATH
ENV PYTHONUNBUFFERED 1
#CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

