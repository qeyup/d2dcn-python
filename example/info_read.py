import sys
sys.path.append('../d2dcn/')
sys.path.append('.')

import d2dcn
import time
import threading



def newData(reader_obj, mutex):
    with mutex:
        if reader_obj.online:
            print("[", reader_obj.epoch , "]", reader_obj.mac, "/" , reader_obj.service, "->", reader_obj.name, "=" , reader_obj.value)

        else:
            print("[", reader_obj.epoch , "]", reader_obj.mac, "/" , reader_obj.service, "->", reader_obj.name, "=" , "OFLINE")


def main():

    d2d_object = d2dcn.d2d()
    mutex = threading.Lock()

    info_reader_objects = d2d_object.getAvailableInfoReaders(category="example")
    print("Found", len(info_reader_objects), "reader objects")

    for reader_obj in info_reader_objects:
        reader_obj.onUpdateValue = lambda reader_obj=reader_obj, mutex=mutex : newData(reader_obj, mutex)

    print([info_reader_object.value for info_reader_object in info_reader_objects])
    d2d_object.waitThreads()


    while True:
        time.sleep(1)


if __name__ == '__main__':
    main()