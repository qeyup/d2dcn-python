#!/usr/bin/python3

import sys
import os
sys.path.append(os.path.dirname(__file__) + '/../d2dcn')

import d2dcn
import time


COMMAND_ARG1 = "command_arg1"

RESPONSE_ARG1 = "response_arg1"


def command_call(args):
    print("comand call recived")
    return []


def main():

    d2d_object = d2dcn.d2d()


    # Get available comand example 1
    found_commands1 = d2d_object.getAvailableComands(command="command_example1", wait=5)
    print("Found", len(found_commands1), "example1 commands")


    # Get available comand example 2
    found_commands2 = d2d_object.getAvailableComands(command="command_example2", wait=5)
    print("Found", len(found_commands2), "example2 commands")


    # Call loop
    while len(found_commands1) + len(found_commands2) > 0:

        # Call example 1
        for command_object in found_commands1:
            params = {}
            params["command_arg1"] = True
            result = command_object.call(params)
            print("Command call1 result: ", result.success, "->", result if result.success else result.error)

        # Call example 2
        for command_object in found_commands2:
            params = {}
            params["command_arg1"] = [True, True]
            result = command_object.call(params)
            print("Command call2 result: ", result.success, "->", result if result.success else result.error)


        print("Wait...\n\n")
        time.sleep(2)


    print("Not commands found!")


if __name__ == '__main__':
    try:
        main()
    except:
        pass