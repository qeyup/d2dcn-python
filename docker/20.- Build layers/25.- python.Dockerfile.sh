#!/bin/bash
set -e


# Upgrade system
PACKAGES=()
PACKAGES+=(psutil)
PACKAGES+=(paho-mqtt)
PACKAGES+=(wheel)
PACKAGES+=(setuptools)
PACKAGES+=(twine)

# Install all
pip3 install ${PACKAGES[@]}
