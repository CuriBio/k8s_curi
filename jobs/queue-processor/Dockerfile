FROM python:3.11.0
RUN pip install asyncpg asyncio kubernetes
COPY src/main.py /main.py


CMD ["python", "main.py"]
