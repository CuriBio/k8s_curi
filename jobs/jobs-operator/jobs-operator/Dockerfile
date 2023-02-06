FROM python:3.11.0

RUN pip install kopf kubernetes
COPY src/main.py /main.py

CMD kopf run -A --standalone /main.py --verbose
