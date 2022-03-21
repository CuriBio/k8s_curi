FROM python:3.9-slim as venv
RUN apt-get update; \
    apt-get install -y build-essential
    
WORKDIR /app
COPY ./deployments/pheno/services/apiv1/src/requirements.txt ./

RUN python -m venv --copies /app/venv
RUN . /app/venv/bin/activate && pip install -r ./requirements.txt


FROM python:3.9-slim as prod

COPY --from=venv /app/venv /app/venv/
ENV PATH /app/venv/bin:$PATH

WORKDIR /app
COPY ./deployments/pheno/services/apiv1/src/main.py ./
COPY ./deployments/pheno/services/apiv1/src/lib/ ./lib/
COPY ./deployments/pheno/services/apiv1/src/endpoints/ ./endpoints/
COPY ./core/lib/utils/s3.py ./lib/


ENV PYTHONUNBUFFERED 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

