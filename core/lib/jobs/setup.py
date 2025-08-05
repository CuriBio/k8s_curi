from setuptools import find_packages, setup

setup(
    name="jobs",
    version="0.0.3",
    description="CuriBio jobs queue",
    packages=find_packages(include=["jobs"]),
    install_requires=[
        "asyncpg==0.27.0",
    ],
)
