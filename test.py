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

import sys
import unittest
import d2dcn
import time
import os
import signal
import subprocess
import threading


class container():
    pass


class mqttBroker(unittest.TestCase):

    def __init__(self):
        # Launch discover broker process
        self.broker_discover = d2dcn.d2dBrokerDiscover()
        self.broker_discover.run(True)


        # Launch broker process
        self.pro = subprocess.Popen("mosquitto", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=False)

        time.sleep(2)


    def __del__(self):
        self.pro.send_signal( signal.SIGTERM)
        #self.pro.send_signal(signal.SIGINT)
        self.pro.wait()


class Test1_d2dBrokerDiscover(unittest.TestCase):

    def test1_startStopBrokerDiscover(self):
        broker_discover = d2dcn.d2dBrokerDiscover()
        t1 = broker_discover.run(True)
        time.sleep(2)
        broker_discover.stop()
        time.sleep(1)
        self.assertFalse(t1.is_alive())


    def test2_brokerDiscover(self):


        broker_discover = d2dcn.d2dBrokerDiscover()
        broker_discover.run(True)
        time.sleep(2)


        test1= d2dcn.d2d()
        ip = test1.getBrokerIP()
        self.assertTrue(ip != "")
        self.assertTrue(len(ip.split(".")) == 4)


