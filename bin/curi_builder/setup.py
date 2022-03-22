from setuptools import setup, find_packages

setup(name='builder',
      version='0.1',
      packages=['builder'],
      install_requires=[
        "requests>=2.27.1",
      ],
      zip_safe=False,
      entry_points = {
          'console_scripts': ['builder=builder:main'],
      }
)
