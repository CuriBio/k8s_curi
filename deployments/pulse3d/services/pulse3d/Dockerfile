FROM python:3.11-slim as venv
WORKDIR /app
COPY ./deployments/pulse3d/services/pulse3d/src/requirements.txt ./
COPY ./core/lib/auth ./lib/auth
COPY ./core/lib/utils ./lib/utils
COPY ./core/lib/jobs ./lib/jobs

ARG CODE_ARTIFACT_ACCOUNT_ID
ARG CODE_ARTIFACT_ACCESS_KEY
ARG CODE_ARTIFACT_ACCESS_KEY_ID
ENV AWS_ACCOUNT_ID=$CODE_ARTIFACT_ACCOUNT_ID
ENV AWS_SECRET_ACCESS_KEY=$CODE_ARTIFACT_ACCESS_KEY
ENV AWS_ACCESS_KEY_ID=$CODE_ARTIFACT_ACCESS_KEY_ID

RUN bash -c "echo $AWS_ACCOUNT_ID"

RUN pip install awscli

RUN python -m venv --copies /app/venv && \
    . /app/venv/bin/activate && \
    export CODEARTIFACT_AUTH_TOKEN=$(aws codeartifact get-authorization-token --domain curibio --domain-owner $AWS_ACCOUNT_ID --region us-east-2 --query authorizationToken --output text) && \
    pip install -r ./requirements.txt --extra-index-url=https://aws:$CODEARTIFACT_AUTH_TOKEN@curibio-$AWS_ACCOUNT_ID.d.codeartifact.us-east-2.amazonaws.com/pypi/pulse3d/simple/ && \
    pip install ./lib/auth && \
    pip install ./lib/utils && \
    pip install ./lib/jobs


FROM python:3.11-slim as prod

RUN useradd -ms /bin/bash main_user && groupadd main_group
USER main_user:main_group

COPY --chown=main_user:main_group --from=venv /app/venv /app/venv/
ENV PATH /app/venv/bin:$PATH

WORKDIR /app
COPY --chown=main_user:main_group ./deployments/pulse3d/services/pulse3d/src/main.py ./
COPY --chown=main_user:main_group ./deployments/pulse3d/services/pulse3d/src/core/ ./core
COPY --chown=main_user:main_group ./deployments/pulse3d/services/pulse3d/src/models/ ./models
COPY --chown=main_user:main_group ./deployments/pulse3d/services/pulse3d/disable_log_config.yaml ./

ENV PYTHONUNBUFFERED 1
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--log-config", "disable_log_config.yaml", "--header", "X-Content-Type-Options:nosniff", "--header", "Strict-Transport-Security:max-age=31536000"]
