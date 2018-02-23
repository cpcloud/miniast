import versioneer

from setuptools import setup, find_packages


setup(
    name='miniast',
    packages=find_packages(),
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
)
