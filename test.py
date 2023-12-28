import unittest
import d2dcn


class Testd2dUnitTest(unittest.TestCase):

    def setUp(self):
        pass


    def test_Command1(self):

        test1= d2dcn.d2d()
        test2 = d2dcn.d2d()


        # Register command
        api_result = {"arg1":"int", "arg2":"string"}
        command_type = "test"
        command_name = "command"
        self.assertTrue(test1.addServiceCommand(lambda args : args, command_name, api_result, api_result, command_type))


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


    def test_Info1(self):

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