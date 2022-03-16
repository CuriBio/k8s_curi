from setuptools import setup, find_packages

setup(
    name='auth',
    version='0.0.1',
    description='CuriBio jobs queue',
    packages=find_packages(include=['auth']),
    install_requires=[
        'pydantic==1.9.0',
        'starlette==0.16.0',
        'fastapi==0.70.1',
        'pyjwt==2.3.0',
    ],
)
