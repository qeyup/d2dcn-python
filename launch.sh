#!/bin/bash

COMMAND="sudo docker-compose -p d2dcn_dwc -f docker/docker-compose.yml up -d"
if type konsole &> /dev/null; then konsole -e "${COMMAND}";
elif type xterm &> /dev/null; then xterm -e "${COMMAND}";
else ${COMMAND}; fi
