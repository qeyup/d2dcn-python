import sys
sys.path.append('../d2dcn/')
sys.path.append('.')

import d2dcn
import time
import threading


class container():
    pass


def printInfo(reader_obj, mutex):
    with mutex:
        if reader_obj.online:
            print("[", reader_obj.epoch , "]", reader_obj.mac, "/" , reader_obj.service, "->", reader_obj.name, "=" , reader_obj.value)

        else:
            print("[", reader_obj.epoch , "]", reader_obj.mac, "/" , reader_obj.service, "->", reader_obj.name, "=" , "OFFLINE")


def addNewInfo(d2d_object, mutex, mac, service, category, name):
    info_reader_objects = d2d_object.getAvailableInfoReaders(mac=mac, service=service, category=category, name=name)

    for reader_obj in info_reader_objects:
        reader_obj.addOnUpdateCallback(lambda reader_obj=reader_obj, mutex=mutex: printInfo(reader_obj, mutex))


def main():

    mutex = threading.Lock()

    d2d_object = d2dcn.d2d()


    # Get available objects
    info_reader_objects = d2d_object.getAvailableInfoReaders(category="example")
    print("Found", len(info_reader_objects), "reader objects")
    print([info_reader_object.value for info_reader_object in info_reader_objects])


    # Callback for new objects
    d2d_object.onInfoAdd = lambda mac, service, category, name, d2d_object=d2d_object, mutex=mutex : addNewInfo(d2d_object, mutex, mac, service, category, name)


    # Callback for print updates
    for reader_obj in info_reader_objects:
        reader_obj.addOnUpdateCallback(lambda reader_obj=reader_obj, mutex=mutex: printInfo(reader_obj, mutex))


    # Dead loop
    while True:
        time.sleep(1)


if __name__ == '__main__':
    main()