FROM python:3.11.0

RUN pip install kopf kubernetes
COPY operator.py /operator.py
CMD kopf run --standalone /operator.py