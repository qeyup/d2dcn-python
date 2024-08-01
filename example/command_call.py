import sys
sys.path.append('../d2dcn/')
sys.path.append('.')

import d2dcn
import time


COMMAND_ARG1 = "command_arg1"

RESPONSE_ARG1 = "response_arg1"


def command_call(args):
    print("comand call recived")
    return []


def main():

    d2d_object = d2dcn.d2d(service="call_command_example")

    found_commands = d2d_object.getAvailableComands(wait=5)
    print("Found", len(found_commands), "commands")

    for command_object in found_commands:
        params = {}
        params["command_arg1"] = True
        result = command_object.call(params)
        print("Command call result: ", result.success)
        print(result if result.success else result.error)



    print("Done!")


if __name__ == '__main__':
    main()