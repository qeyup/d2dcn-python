#!/usr/bin/env python3


import d2dcn
import setuptools


if __name__ == '__main__':
    setuptools.setup(
        name = 'd2dcn',
        version = d2dcn.version,
        packages = ["d2dcn"],
        install_requires = [
            "psutil",
            "SharedTableBroker>=0.1.3",
            "pyroute2"
        ],
        author = "Javier Moreno Garcia",
        author_email = "jgmore@gmail.com",
        description = "",
        long_description_content_type = "text/markdown",
        long_description = "",
        url = "https://github.com/qeyup/d2dcn-python"
    )
