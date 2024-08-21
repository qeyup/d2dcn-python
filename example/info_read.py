import sys
sys.path.append('../d2dcn/')
sys.path.append('.')

import d2dcn
import threading



def newData(mutex:threading.Lock):
    if mutex.locked():
        mutex.release()


def main():

    d2d_object = d2dcn.d2d()
    mutex = threading.Lock()


    info_reader_objects = d2d_object.getAvailableInfoReaders(name=".*_example")
    print("Found", len(info_reader_objects), "reader objects")

    for reader_obj in info_reader_objects:
        reader_obj.onUpdateValue = lambda mutex=mutex : newData(mutex)

    while len(info_reader_objects) > 0 and mutex.acquire():
        print([info_reader_object.value for info_reader_object in info_reader_objects])



if __name__ == '__main__':
    main()