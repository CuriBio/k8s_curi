from setuptools import setup, find_packages

setup(
    name="utils",
    version="0.0.1",
    description="CuriBio utils",
    packages=find_packages(include=["utils"]),
    install_requires=[
        "asyncpg==0.27.0",
        "boto3==1.28.6",
        "botocore==1.31.6",
        "jmespath==1.0.0",
        "fastapi-mail==1.4.1",
        "pydantic==2.5.2",
        "python-dateutil==2.8.2",
        "s3transfer==0.6.1",
        "six==1.16.0",
        "urllib3==1.26.9",
        "structlog==23.2.0",
        "stream-zip==0.0.48",
    ],
)
