#!/usr/bin/env python3


import d2dcn
import setuptools


entries = {}
packages = ['.']
data_files = []
install_requires=['requests']

if __name__ == '__main__':
    setuptools.setup(
        name='d2dcn',
        version=d2dcn.version,
        packages=packages,
        entry_points=entries,
        data_files=data_files,
        install_requires=install_requires,
        author="Javier Moreno Garcia",
        author_email="jgmore@gmail.com",
        description="",
        long_description_content_type="text/markdown",
        long_description="",
        url="https://github.com/qeyup/DockerBuild",
    )
