from setuptools import setup, find_packages

setup(
    name='utils',
    version='0.0.1',
    description='CuriBio utils',
    packages=find_packages(include=['utils']),
    install_requires=[
        'boto3==1.21.24',
        'botocore==1.24.24',
        'jmespath==1.0.0',
        'python-dateutil==2.8.2',
        's3transfer==0.5.2',
        'six==1.16.0',
        'urllib3==1.26.9',
    ],
)
