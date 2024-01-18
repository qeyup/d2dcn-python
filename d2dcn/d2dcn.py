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

import os
import socket
import threading
import time
import uuid
import psutil
import json
import re
import paho.mqtt.client
import ServiceDiscovery


version = "0.2.0"


class d2dConstants():
    MQTT_SERVICE_NAME = "MQTT_BROKER"
    MQTT_BROKER_PORT = 1883
    MQTT_PREFIX = "d2dcn"
    COMMAND_LEVEL = "command"
    INFO_LEVEL = "info"

    class category:
        GENERIC = "generic"
        GPIO = "gpio"
        CONFIGURATION = "configuration"

    class commandErrorMsg:
        BAD_INPUT = "invalid input"
        BAD_OUTPUT = "invalid output"
        CALLBACK_ERROR = "command error"

    class commandField():
        PROTOCOL = "protocol"
        IP = "ip"
        PORT = "port"
        INPUT = "input"
        OUTPUT = "output"

    class commandProtocol():
        JSON_UDP = "json-udp"

    class infoField():
        VALUE = "value"
        TYPE = "type"
        EPOCH = "epoch"
        OPTIONAL = "optional"

    class valueTypes():
        BOOL = "bool"
        INT = "int"
        STRING = "string"
        FLOAT = "float"


class container():
    pass


class udpRandomPortListener():

    def __init__(self):
        self.__open = True
        self.__sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.__sock.bind(('', 0))
        self.__sock.settimeout(0.1)


    def __del__(self):
        self.close()


    def read(self, timeout=-1):

        current_epoch_time = int(time.time())
        while self.__open:
            try:
                data, (ip, port) = self.__sock.recvfrom(4096)
                return data, ip, port

            except socket.timeout:
                if timeout >= 0 and int(time.time()) - current_epoch_time >= timeout:
                    return None, None, None

            except socket.error:
                return None, None, None

        return None, None, None


    def send(self, ip, port, msg):
        if isinstance(msg, str):
            msg = msg.encode()
        self.__sock.sendto(msg, (ip, port))


    @property
    def ip(self):
        hostname = socket.gethostname()
        return socket.gethostbyname(hostname)


    @property
    def port(self):
        return self.__sock.getsockname()[1]


    def close(self):
        self.__open = False
        self.__sock.close()


class udpClient():
    def __init__(self, ip, port):
        self.__open = True
        self.__remote_ip = ip
        self.__remote_port = port
        self.__sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.__sock.settimeout(0.1)


    def __del__(self):
        self.close()


    def read(self, timeout=-1):

        current_epoch_time = int(time.time())
        while self.__open:
            try:
                data = self.__sock.recv(4096)
                return data

            except socket.timeout:
                if timeout >= 0 and int(time.time()) - current_epoch_time >= timeout:
                    return None

            except socket.error:
                return None

        return None


    def send(self, msg):
        if isinstance(msg, str):
            msg = msg.encode()
        self.__sock.sendto(msg, (self.__remote_ip, self.__remote_port))


    @property
    def local_ip(self):
        hostname = socket.gethostname()
        return socket.gethostbyname(hostname)


    @property
    def local_port(self):
        return self.__sock.getsockname()[1]


    @property
    def remote_ip(self):
        return self.__remote_ip


    @property
    def remote_port(self):
        return self.__remote_port


    def close(self):
        self.__open = False
        self.__sock.close()


class d2dCommand():

    def __init__(self,mac, service, category, name, protocol, ip, port, params, response):
        self.__name = name
        self.__mac = mac
        self.__service = service
        self.__category = category
        self.__params = params
        self.__response = response
        self.__socket = udpClient(ip, port)
        self.__protocol = protocol


    @property
    def name(self):
        return self.__name


    @property
    def mac(self):
        return self.__mac


    @property
    def service(self):
        return self.__service


    @property
    def category(self):
        return self.__category


    @property
    def params(self):
        return self.__params


    @property
    def response(self):
        return self.__response


    def call(self, args:dict, timeout=10) -> dict:

        try:
            self.__socket.send(json.dumps(args, indent=1))
            response = self.__socket.read(timeout)
            response_dict = json.loads(response)
            return response_dict

        except:
            return None


