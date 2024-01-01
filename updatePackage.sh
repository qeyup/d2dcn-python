#!/bin/bash

# Generate package
python3 setup.py sdist bdist_wheel 

# upload to pypi
twine upload dist/*
