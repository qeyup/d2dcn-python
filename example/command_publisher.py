import sys
sys.path.append('../d2dcn/')
sys.path.append('.')

import d2dcn


COMMAND_ARG1 = "command_arg1"

RESPONSE_ARG1 = "response_arg1"


def command_call(args):
    print("comand call recived")
    return []


def main():

    d2d_object = d2dcn.d2d()

    command_args = {}
    command_args[COMMAND_ARG1] = {}
    command_args[COMMAND_ARG1][d2dcn.d2dConstants.infoField.TYPE] = d2dcn.d2dConstants.valueTypes.BOOL

    response_args = {}
    response_args[RESPONSE_ARG1] = {}
    response_args[RESPONSE_ARG1][d2dcn.d2dConstants.infoField.TYPE] = d2dcn.d2dConstants.valueTypes.STRING

    command_category = "example"
    command_name = "command_example1"

    d2d_object.addServiceCommand(command_call, command_name, command_args, response_args, command_category)

    print("wait calls")
    d2d_object.waitThreads()

    print("Done!")


if __name__ == '__main__':
    main()