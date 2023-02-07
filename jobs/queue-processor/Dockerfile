FROM python:3.11.0
RUN pip install asyncpg asyncio kubernetes
COPY src/main.py /main.py

# RUN useradd main_user && groupadd main_group
# RUN chown -R main_user:main_group /
# USER main_user:main_group

CMD ["python", "main.py"]
