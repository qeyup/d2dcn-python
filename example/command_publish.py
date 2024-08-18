import sys
sys.path.append('../d2dcn/')
sys.path.append('.')

import d2dcn


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

    if len(sys.argv) > 1:
        service=sys.argv[1]

    else:
        service="publish_command_example"


    d2d_object = d2dcn.d2d(service=service)


    # Command call 1
    command_args = {}
    command_args[COMMAND_ARG1] = {}
    command_args[COMMAND_ARG1][d2dcn.d2dConstants.infoField.TYPE] = d2dcn.d2dConstants.valueTypes.BOOL

    response_args = {}
    response_args[RESPONSE_ARG1] = {}
    response_args[RESPONSE_ARG1][d2dcn.d2dConstants.infoField.TYPE] = d2dcn.d2dConstants.valueTypes.STRING

    command1_category = "example"
    command1_name = "command_example1"

    d2d_object.addServiceCommand(command_call, command1_name, command_args, response_args, command1_category)


    # Command call 2
    command_args = {}
    command_args[COMMAND_ARG1] = {}
    command_args[COMMAND_ARG1][d2dcn.d2dConstants.infoField.TYPE] = d2dcn.d2dConstants.valueTypes.BOOL_ARRAY

    response_args = {}
    response_args[RESPONSE_ARG1] = {}
    response_args[RESPONSE_ARG1][d2dcn.d2dConstants.infoField.TYPE] = d2dcn.d2dConstants.valueTypes.STRING_ARRAY

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
    main()