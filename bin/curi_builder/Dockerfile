FROM alpine:latest as venv
RUN apk add --no-cache --update python3 py3-pip git

WORKDIR /builder
COPY ./setup.py /builder
COPY ./builder /builder/builder

RUN python3 -m venv --copies /venv
RUN . /venv/bin/activate && pip3 install -e .

RUN wget https://releases.hashicorp.com/terraform/1.2.5/terraform_1.2.5_linux_amd64.zip \
  && unzip terraform_1.2.5_linux_amd64.zip \
  && mv terraform /venv/bin \
  && rm terraform_1.2.5_linux_amd64.zip

ENV PATH /venv/bin:$PATH
ENV PYTHONUNBUFFERED 1

