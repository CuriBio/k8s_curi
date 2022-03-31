from setuptools import setup, find_packages

setup(
    name='jobs',
    version='0.0.2',
    description='CuriBio jobs queue',
    packages=find_packages(include=['jobs']),
    install_requires=[
        'asyncpg==0.25.0',
    ],
)
