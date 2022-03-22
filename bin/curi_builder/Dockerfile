FROM alpine:latest as venv
RUN apk add --no-cache --update python3 py3-pip git

WORKDIR /builder
COPY ./setup.py /builder
COPY ./builder /builder/builder

RUN python3 -m venv --copies /venv
RUN . /venv/bin/activate && pip3 install -e .

ENV PATH /venv/bin:$PATH
ENV PYTHONUNBUFFERED 1

