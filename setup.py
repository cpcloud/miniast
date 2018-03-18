import versioneer

from setuptools import setup, find_packages


setup(
    name='miniast',
    url='https://github.com/cpcloud/miniast',
    packages=find_packages(),
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    description='Lightweight macros for Python',
    license='Apache License, Version 2.0',
    author='Phillip Cloud',
    author_email='cpcloud@gmail.com',
)
