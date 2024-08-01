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

    found_commands = d2d_object.getAvailableComands(command="command_example1", wait=5)
    print("Found", len(found_commands), "example1 commands")

    for command_object in found_commands:
        params = {}
        params["command_arg1"] = True
        result = command_object.call(params)
        print("Command call result: ", result.success)
        print(result if result.success else result.error)

    
    found_commands = d2d_object.getAvailableComands(command="command_example2", wait=5)
    print("Found", len(found_commands), "example2 commands")

    for command_object in found_commands:
        params = {}
        params["command_arg1"] = [True, True]
        result = command_object.call(params)
        print("Command call result: ", result.success)
        print(result if result.success else result.error)


    print("Done!")


if __name__ == '__main__':
    main()