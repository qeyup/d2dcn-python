#! /usr/bin/python3
# 
# This file is part of the d2dcn distribution.
# Copyright (c) 2015 Liviu Ionescu.
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

        test1= d2dcn.d2d()
        test2 = d2dcn.d2d()


        # Subcribe commands
        tmp_container = container()
        tmp_container.wait = threading.Lock()
        tmp_container.wait.acquire()
        def checkUpdate(mac, service, type, name):
            tmp_container.mac = mac
            tmp_container.service = service
            tmp_container.type = type
            tmp_container.name = name
            tmp_container.wait.release()
        test2.onCommandUpdate = checkUpdate
        self.assertTrue(test2.subscribeComands())


        # Register command
        api_result = {"arg1":"int", "arg2":"string"}
        command_type = "test"
        command_name = "command"
        self.assertTrue(test1.addServiceCommand(lambda args : args, command_name, api_result, api_result, command_type))


        # Wait command update and check
        self.assertTrue(tmp_container.wait.acquire(timeout=2))
        self.assertTrue(tmp_container.mac == test1.mac)
        self.assertTrue(tmp_container.service == test1.service)
        self.assertTrue(tmp_container.type == command_type)
        self.assertTrue(tmp_container.name == command_name)


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
        return


        # Test command call
        result = test_command.call(api_result)
        self.assertTrue(result == api_result)


    def dis_test_Info1(self):

        test1= d2dcn.d2d()
        test2 = d2dcn.d2d()

        # Publish value
        info_name = "test"
        info_value = 2
        self.assertTrue(test1.publishInfo(self, info_name, info_value))


        # Subscribe all
        self.assertTrue(test2.subscribeInfo())


if __name__ == '__main__':
    unittest.main()