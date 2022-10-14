from setuptools import setup

setup(
    name="builder",
    version="0.1",
    packages=["builder"],
    install_requires=[
        "requests>=2.27.1",
        "alembic>=1.7.7",
        "SQLAlchemy>=1.4.35",
        "psycopg2-binary>=2.9.3",
        "argon2-cffi>=21.3.0",
        "argon2-cffi-bindings>=21.2.0",
    ],
    zip_safe=False,
    entry_points={
        "console_scripts": ["builder=builder:main"],
    },
)