class d2dInfo():

    def __init__(self,mac, service, category, name, value, valueType, epoch):
        self.__name = name
        self.__mac = mac
        self.__service = service
        self.__category = category
        self.__value = value
        self.__epoch = epoch
        self.__valueType = valueType

    @property
    def name(self):
        return self.__name

    @property
    def mac(self):
        return self.__mac

    @property
    def service(self):
        return self.__service

    @property
    def category(self):
        return self.__category

    @property
    def value(self):
        return self.__value

    @property
    def valueType(self):
        return self.__valueType

    @property
    def epoch(self):
        return self.__epoch


class d2d():

    def __init__(self, broker_discover_timeout=5, broker_discover_retry=-1):
        self.__mac = hex(uuid.getnode()).replace("0x", "")

        process = psutil.Process(os.getpid())
        process_name = process.name()
        self.__service = process_name.split(".")[0]

        self.__broker_discover_timeout = broker_discover_timeout
        self.__broker_discover_retry = broker_discover_retry

        self.__client = None
        self.__threads = []
        self.__command_sockets = []
        self.__shared_container = container()
        self.__shared_container.run = True
        self.__shared_container.callback_mutex = threading.RLock()
        self.__shared_container.registered_mutex = threading.RLock()
        self.__shared_container.command_update_callback = None
        self.__shared_container.info_update_callback = None
        self.__shared_container.registered_commands = {}
        self.__shared_container.registered_info = {}


    def __del__(self):
        if self.__client:
            self.__client.disconnect()
        self.__shared_container.run = False
        for socket in self.__command_sockets:
            socket.close()
        for thread in self.__threads:
            thread.join()

    @property
    def service(self):
        return self.__service


    @property
    def mac(self):
        return self.__mac


    @property
    def onCommandUpdate(self):
        return self.__shared_container.command_update_callback


    @onCommandUpdate.setter
    def onCommandUpdate(self, callback):
        with self.__shared_container.callback_mutex:
            self.__shared_container.command_update_callback = callback

    @property
    def onInfoUpdate(self):
        return self.__shared_container.info_update_callback


    @onInfoUpdate.setter
    def onInfoUpdate(self, callback):
        with self.__shared_container.callback_mutex:
            self.__shared_container.info_update_callback = callback


    def __brokerMessaheReceived(message, shared_container):

        try:
            command_info = json.loads(message.payload)
        except:
            return

        topic_split = message.topic.split("/")
        if len(topic_split) != 6:
            return

        prefix = topic_split[0]
        mac = topic_split[1]
        service = topic_split[2]
        mode = topic_split[3]
        category = topic_split[4]
        name = topic_split[5]

        if prefix != d2dConstants.MQTT_PREFIX:
            return

        if mode == d2dConstants.COMMAND_LEVEL:

            try:
                protocol = command_info[d2dConstants.commandField.PROTOCOL]
                ip = command_info[d2dConstants.commandField.IP]
                port = command_info[d2dConstants.commandField.PORT]
                params = command_info[d2dConstants.commandField.INPUT]
                response = command_info[d2dConstants.commandField.OUTPUT]
            except:
                return

            command_object = d2dCommand(mac, service, category, name, protocol, ip, port, params, response)
            with shared_container.registered_mutex:
                shared_container.registered_commands[message.topic] = command_object

            with shared_container.callback_mutex:
                if shared_container.command_update_callback:
                    shared_container.command_update_callback(command_object)

        elif mode == d2dConstants.INFO_LEVEL:
            try:
                value = command_info[d2dConstants.infoField.VALUE]
                valtype = command_info[d2dConstants.infoField.TYPE]
                epoch = command_info[d2dConstants.infoField.EPOCH]
            except:
                return

            info_object = d2dInfo(mac, service, category, name, value, valtype, epoch)
            with shared_container.registered_mutex:
                shared_container.registered_info[message.topic] = info_object

            with shared_container.callback_mutex:
                if shared_container.info_update_callback:
                    shared_container.info_update_callback(info_object)


    def __checkBrokerConnection(self) -> bool:

        if self.__client:
            if self.__client.is_connected():
                return True
            else:
                for interval in range(50):
                    time.sleep(0.05)
                    if self.__client.is_connected():
                        return True

                return self.__client.is_connected()


        discover_client = ServiceDiscovery.client()
        broker_ip = discover_client.getServiceIP(d2dConstants.MQTT_SERVICE_NAME,
            timeout=self.__broker_discover_timeout, retry=self.__broker_discover_retry)
        if not broker_ip:
            return False


        client = paho.mqtt.client.Client()
        try:
            client.connect(broker_ip, d2dConstants.MQTT_BROKER_PORT)
        except:
            return False

        client.on_message = lambda client, shared_container, message : d2d.__brokerMessaheReceived(message, shared_container)
        client.user_data_set(self.__shared_container)
        client.loop_start()

        self.__client = client
        return True


    def __createMQTTPath(self, mac, service, category, mode, name) -> str:

        if mode not in [d2dConstants.COMMAND_LEVEL, d2dConstants.INFO_LEVEL]:
            return ""

        mqtt_path = d2dConstants.MQTT_PREFIX + "/"

        if mac != "":
            mqtt_path += mac + "/"
        else:
            mqtt_path += "+/"

        if service != "":
            mqtt_path += service + "/"
        else:
            mqtt_path += "+/"

        mqtt_path += mode + "/"

        if category != "":
            mqtt_path += category + "/"
        else:
            mqtt_path += "+/"

        if name != "":
            mqtt_path += name
        else:
            mqtt_path += "+"

        mqtt_path = mqtt_path.replace("#", "")

        return mqtt_path


    def __getType(self, data) -> str:

        if isinstance(data, float):
            return d2dConstants.valueTypes.FLOAT

        elif isinstance(data, bool):
            return d2dConstants.valueTypes.BOOL

        elif isinstance(data, int):
            return d2dConstants.valueTypes.INT

        elif isinstance(data, str):
            return d2dConstants.valueTypes.STRING

        else:
            return ""


    def __checkInOutDefinedField(field) -> bool:

        if d2dConstants.infoField.TYPE not in field:
            return False

        elif not isinstance(field[d2dConstants.infoField.TYPE], str):
            return False

        elif d2dConstants.infoField.OPTIONAL in field and not isinstance(field[d2dConstants.infoField.OPTIONAL], bool):
            return False

        return True


    def __checkFieldType(field, field_type):
        if field_type == d2dConstants.valueTypes.STRING:
            return isinstance(field, str)

        elif field_type == d2dConstants.valueTypes.BOOL:
            return isinstance(field, bool)

        elif field_type == d2dConstants.valueTypes.INT:
            return isinstance(field, int)

        elif field_type == d2dConstants.valueTypes.FLOAT:
            return isinstance(field, float)

        return False


    def __checkInOutField(data_dict, prototipe_dict) -> bool:

        # Chect type and non-exists
        for field in data_dict:
            if field not in prototipe_dict:
                return False
            if not d2d.__checkFieldType(data_dict[field], prototipe_dict[field][d2dConstants.infoField.TYPE]):
                return False

        # Check optional
        for field in prototipe_dict:
            field_prototipe = prototipe_dict[field]
            mandatory = d2dConstants.infoField.OPTIONAL not in field_prototipe or not field_prototipe[d2dConstants.infoField.OPTIONAL]
            if field not in data_dict and mandatory:
                return False

        return True


    def __commandListenThead(socket, shared_container, command_callback, input_params, output_params):
        while shared_container.run:
            read, ip, port = socket.read()
            if not read:
                break


            # json -> map
            try:
                args = json.loads(read)
            except:
                socket.send(ip, port, d2dConstants.commandErrorMsg.BAD_INPUT)
                continue


            # Check args
            if not d2d.__checkInOutField(args, input_params):
                socket.send(ip, port, d2dConstants.commandErrorMsg.BAD_INPUT)
                continue


            # Call command
            response_dict = command_callback(args)
            if response_dict:

                # Check args
                if not d2d.__checkInOutField(response_dict, output_params):
                    socket.send(ip, port, d2dConstants.commandErrorMsg.BAD_OUTPUT)

                else:
                    # map -> json
                    response = json.dumps(response_dict, indent=1)
                    socket.send(ip, port, response)

            else:
                socket.send(ip, port, d2dConstants.commandErrorMsg.CALLBACK_ERROR)


    def addServiceCommand(self, cmdCallback, name:str, input_params:dict, output_params:dict, category:str="")-> bool:

        if not cmdCallback:
            return False

        for field in input_params:
            if not d2d.__checkInOutDefinedField(input_params[field]):
                return False

        for field in output_params:
            if not d2d.__checkInOutDefinedField(input_params[field]):
                return False

        if not self.__checkBrokerConnection():
            return False

        if category == "":
            category = d2dConstants.category.GENERIC

        listen_socket = udpRandomPortListener()
        self.__command_sockets.append(listen_socket)
        thread = threading.Thread(target=d2d.__commandListenThead, daemon=True, args=[listen_socket, self.__shared_container, cmdCallback, input_params, output_params])
        thread.start()
        self.__threads.append(thread)


        mqtt_path = self.__createMQTTPath(self.__mac, self.__service, category, d2dConstants.COMMAND_LEVEL, name)

        mqtt_msg = {}
        mqtt_msg[d2dConstants.commandField.PROTOCOL] = d2dConstants.commandProtocol.JSON_UDP
        mqtt_msg[d2dConstants.commandField.IP] = listen_socket.ip
        mqtt_msg[d2dConstants.commandField.PORT] = listen_socket.port
        mqtt_msg[d2dConstants.commandField.INPUT] = input_params
        mqtt_msg[d2dConstants.commandField.OUTPUT] = output_params

        msg_info = self.__client.publish(mqtt_path, payload=json.dumps(mqtt_msg, indent=1), qos=1, retain=True)
        return msg_info.rc == paho.mqtt.client.MQTT_ERR_SUCCESS


    def subscribeComands(self, mac:str="", service:str="", category:str="", command:str="") -> bool:

        if not self.__checkBrokerConnection():
            return False

        mqtt_path = self.__createMQTTPath(mac, service, category, d2dConstants.COMMAND_LEVEL, command)

        try:
            self.__client.subscribe(mqtt_path)
        except:
            return False

        return True


    def getAvailableComands(self, mac:str="", service:str="", category:str="", command:str="") -> list:

        mqtt_pattern_path = self.__createMQTTPath(mac, service, category, d2dConstants.COMMAND_LEVEL, command)
        mqtt_pattern_path = mqtt_pattern_path.replace("+", ".*")

        commands = []
        with self.__shared_container.registered_mutex:
            for mqtt_path in self.__shared_container.registered_commands:
                if re.search(mqtt_pattern_path, mqtt_path):
                    commands.append(self.__shared_container.registered_commands[mqtt_path])

        return commands


    def subscribeInfo(self, mac:str="", service:str="", category="", name:str="") -> bool:
        if not self.__checkBrokerConnection():
            return False

        mqtt_path = self.__createMQTTPath(mac, service, category, d2dConstants.INFO_LEVEL, name)

        try:
            self.__client.subscribe(mqtt_path)
        except:
            return False

        return True


    def getSubscribedInfo(self, mac:str="", service:str="", category="", name:str="") -> dict:
        mqtt_pattern_path = self.__createMQTTPath(mac, service, category, d2dConstants.INFO_LEVEL, name)
        mqtt_pattern_path = mqtt_pattern_path.replace("+", ".*")

        info = []
        with self.__shared_container.registered_mutex:
            for mqtt_path in self.__shared_container.registered_info:
                if re.search(mqtt_pattern_path, mqtt_path):
                    info.append(self.__shared_container.registered_info[mqtt_path])

        return info


    def publishInfo(self, name:str, value:str, category:str) -> bool:
        if not self.__checkBrokerConnection():
            return False

        if category == "":
            category = d2dConstants.category.GENERIC

        mqtt_path = self.__createMQTTPath(self.__mac, self.__service, category, d2dConstants.INFO_LEVEL, name)

        value_type = self.__getType(value)
        if value_type == "":
            return False

        mqtt_msg = {}
        mqtt_msg[d2dConstants.infoField.VALUE] = value
        mqtt_msg[d2dConstants.infoField.TYPE] = value_type
        mqtt_msg[d2dConstants.infoField.EPOCH] = int(time.time())
        msg_info = self.__client.publish(mqtt_path, payload=json.dumps(mqtt_msg, indent=1), qos=1, retain=True)
        return msg_info.rc == paho.mqtt.client.MQTT_ERR_SUCCESS
