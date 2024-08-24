#!/usr/bin/python3

import sys
import os
sys.path.append(os.path.dirname(__file__) + '/../d2dcn')

import d2dcn
import traceback


COMMAND_ARG1 = "command_arg1"

RESPONSE_ARG1 = "response_arg1"


def command_call(args):
    response = {}
    response[RESPONSE_ARG1] = "Recived!"
    return response


def command_call2(args):
    response = {}
    response[RESPONSE_ARG1] = ["Recived!"]
    return response


def main():

    service=sys.argv[1] if len(sys.argv) > 1 else "publish_command_example"
    d2d_object = d2dcn.d2d(service=service)


    # Command call 1
    command_args = d2dcn.commandArgsDef()
    command_args.add(COMMAND_ARG1, d2dcn.constants.valueTypes.BOOL)

    response_args = d2dcn.commandArgsDef()
    response_args.add(RESPONSE_ARG1, d2dcn.constants.valueTypes.STRING, True)

    command1_category = "example"
    command1_name = "command_example1"

    d2d_object.addServiceCommand(command_call, command1_name, command_args, response_args, command1_category)


    # Command call 2
    command_args = d2dcn.commandArgsDef()
    command_args.add(COMMAND_ARG1, d2dcn.constants.valueTypes.BOOL_ARRAY)

    response_args = d2dcn.commandArgsDef()
    response_args.add(RESPONSE_ARG1, d2dcn.constants.valueTypes.STRING_ARRAY, True)

    command2_category = "example"
    command2_name = "command_example2"

    d2d_object.addServiceCommand(command_call2, command2_name, command_args, response_args, command2_category)


    # Enable / Disable loop
    command1_enable = True
    command2_enable = True
    while True:

        input("Enter to " + ("Disable " if command1_enable else "Enable ") + service + "/" +command1_name + "...")
        command1_enable = not command1_enable
        d2d_object.enableCommand(command1_name, command1_enable)


        input("Enter to " + ("Disable " if command2_enable else "Enable ") + service + "/" +command2_name + "...")
        command2_enable = not command2_enable
        d2d_object.enableCommand(command2_name, command2_enable)


if __name__ == '__main__':
    try:
        main()

    except:
        print(traceback.format_exc())
