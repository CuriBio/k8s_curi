FROM alpine:latest as venv
RUN apk add --no-cache --update python3 python3-dev py3-pip git build-base

WORKDIR /builder
COPY ./setup.py /builder
COPY ./builder /builder/builder

RUN python3 -m venv --copies /venv
RUN . /venv/bin/activate && pip3 install -e .

RUN wget https://releases.hashicorp.com/terraform/1.5.2/terraform_1.5.2_linux_amd64.zip \
  && unzip terraform_1.5.2_linux_amd64.zip \
  && mv terraform /venv/bin \
  && rm terraform_1.5.2_linux_amd64.zip

# currently not switching to non-root user for this image

ENV PATH /venv/bin:$PATH
ENV PYTHONUNBUFFERED 1

