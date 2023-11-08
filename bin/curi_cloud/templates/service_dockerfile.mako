FROM python:3.11-alpine as venv

WORKDIR /app
COPY ./src/requirements.txt ./

#### virtualenv
RUN python -m venv --copies /app/venv
RUN . /app/venv/bin/activate && pip install -r ./requirements.txt


FROM python:3.11-alpine as prod

#### copy Python dependencies from build image
COPY --from=venv /app/venv /app/venv/
ENV PATH /app/venv/bin:$PATH

WORKDIR /app
COPY ./src/main.py ./

ENV PYTHONUNBUFFERED 1
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

