from setuptools import setup, find_packages

with open('requirements.txt') as f:
    required = f.read().splitlines()

setup(name='bqConductor',
      version='0.1',
      description='Orchestrating computations inside bigquery',
      url='https://github.com/Bobain/bigquery-conductor',
      author='Bobain',
      author_email='romain.burgot@gmail.com',
      license='...',
      packages=find_packages(),
      install_requires=required,
      zip_safe=False)
