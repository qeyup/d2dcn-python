#! /usr/bin/python3
# 
# This file is part of the d2dcn distribution.
# Copyright (c) 2023 Javier Moreno Garcia.
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3.
#
# This program is distributed in the hope that it will be useful, but 
# WITHOUT ANY WARRANTY; without even the implied warranty of 
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU 
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License 
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#

import unittest
import d2dcn
import time
import weakref
import threading

class container():
    pass



class d2dcnTest(unittest.TestCase):

    category = "unit test"
    test_comand_name = "unit test command"
    test_info_writer_int = "unit test int info writer"
    test_info_writer_float = "unit test float info writer"
    test_info_writer_string = "unit test string info writer"
    test_info_writer_bool = "unit test bool info writer"
    test_info_writer_int_array = "unit test int_array info writer"
    test_info_writer_float_array = "unit test float_array info writer"
    test_info_writer_string_array = "unit test string_array info writer"
    test_info_writer_bool_array = "unit test bool_array info writer"


    def test0_startStop(self):
        test_obj = d2dcn.d2d(service="test0_startStop", start=False)
        test_obj.start()
        test_obj.stop()


    def test1_deleteInstance(self):

        def auxCall():
            test_obj = d2dcn.d2d(service="test1_deleteInstance")
            test_obj.addServiceCommand(lambda args : args, "test_command", {}, {}, d2dcnTest.category)
            comand = test_obj.getAvailableComands(name="test_*")[0]
            info_writer = test_obj.addInfoWriter("test_writer", d2dcn.constants.valueTypes.INT)
            info_reader = test_obj.getAvailableInfoReaders(name="test_*")[0]

            d2d_weak_ref = weakref.ref(test_obj)
            command_weak_ref = weakref.ref(comand)
            info_writer_weak_ref = weakref.ref(info_writer)
            info_readers_weak_ref = weakref.ref(info_reader)

            return d2d_weak_ref, command_weak_ref, info_writer_weak_ref, info_readers_weak_ref

        d2d_weak_ref, command_weak_ref, info_writer_weak_ref, info_readers_weak_ref = auxCall()
        self.assertTrue(d2d_weak_ref() == None, "d2d object is not deleted")
        self.assertTrue(command_weak_ref() == None, "command object is not deleted")
        self.assertTrue(info_writer_weak_ref() == None, "writer object is not deleted")
        self.assertTrue(info_readers_weak_ref() == None, "reader object is not deleted")


    def test2_Properties(self):

        test_obj= d2dcn.d2d(service="test2_Properties")
        self.assertTrue(test_obj.mac != "", "Object has not MAC")
        self.assertTrue(test_obj.service != "Object has not service name")

        test_obj.addServiceCommand(lambda args : args, d2dcnTest.test_comand_name, {}, {}, d2dcnTest.category)
        comand = test_obj.getAvailableComands(name=d2dcnTest.test_comand_name)[0]
        self.assertTrue(comand.name == d2dcnTest.test_comand_name, "incorrect name")
        self.assertTrue(comand.service == test_obj.service, "incorrect service")
        self.assertTrue(comand.mac == test_obj.mac, "incorrect MAC")
        self.assertTrue(comand.category == d2dcnTest.category, "incorrect category")

        info_writer = test_obj.addInfoWriter(d2dcnTest.test_info_writer_int, d2dcn.constants.valueTypes.INT, d2dcnTest.category)
        self.assertTrue(info_writer.name == d2dcnTest.test_info_writer_int, "incorrect name")
        self.assertTrue(info_writer.service == test_obj.service, "incorrect service")
        self.assertTrue(info_writer.mac == test_obj.mac, "incorrect MAC")
        self.assertTrue(info_writer.category == d2dcnTest.category, "incorrect category")

        info_reader = test_obj.getAvailableInfoReaders(name=d2dcnTest.test_info_writer_int)[0]
        self.assertTrue(info_reader.name == d2dcnTest.test_info_writer_int, "incorrect name")
        self.assertTrue(info_reader.service == test_obj.service, "incorrect service")
        self.assertTrue(info_reader.mac == test_obj.mac, "incorrect MAC")
        self.assertTrue(info_reader.category == d2dcnTest.category, "incorrect category")


    def test3_Command(self):

        test1 = d2dcn.d2d(service="test3_Command_A")
        test2 = d2dcn.d2d(service="test3_Command_B")

        wait_mutex = threading.Lock()
        wait_mutex.acquire()
        test2.onCommandUpdate = lambda mac, service, category, name, wait_mutex=wait_mutex : wait_mutex.release() if wait_mutex.locked() else True


        # Register command with client 1
        api_result = d2dcn.commandArgsDef()
        api_result.add("arg1", d2dcn.constants.valueTypes.INT)
        api_result.add("arg2", d2dcn.constants.valueTypes.STRING)
        api_result.add("arg3", d2dcn.constants.valueTypes.FLOAT)
        api_result.add("arg4", d2dcn.constants.valueTypes.BOOL)
        api_result.add("arg5", d2dcn.constants.valueTypes.INT_ARRAY)
        api_result.add("arg6", d2dcn.constants.valueTypes.STRING_ARRAY)
        api_result.add("arg7", d2dcn.constants.valueTypes.FLOAT_ARRAY)
        api_result.add("arg8", d2dcn.constants.valueTypes.BOOL_ARRAY)
        api_result.add("arg9", d2dcn.constants.valueTypes.BOOL, True)

        self.assertTrue(test1.addServiceCommand(lambda args : args, d2dcnTest.test_comand_name, api_result, api_result, d2dcnTest.category), "Error adding command")


        # Get comand from clien 2
        comands = test2.getAvailableComands(name=d2dcnTest.test_comand_name, wait=5)
        self.assertTrue(len(comands) > 0, "Not found command")


        # Check args
        self.assertTrue(comands[0].params.names == api_result.names, "Command args should be equal")
        self.assertTrue(comands[0].response.names == api_result.names, "Response args should be equal")
        for name in api_result.names:

            self.assertTrue(comands[0].params.getArgType(name) == api_result.getArgType(name), "Arg type are not correct")
            self.assertTrue(comands[0].params.isArgOptional(name) == api_result.isArgOptional(name), "Arg optional are not correct")

            self.assertTrue(comands[0].response.getArgType(name) == api_result.getArgType(name), "Arg type are not correct")
            self.assertTrue(comands[0].response.isArgOptional(name) == api_result.isArgOptional(name), "Arg optional are not correct")


        # Test command call. Missing non optional arg
        result = comands[0].call({})
        self.assertFalse(result.success, "Command must fail if any of the non-optinal paramas are missing")


        # Test command call. Missing optional arg
        params = {}
        params["arg1"] = 1
        params["arg2"] = "string"
        params["arg3"] = 1.2
        params["arg4"] = True
        params["arg5"] = [1, 2]
        params["arg6"] = ["a", "bb"]
        params["arg7"] = [2.2, 3.3]
        params["arg8"] = [True, False]
        result = comands[0].call(params)
        self.assertTrue(result.success, "Commnd should be success")
        self.assertTrue(result == params, "Input params should be equal to output params")


        # Test command call. all args
        params = {}
        params["arg1"] = 1
        params["arg2"] = "string"
        params["arg3"] = 1.2
        params["arg4"] = True
        params["arg5"] = [1, 2]
        params["arg6"] = ["a", "bb"]
        params["arg7"] = [2.2, 3.3]
        params["arg8"] = [True, False]
        params["arg9"] = True
        result = comands[0].call(params)
        self.assertTrue(result.success, "Commnd should be success")
        self.assertTrue(result == params, "Input params should be equal to output params")


        # Test command call. all args but incorrect type
        params = {}
        params["arg1"] = [1]
        params["arg2"] = "string"
        params["arg3"] = 1.2
        params["arg4"] = True
        params["arg5"] = [1, 2]
        params["arg6"] = ["a", "bb"]
        params["arg7"] = [2.2, 3.3]
        params["arg8"] = [True, False]
        result = comands[0].call(params)
        self.assertFalse(result.success, "Commnd should fail")


        # Test empty lists
        params = {}
        params["arg1"] = 1
        params["arg2"] = "string"
        params["arg3"] = 1.2
        params["arg4"] = True
        params["arg5"] = []
        params["arg6"] = []
        params["arg7"] = []
        params["arg8"] = []
        result = comands[0].call(params)
        self.assertTrue(result.success, "Commnd should be success")


        # Test enable/disable command
        self.assertTrue(comands[0].enable == True, "Command is not enable")

        self.assertTrue(test1.enableCommand(d2dcnTest.test_comand_name, False), "Error when disable command")
        self.assertTrue(wait_mutex.acquire(timeout=5), "Wait change timeout")
        self.assertTrue(comands[0].enable == False, "Command is enable")

        result = comands[0].call(params)
        self.assertFalse(result.success, "Commnd should not be success")

        self.assertTrue(test1.enableCommand(d2dcnTest.test_comand_name, True), "Error when enbale command")
        self.assertTrue(wait_mutex.acquire(timeout=5), "Wait change timeout")
        self.assertTrue(comands[0].enable == True, "Command is not enable")


    def test4_infoSharing(self):

        test1= d2dcn.d2d(service="test4_infoSharing_A")
        test2 = d2dcn.d2d(service="test4_infoSharing_B")

        wait_mutex = threading.Lock()
        wait_mutex.acquire()


        # Register info writers
        int_writer = test1.addInfoWriter(d2dcnTest.test_info_writer_int, d2dcn.constants.valueTypes.INT, d2dcnTest.category)
        self.assertTrue(int_writer != None, "Error crearing info writer object")

        float_writer = test1.addInfoWriter(d2dcnTest.test_info_writer_float, d2dcn.constants.valueTypes.FLOAT, d2dcnTest.category)
        self.assertTrue(float_writer != None, "Error crearing info writer object")

        string_writer = test1.addInfoWriter(d2dcnTest.test_info_writer_string, d2dcn.constants.valueTypes.STRING, d2dcnTest.category)
        self.assertTrue(string_writer != None, "Error crearing info writer object")

        bool_writer = test1.addInfoWriter(d2dcnTest.test_info_writer_bool, d2dcn.constants.valueTypes.BOOL, d2dcnTest.category)
        self.assertTrue(bool_writer != None, "Error crearing info writer object")

        int_array_writer = test1.addInfoWriter(d2dcnTest.test_info_writer_int_array, d2dcn.constants.valueTypes.INT_ARRAY, d2dcnTest.category)
        self.assertTrue(int_array_writer != None, "Error crearing info writer object")

        float_array_writer = test1.addInfoWriter(d2dcnTest.test_info_writer_float_array, d2dcn.constants.valueTypes.FLOAT_ARRAY, d2dcnTest.category)
        self.assertTrue(float_array_writer != None, "Error crearing info writer object")

        string_array_writer = test1.addInfoWriter(d2dcnTest.test_info_writer_string_array, d2dcn.constants.valueTypes.STRING_ARRAY, d2dcnTest.category)
        self.assertTrue(string_array_writer != None, "Error crearing info writer object")

        bool_array_writer = test1.addInfoWriter(d2dcnTest.test_info_writer_bool_array, d2dcn.constants.valueTypes.BOOL_ARRAY, d2dcnTest.category)
        self.assertTrue(bool_array_writer != None, "Error crearing info writer object")


        # Get info readers
        int_readers = test2.getAvailableInfoReaders(name=d2dcnTest.test_info_writer_int, category=d2dcnTest.category, wait=5)
        self.assertTrue(len(int_readers)>0, "Reader info element not found")
        int_readers[0].addOnUpdateCallback(lambda wait_mutex=wait_mutex : wait_mutex.release() if wait_mutex.locked() else True)

        float_readers = test2.getAvailableInfoReaders(name=d2dcnTest.test_info_writer_float, category=d2dcnTest.category, wait=5)
        self.assertTrue(len(float_readers)>0, "Reader info element not found")
        float_readers[0].addOnUpdateCallback(lambda wait_mutex=wait_mutex : wait_mutex.release() if wait_mutex.locked() else True)

        string_readers = test2.getAvailableInfoReaders(name=d2dcnTest.test_info_writer_string, category=d2dcnTest.category, wait=5)
        self.assertTrue(len(string_readers)>0, "Reader info element not found")
        string_readers[0].addOnUpdateCallback(lambda wait_mutex=wait_mutex : wait_mutex.release() if wait_mutex.locked() else True)

        bool_readers = test2.getAvailableInfoReaders(name=d2dcnTest.test_info_writer_bool, category=d2dcnTest.category, wait=5)
        self.assertTrue(len(bool_readers)>0, "Reader info element not found")
        bool_readers[0].addOnUpdateCallback(lambda wait_mutex=wait_mutex : wait_mutex.release() if wait_mutex.locked() else True)

        int_array_readers = test2.getAvailableInfoReaders(name=d2dcnTest.test_info_writer_int_array, category=d2dcnTest.category, wait=5)
        self.assertTrue(len(int_array_readers)>0, "Reader info element not found")
        int_array_readers[0].addOnUpdateCallback(lambda wait_mutex=wait_mutex : wait_mutex.release() if wait_mutex.locked() else True)

        float_array_readers = test2.getAvailableInfoReaders(name=d2dcnTest.test_info_writer_float_array, category=d2dcnTest.category, wait=5)
        self.assertTrue(len(float_array_readers)>0, "Reader info element not found")
        float_array_readers[0].addOnUpdateCallback(lambda wait_mutex=wait_mutex : wait_mutex.release() if wait_mutex.locked() else True)

        string_array_readers = test2.getAvailableInfoReaders(name=d2dcnTest.test_info_writer_string_array, category=d2dcnTest.category, wait=5)
        self.assertTrue(len(string_array_readers)>0, "Reader info element not found")
        string_array_readers[0].addOnUpdateCallback(lambda wait_mutex=wait_mutex : wait_mutex.release() if wait_mutex.locked() else True)

        bool_array_readers = test2.getAvailableInfoReaders(name=d2dcnTest.test_info_writer_bool_array, category=d2dcnTest.category, wait=5)
        self.assertTrue(len(bool_array_readers)>0, "Reader info element not found")
        bool_array_readers[0].addOnUpdateCallback(lambda wait_mutex=wait_mutex : wait_mutex.release() if wait_mutex.locked() else True)


        # Set and ead values
        int_writer.value = 10
        self.assertTrue(wait_mutex.acquire(timeout=5), "Writer value update not received")
        self.assertTrue(int_readers[0].value == int_writer.value, "Writer and reader value should be equal")

        float_writer.value = 10.10
        self.assertTrue(wait_mutex.acquire(timeout=5), "Writer value update not received")
        self.assertTrue(float_readers[0].value == float_writer.value, "Writer and reader value should be equal")

        string_writer.value = "test"
        self.assertTrue(wait_mutex.acquire(timeout=5), "Writer value update not received")
        self.assertTrue(string_readers[0].value == string_writer.value, "Writer and reader value should be equal")

        bool_writer.value = True
        self.assertTrue(wait_mutex.acquire(timeout=5), "Writer value update not received")
        self.assertTrue(bool_readers[0].value == bool_writer.value, "Writer and reader value should be equal")

        int_array_writer.value = [10, 20]
        self.assertTrue(wait_mutex.acquire(timeout=5), "Writer value update not received")
        self.assertTrue(int_array_readers[0].value == int_array_writer.value, "Writer and reader value should be equal")

        float_array_writer.value = [10.10, 20.20]
        self.assertTrue(wait_mutex.acquire(timeout=5), "Writer value update not received")
        self.assertTrue(float_array_readers[0].value == float_array_writer.value, "Writer and reader value should be equal")

        string_array_writer.value = ["test1", "test2"]
        self.assertTrue(wait_mutex.acquire(timeout=5), "Writer value update not received")
        self.assertTrue(string_array_readers[0].value == string_array_writer.value, "Writer and reader value should be equal")

        bool_array_writer.value = [True, False]
        self.assertTrue(wait_mutex.acquire(timeout=5), "Writer value update not received")
        self.assertTrue(bool_array_readers[0].value == bool_array_writer.value, "Writer and reader value should be equal")


        # Test set incorrect writer type
        try:
            int_writer.value="test"
            self.assertTrue(False, "Should raise execption")
        except:
            pass

        try:
            float_writer.value = 10
            self.assertTrue(False, "Should raise execption")
        except:
            pass

        try:
            string_writer.value = 10
            self.assertTrue(False, "Should raise execption")
        except:
            pass

        try:
            bool_writer.value = 1
            self.assertTrue(False, "Should raise execption")
        except:
            pass

        try:
            int_array_writer.value = 10
            self.assertTrue(False, "Should raise execption")
        except:
            pass

        try:
            float_array_writer.value = 10.10
            self.assertTrue(False, "Should raise execption")
        except:
            pass

        try:
            string_array_writer.value = "test1"
            self.assertTrue(False, "Should raise execption")
        except:
            pass

        try:
            bool_array_writer.value = 10
            self.assertTrue(False, "Should raise execption")
        except:
            pass



if __name__ == '__main__':
    unittest.main(verbosity=2)