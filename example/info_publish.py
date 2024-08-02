import sys
sys.path.append('../d2dcn/')
sys.path.append('.')

import d2dcn
import time




def main():

    d2d_object = d2dcn.d2d(service="publish_cinfo_example")
    change_value = 0


    while True:

        # Publish int value
        info_name = "int test"
        info_value = change_value
        info_category = "test"
        d2d_object.publishInfo(info_name, info_value, info_category)

        # Publish int array value
        info_name = "int array test"
        info_value = [change_value, change_value+1, change_value+2, change_value+3]
        info_category = "test"
        d2d_object.publishInfo(info_name, info_value, info_category)

        # Publish bool value
        info_name = "bool test"
        info_value = True if change_value % 2 else False
        info_category = "test"
        d2d_object.publishInfo(info_name, info_value, info_category)

        # Publish bool array value
        info_name = "bool array test"
        info_value = [True if change_value % 2 else False, False if change_value % 2 else True ]
        info_category = "test"
        d2d_object.publishInfo(info_name, info_value, info_category)

        # Publish float value
        info_name = "float test"
        info_value = float(change_value) + 0.5
        info_category = "test"
        d2d_object.publishInfo(info_name, info_value, info_category)

        # Publish float array value
        info_name = "float array test"
        info_value = [float(change_value) + 0.25, float(change_value) + 0.5, float(change_value) + 0.75]
        info_category = "test"
        d2d_object.publishInfo(info_name, info_value, info_category)

        # Publish string value
        info_name = "string test"
        info_value = ">>" + str(change_value) + "<<"
        info_category = "test"
        d2d_object.publishInfo(info_name, info_value, info_category)

        # Publish string value
        info_name = "string array test"
        info_value = [">>" + str(change_value) + "<<", ">>" + str(change_value) + "<<"]
        info_category = "test"
        d2d_object.publishInfo(info_name, info_value, info_category)

        print(change_value)
        change_value += 1
        time.sleep(1)



if __name__ == '__main__':
    main()