FROM python:3.11-alpine as venv

WORKDIR /app
COPY ./deployments/pheno/services/apiv1/src/requirements.txt ./
COPY ./core/lib/utils ./lib/utils


RUN python -m venv --copies /app/venv
RUN . /app/venv/bin/activate && pip install -r ./requirements.txt && pip install ./lib/utils


FROM python:3.11-alpine as prod

COPY --from=venv /app/venv /app/venv/
ENV PATH /app/venv/bin:$PATH

RUN addgroup -S main_group
RUN adduser -S main_user --ingroup main_group
USER main_user:main_group

WORKDIR /app
COPY ./deployments/pheno/services/apiv1/src/main.py ./
COPY ./deployments/pheno/services/apiv1/src/lib/ ./lib/
COPY ./deployments/pheno/services/apiv1/src/endpoints/ ./endpoints/

ENV PYTHONUNBUFFERED 1
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

