FROM python:3.11.0

WORKDIR /app
RUN pip install kopf kubernetes
COPY src/main.py /main.py

RUN useradd main_user && groupadd main_group
RUN chown -R main_user:main_group /app
USER main_user:main_group

CMD kopf run -A --standalone /main.py --verbose
