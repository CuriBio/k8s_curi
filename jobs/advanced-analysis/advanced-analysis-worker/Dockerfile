FROM python:3.11-slim as venv

WORKDIR /app
COPY ./jobs/advanced-analysis/advanced-analysis-worker/src/requirements.txt ./
COPY ./core/lib/jobs ./lib/jobs
COPY ./core/lib/utils ./lib/utils

# Following args are required for pushing to the test cluster, you need to add and export modl access keys to get advanced analysis repo
# ARG CODE_ARTIFACT_ACCOUNT_ID
# ARG CODE_ARTIFACT_ACCESS_KEY
# ARG CODE_ARTIFACT_ACCESS_KEY_ID
# ENV AWS_ACCOUNT_ID=$CODE_ARTIFACT_ACCOUNT_ID
# ENV AWS_SECRET_ACCESS_KEY=$CODE_ARTIFACT_ACCESS_KEY
# ENV AWS_ACCESS_KEY_ID=$CODE_ARTIFACT_ACCESS_KEY_ID

# RUN apt update
# RUN apt install awscli --yes

RUN python -m venv --copies /app/venv && \
    . /app/venv/bin/activate && \
    pip install -r ./requirements.txt && \
    pip install ./lib/jobs && \
    pip install ./lib/utils

FROM python:3.11-slim as prod
ARG DEBIAN_FRONTEND=noninteractive

RUN useradd main_user && groupadd main_group

USER main_user:main_group

COPY --from=venv --chown=main_user:main_group /app/venv /app/venv/
ENV PATH /app/venv/bin:$PATH

WORKDIR /app
COPY --chown=main_user:main_group ./jobs/advanced-analysis/advanced-analysis-worker/src/main.py ./
# TODO remove this once advanced analysis package is downloaded from code artifact
COPY --chown=main_user:main_group ./jobs/advanced-analysis/advanced-analysis-worker/src/advanced_analysis.py ./

ENV PYTHONUNBUFFERED 1
CMD ["python", "main.py"]
