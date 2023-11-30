FROM python:3.11-slim as venv

WORKDIR /app
COPY ./jobs/pulse3d/pulse3d-worker_rewrite/src/requirements.txt ./
COPY ./core/lib/jobs ./lib/jobs
COPY ./core/lib/utils ./lib/utils

RUN python -m venv --copies /app/venv && \
    . /app/venv/bin/activate && \
    pip install -r ./requirements.txt && \
    pip install ./lib/jobs && \
    pip install ./lib/utils

RUN echo "Getting CodeArtifact Auth"

ARG ACCESS_KEY
ARG ACCESS_KEY_ID

ENV AWS_SECRET_ACCESS_KEY=$ACCESS_KEY
ENV AWS_ACCESS_KEY_ID=$ACCESS_KEY_ID
# # pip install -r requirements.txt --extra-index-url=https://aws:$CODEARTIFACT_AUTH_TOKEN@curibio-245339368379.d.codeartifact.us-east-2.amazonaws.com/pypi/pulse3d/simple/
RUN pip install awscli && echo $AWS_SECRET_ACCESS_KEY && export AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY && export AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID export CODEARTIFACT_AUTH_TOKEN=$(aws codeartifact get-authorization-token --domain curibio --domain-owner 245339368379 --region us-east-2 --query authorizationToken --output text) && pip install pulse3d==1.0.0rc6 --extra-index-url=https://aws:$CODEARTIFACT_AUTH_TOKEN@curibio-245339368379.d.codeartifact.us-east-2.amazonaws.com/pypi/pulse3d/simple/

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

