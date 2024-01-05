from setuptools import setup, find_packages

setup(
    name="auth",
    version="0.0.2",
    description="CuriBio auth utils",
    packages=find_packages(include=["auth"]),
    install_requires=[
        "pydantic==2.5.2",
        "starlette==0.27.0",
        "fastapi==0.105.0",
        "pyjwt==2.3.0",
        "immutabledict==3.0.0",
    ],
)
