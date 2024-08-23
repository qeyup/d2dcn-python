#!/usr/bin/python3

import sys
import os
sys.path.append(os.path.dirname(__file__) + '/../d2dcn')

import d2dcn
import time




def main():


    d2d_object = d2dcn.d2d(service=sys.argv[1] if len(sys.argv) > 1 else "publish_info_example")

    int_writer = d2d_object.addInfoWriter("int", d2dcn.constants.valueTypes.INT, "example")
    float_writer = d2d_object.addInfoWriter("float", d2dcn.constants.valueTypes.FLOAT, "example")
    string_writer = d2d_object.addInfoWriter("string", d2dcn.constants.valueTypes.STRING, "example")
    bool_writer = d2d_object.addInfoWriter("bool", d2dcn.constants.valueTypes.BOOL, "example")
    int_array_writer = d2d_object.addInfoWriter("int_array", d2dcn.constants.valueTypes.INT_ARRAY, "example")
    float_array_writer = d2d_object.addInfoWriter("float_array", d2dcn.constants.valueTypes.FLOAT_ARRAY, "example")
    string_array_writer = d2d_object.addInfoWriter("string_array", d2dcn.constants.valueTypes.STRING_ARRAY, "example")
    bool_array_writer = d2d_object.addInfoWriter("bool_array", d2dcn.constants.valueTypes.BOOL_ARRAY, "example")


    # Main loop
    counter = 0
    while True:

        int_array_writer.value = [int_writer.value, int_writer.value + 1]
        float_array_writer.value = [float_writer.value, float_writer.value + 0.5]
        string_array_writer.value = [string_writer.value, "value_" + str(int_writer.value)]
        bool_array_writer.value = [bool_writer.value, not bool_writer.value]

        int_writer.value = int_array_writer.value[1]
        float_writer.value = float_array_writer.value[1]
        string_writer.value = string_array_writer.value[1]
        bool_writer.value = bool_array_writer.value[1]

        print(int_writer.value, float_writer.value, string_writer.value, bool_writer.value, int_array_writer.value, float_array_writer.value, string_array_writer.value, bool_array_writer.value)

        if counter == 5:
            input("Enter con continue...")
            counter = 0

        else:
            time.sleep(1)
            counter += 1



if __name__ == '__main__':
    try:
        main()
    except:
        pass