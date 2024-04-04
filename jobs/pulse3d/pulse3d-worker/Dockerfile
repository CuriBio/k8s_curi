FROM python:3.11-slim as venv

WORKDIR /app
COPY ./jobs/pulse3d/pulse3d-worker/src/requirements.txt ./
COPY ./core/lib/jobs ./lib/jobs
COPY ./core/lib/utils ./lib/utils

# Following args are required for pushing to the test cluster, you need to add and export modl access keys to get pulse3d repo
ARG CODE_ARTIFACT_ACCOUNT_ID
ARG CODE_ARTIFACT_ACCESS_KEY
ARG CODE_ARTIFACT_ACCESS_KEY_ID
ENV AWS_ACCOUNT_ID=$CODE_ARTIFACT_ACCOUNT_ID
ENV AWS_SECRET_ACCESS_KEY=$CODE_ARTIFACT_ACCESS_KEY
ENV AWS_ACCESS_KEY_ID=$CODE_ARTIFACT_ACCESS_KEY_ID

RUN pip install awscli

RUN python -m venv --copies /app/venv && \
    . /app/venv/bin/activate && \
    export CODEARTIFACT_AUTH_TOKEN=$(aws codeartifact get-authorization-token --domain curibio --domain-owner $AWS_ACCOUNT_ID --region us-east-2 --query authorizationToken --output text) && \
    pip install -r ./requirements.txt --extra-index-url=https://aws:$CODEARTIFACT_AUTH_TOKEN@curibio-$AWS_ACCOUNT_ID.d.codeartifact.us-east-2.amazonaws.com/pypi/pulse3d/simple/ && \
    pip install ./lib/jobs && \
    pip install ./lib/utils

FROM python:3.11-slim as prod
ARG DEBIAN_FRONTEND=noninteractive

RUN useradd main_user && groupadd main_group

USER main_user:main_group

COPY --from=venv --chown=main_user:main_group /app/venv /app/venv/
ENV PATH /app/venv/bin:$PATH

WORKDIR /app
COPY --chown=main_user:main_group ./jobs/pulse3d/pulse3d-worker/src/main.py ./
COPY --chown=main_user:main_group ./jobs/pulse3d/pulse3d-worker/src/lib ./lib

ENV PYTHONUNBUFFERED 1
CMD ["python", "main.py"]
