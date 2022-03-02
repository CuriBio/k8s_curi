FROM nvidia/cuda:11.3.1-base-ubuntu20.04 as venv

WORKDIR /app
COPY ./src/requirements.txt ./

RUN apt-get update && apt-get install -y --no-install-recommends \
        apt-utils \
        python3.9 \
        python3-dev \
        python3-pip \
        python3-venv \
        python3-setuptools \
        && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get update

RUN python3 -m venv --copies /app/venv
RUN . /app/venv/bin/activate

RUN python3 -m pip install --upgrade pip && \
    pip install --upgrade torch==1.10.2 && \
    pip install --upgrade torchvision==0.11.3 \
    pip install --upgrade scikit-image

RUN pip install -r ./requirements.txt



FROM nvidia/cuda:11.3.1-base-ubuntu20.04 as prod

COPY --from=venv /app/venv /app/venv/
ENV PATH /app/venv/bin:$PATH

WORKDIR /app
COPY ./src/main.py ./
COPY ./src/lib ./
COPY ./src/pytorch ./

ENV PYTHONUNBUFFERED 1
CMD ["python", "main.py"]

