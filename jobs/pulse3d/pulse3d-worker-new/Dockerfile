FROM python:3.11-slim AS venv

WORKDIR /app
COPY ./jobs/pulse3d/pulse3d-worker-new/src/requirements.txt ./
COPY ./core/lib/jobs ./lib/jobs
COPY ./core/lib/utils ./lib/utils

RUN apt update
RUN apt install awscli --yes

RUN --mount=type=secret,id=CODE_ARTIFACT_ACCOUNT_ID,env=AWS_ACCOUNT_ID \
    --mount=type=secret,id=CODE_ARTIFACT_ACCESS_KEY,env=AWS_SECRET_ACCESS_KEY \
    --mount=type=secret,id=CODE_ARTIFACT_ACCESS_KEY_ID,env=AWS_ACCESS_KEY_ID \
    python -m venv --copies /app/venv && \
    . /app/venv/bin/activate && \
    export CODEARTIFACT_AUTH_TOKEN=$(aws codeartifact get-authorization-token --domain curibio --domain-owner $AWS_ACCOUNT_ID --region us-east-2 --query authorizationToken --output text) && \
    pip install -r ./requirements.txt --extra-index-url=https://aws:$CODEARTIFACT_AUTH_TOKEN@curibio-$AWS_ACCOUNT_ID.d.codeartifact.us-east-2.amazonaws.com/pypi/pulse3d/simple/ && \
    pip install ./lib/jobs && \
    pip install ./lib/utils

FROM python:3.11-slim AS prod
ARG DEBIAN_FRONTEND=noninteractive

RUN useradd main_user && groupadd main_group

USER main_user:main_group

COPY --from=venv --chown=main_user:main_group /app/venv /app/venv/
ENV PATH=/app/venv/bin:$PATH

WORKDIR /app
COPY --chown=main_user:main_group ./jobs/pulse3d/pulse3d-worker-new/src/main.py ./

ENV PYTHONUNBUFFERED=1
CMD ["python", "main.py"]
