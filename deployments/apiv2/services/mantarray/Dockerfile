FROM python:3.9-slim as venv

WORKDIR /app
COPY ./deployments/apiv2/services/mantarray/src/requirements.txt ./

RUN python -m venv --copies /app/venv
RUN . /app/venv/bin/activate && pip install -r ./requirements.txt


FROM python:3.9-slim as prod

COPY --from=venv /app/venv /app/venv/
ENV PATH /app/venv/bin:$PATH

WORKDIR /app
COPY ./deployments/apiv2/services/mantarray/src/main.py ./
COPY ./deployments/apiv2/services/mantarray/src/utils/ ./utils/
COPY ./deployments/apiv2/services/mantarray/src/templates/ ./templates

ENV PYTHONUNBUFFERED 1
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9000", "--reload"]
