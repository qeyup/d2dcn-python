#! /usr/bin/python3

import sys
import unittest
import d2dcn
import time
import os
import signal
import subprocess
 

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
        #pro.send_signal(signal.SIGINT)
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


class Test2_d2dUnitTest(unittest.TestCase):

    def setUp(self):
        self.mqtt_broker = mqttBroker()


    def test3_d2dcnInfoAsignation(self):

        test1= d2dcn.d2d()
        self.assertTrue(test1.mac != "")
        self.assertTrue(test1.service != "")


    def test4_RegisteredCommand(self):

        test1= d2dcn.d2d()
        test2 = d2dcn.d2d()


        # Register command
        api_result = {"arg1":"int", "arg2":"string"}
        command_type = "test"
        command_name = "command"
        self.assertTrue(test1.addServiceCommand(lambda args : args, command_name, api_result, api_result, command_type), "Check if broker is active")

        return


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
        self.assertTrue(test_command.api == api_result)
        self.assertTrue(test_command.result == api_result)


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