class Test2_d2dcn(unittest.TestCase):

    def setUp(self):
        self.mqtt_broker = mqttBroker()


    def test1_d2dcnProperties(self):

        test1= d2dcn.d2d()
        self.assertTrue(test1.mac != "")
        self.assertTrue(test1.service != "")


    def test2_RegisteredCommand(self):

        test1 = d2dcn.d2d()
        test2 = d2dcn.d2d()


        # Subcribe commands
        tmp_container = container()
        tmp_container.wait = threading.Lock()
        tmp_container.wait.acquire()
        def checkUpdate(command):
            tmp_container.command = command
            tmp_container.wait.release()
        test2.onCommandUpdate = checkUpdate
        self.assertTrue(test2.subscribeComands())


        # Register command
        api_result = {}
        api_result["arg1"] = {}
        api_result["arg1"]["type"] = "int"
        api_result["arg2"] = {}
        api_result["arg2"]["type"] = "string"
        api_result["arg2"]["optional"] = True
        api_result["arg3"] = {}
        api_result["arg3"]["type"] = "float"
        api_result["arg3"]["optional"] = True
        api_result["arg4"] = {}
        api_result["arg4"]["type"] = "bool"
        api_result["arg4"]["optional"] = True
        command_type = "test"
        command_name = "command"
        self.assertTrue(test1.addServiceCommand(lambda args : args, command_name, api_result, api_result, command_type))


        # Wait command update and check
        self.assertTrue(tmp_container.wait.acquire(timeout=2))
        self.assertTrue(tmp_container.command.mac == test1.mac)
        self.assertTrue(tmp_container.command.service == test1.service)
        self.assertTrue(tmp_container.command.type == command_type)
        self.assertTrue(tmp_container.command.name == command_name)


        # Check registered command
        availableCommands = test2.getAvailableComands()
        self.assertTrue(len(availableCommands) >= 1)

        availableCommands = test2.getAvailableComands(mac=test1.mac, service=test1.service, type=command_type, command=command_name)
        self.assertTrue(len(availableCommands) == 1)


        # Test command info
        test_command = availableCommands[0]
        self.assertTrue(isinstance(test_command, d2dcn.d2dCommand))
        self.assertTrue(test_command.mac == test1.mac)
        self.assertTrue(test_command.name == command_name)
        self.assertTrue(test_command.service == test1.service)
        self.assertTrue(test_command.params == api_result)
        self.assertTrue(test_command.response == api_result)


        # Test command call. Missing non optional arg
        params = {}
        params["arg2"] = "string"
        result = test_command.call(params)
        self.assertTrue(result == None)


        # Test command call. Missing optional arg
        params = {}
        params["arg1"] = 1
        params["arg3"] = 1.2
        params["arg4"] = True
        result = test_command.call(params)
        self.assertTrue(result == params)


        # Test command. Call success
        params = {}
        params["arg1"] = 0
        params["arg2"] = "string"
        params["arg4"] = False
        result = test_command.call(params)
        self.assertTrue(result == params)


        # Test command. Invalid arg type
        params = {}
        params["arg1"] = "string"
        params["arg2"] = "string"
        result = test_command.call(params)
        self.assertTrue(result == None)


    def test3_publishGetInfo(self):

        test1= d2dcn.d2d()
        test2 = d2dcn.d2d()

        # Subcribe info
        tmp_container = container()
        tmp_container.wait = threading.Lock()
        tmp_container.wait.acquire()
        def checkUpdate(info):
            tmp_container.info = info
            tmp_container.wait.release()
        test2.onInfoUpdate= checkUpdate
        self.assertTrue(test2.subscribeInfo())

        # Publish int value
        info_name = "test"
        info_value = 2
        info_type = "test"
        self.assertTrue(test1.publishInfo(info_name, info_value, info_type))


        # Wait command update and check
        self.assertTrue(tmp_container.wait.acquire(timeout=2))
        self.assertTrue(tmp_container.info.mac == test1.mac)
        self.assertTrue(tmp_container.info.service == test1.service)
        self.assertTrue(tmp_container.info.type == info_type)
        self.assertTrue(tmp_container.info.name == info_name)
        self.assertTrue(tmp_container.info.value == info_value)
        self.assertTrue(tmp_container.info.valueType == d2dcn.d2dConstants.valueTypes.INT)
        self.assertTrue(isinstance(tmp_container.info.value, int))
        self.assertTrue(tmp_container.info.epoch != 0)


        # Publish float value
        info_value = 2.3
        last_epoch = tmp_container.info.epoch
        self.assertTrue(test1.publishInfo(info_name, info_value, info_type))


        # Wait command update and check
        self.assertTrue(tmp_container.wait.acquire(timeout=2))
        self.assertTrue(tmp_container.info.value == info_value)
        self.assertTrue(isinstance(tmp_container.info.value, float))
        self.assertTrue(tmp_container.info.valueType == d2dcn.d2dConstants.valueTypes.FLOAT)
        self.assertTrue(tmp_container.info.epoch >= last_epoch)


        # Publish bool value
        info_value = True
        last_epoch = tmp_container.info.epoch
        self.assertTrue(test1.publishInfo(info_name, info_value, info_type))


        # Wait command update and check
        self.assertTrue(tmp_container.wait.acquire(timeout=2))
        self.assertTrue(tmp_container.info.value == info_value)
        self.assertTrue(isinstance(tmp_container.info.value, bool))
        self.assertTrue(tmp_container.info.valueType == d2dcn.d2dConstants.valueTypes.BOOL)
        self.assertTrue(tmp_container.info.epoch >= last_epoch)


        # Publish string value
        info_value = "abcdefg"
        last_epoch = tmp_container.info.epoch
        self.assertTrue(test1.publishInfo(info_name, info_value, info_type))


        # Wait command update and check
        self.assertTrue(tmp_container.wait.acquire(timeout=2))
        self.assertTrue(tmp_container.info.value == info_value)
        self.assertTrue(isinstance(tmp_container.info.value, str))
        self.assertTrue(tmp_container.info.valueType == d2dcn.d2dConstants.valueTypes.STRING)
        self.assertTrue(tmp_container.info.epoch >= last_epoch)


        # Check registered command
        subscribed_info = test2.getSubscribedInfo()
        self.assertTrue(len(subscribed_info) >= 1)

        subscribed_info = test2.getSubscribedInfo(mac=test1.mac, service=test1.service, type=info_type, name=info_name)
        self.assertTrue(len(subscribed_info) == 1)


if __name__ == '__main__':
    unittest.main()