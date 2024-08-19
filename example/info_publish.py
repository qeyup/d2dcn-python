import sys
sys.path.append('../d2dcn/')
sys.path.append('.')

import d2dcn
import time




def main():


    d2d_object = d2dcn.d2d(service=sys.argv[1] if len(sys.argv) > 1 else "publish_info_example")

    int_writer = d2d_object.addInfoWriter("int_example", "example", d2dcn.d2dConstants.valueTypes.INT)
    float_writer = d2d_object.addInfoWriter("float_example", "example", d2dcn.d2dConstants.valueTypes.FLOAT)
    string_writer = d2d_object.addInfoWriter("string_example", "example", d2dcn.d2dConstants.valueTypes.STRING)
    bool_writer = d2d_object.addInfoWriter("bool_example", "example", d2dcn.d2dConstants.valueTypes.BOOL)
    int_array_writer = d2d_object.addInfoWriter("int_array_example", "example", d2dcn.d2dConstants.valueTypes.INT_ARRAY)
    float_array_writer = d2d_object.addInfoWriter("float_array_example", "example", d2dcn.d2dConstants.valueTypes.FLOAT_ARRAY)
    string_array_writer = d2d_object.addInfoWriter("string_array_example", "example", d2dcn.d2dConstants.valueTypes.STRING_ARRAY)
    bool_array_writer = d2d_object.addInfoWriter("bool_array_example", "example", d2dcn.d2dConstants.valueTypes.BOOL_ARRAY)


    # Main loop
    while True:

        int_array_writer.value = [int_writer.value]
        float_array_writer.value = [float_writer.value]
        string_array_writer.value = [string_writer.value]
        bool_array_writer.value = [bool_writer.value]

        int_writer.value = int_writer.value + 1
        float_writer.value = float_writer.value + 0.5
        string_writer.value = "value_" + str(int_writer.value)
        bool_writer.value = not bool_writer.value

        int_array_writer.value = int_array_writer.value + [int_writer.value]
        float_array_writer.value = float_array_writer.value + [float_writer.value]
        string_array_writer.value = string_array_writer.value + [string_writer.value]
        bool_array_writer.value = bool_array_writer.value + [bool_writer.value]


        print(int_writer.value, float_writer.value, string_writer.value, bool_writer.value, int_array_writer.value, float_array_writer.value, string_array_writer.value, bool_array_writer.value)

        time.sleep(1)



if __name__ == '__main__':
    main()