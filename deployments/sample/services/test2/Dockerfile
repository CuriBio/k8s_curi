FROM python:3.9-slim as venv

WORKDIR /app
COPY ./deployments/sample/services/test2/src/requirements.txt ./

RUN python -m venv --copies /app/venv
RUN . /app/venv/bin/activate && pip install -r ./requirements.txt


FROM python:3.9-slim as prod

COPY --from=venv /app/venv /app/venv/
ENV PATH /app/venv/bin:$PATH

WORKDIR /app
COPY ./deployments/sample/services/test2/src/main.py ./

ENV PYTHONUNBUFFERED 1
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7000", "--reload"]

