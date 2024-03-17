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
import weakref


version = "0.3.3"


class d2dConstants():
    MQTT_SERVICE_NAME = "MQTT_BROKER"
    MQTT_BROKER_PORT = 1883
    MTU = 4096
    MAX_LISTEN_TCP_SOKETS = 0
    MQTT_PREFIX = "d2dcn"
    COMMAND_LEVEL = "command"
    INFO_LEVEL = "info"
    STATE = "state"

    class state:
        OFFLINE = "offline"

    class category:
        GENERIC = "generic"
        GPIO = "gpio"
        CONFIGURATION = "configuration"

    class commandErrorMsg:
        BAD_INPUT = "Invalid input"
        BAD_OUTPUT = "Invalid output"
        CALLBACK_ERROR = "Command error"
        CONNECTION_ERROR = "Connection error"
        TIMEOUT_ERROR = "Timeout error"
        EXCEPTION_ERROR = "Exception raised"
        NOT_ENABLE_ERROR = "Command not enable"

    class commandField():
        PROTOCOL = "protocol"
        IP = "ip"
        PORT = "port"
        INPUT = "input"
        OUTPUT = "output"
        ENABLE = "enable"
        TIMEOUT = "timeout"

    class commandProtocol():
        JSON_UDP = "json-udp"
        JSON_TCP = "json-tcp"

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
        super().__init__()
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
                data, (ip, port) = self.__sock.recvfrom(d2dConstants.MTU)
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

        chn_msg = [msg[idx : idx + d2dConstants.MTU] for idx in range(0, len(msg), d2dConstants.MTU)]

        for chn in chn_msg:
            self.__sock.sendto(chn, (ip, port))


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
                data = self.__sock.recv(d2dConstants.MTU)
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

        chn_msg = [msg[idx : idx + d2dConstants.MTU] for idx in range(0, len(msg), d2dConstants.MTU)]

        for chn in chn_msg:
            self.__sock.sendto(chn, (self.__remote_ip, self.__remote_port))


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


class tcpRandomPortListener():


    class connection():

        def __init__(self, connection, ip, port):
            self.__sock = connection
            self.__ip = ip
            self.__port = port
            self.__open = True
            self.__sock.settimeout(0.1)


        def read(self, timeout=-1):

            current_epoch_time = int(time.time())
            while self.__open:
                try:
                    data = self.__sock.recv(d2dConstants.MTU)
                    return data

                except socket.timeout:
                    if timeout >= 0 and int(time.time()) - current_epoch_time >= timeout:
                        return None

                except socket.error:
                    self.close()
                    return None



        def send(self, msg):
            if isinstance(msg, str):
                msg = msg.encode()

            chn_msg = [msg[idx : idx + d2dConstants.MTU] for idx in range(0, len(msg), d2dConstants.MTU)]

            for chn in chn_msg:
                self.__sock.sendall(chn)


        def isConnected(self):
            return self.__open


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


    def __init__(self):
        super().__init__()
        self.__open = True
        self.__sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__sock.bind(('', 0))
        self.__sock.settimeout(0.1)
        self.__sock.listen(d2dConstants.MAX_LISTEN_TCP_SOKETS)


    def __del__(self):
        self.close()


    @property
    def ip(self):
        hostname = socket.gethostname()
        return socket.gethostbyname(hostname)


    @property
    def port(self):
        return self.__sock.getsockname()[1]


    def waitConnection(self, timeout=-1):

        current_epoch_time = int(time.time())
        while self.__open:
            try:
                connection, (ip, port) = self.__sock.accept()
                return tcpRandomPortListener.connection(connection, ip, port)


            except socket.timeout:
                if timeout >= 0 and int(time.time()) - current_epoch_time >= timeout:
                    return None

            except socket.error:
                return None


    def close(self):
        self.__open = False
        self.__sock.close()


class tcpClient():
    def __init__(self, ip, port):
        self.__open = False
        self.__remote_ip = ip
        self.__remote_port = port
        self.__sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__sock.settimeout(0.1)


    def __del__(self):
        self.close()


    def __connect(self):
        if not self.__open:
            try:
                self.__sock.connect((self.__remote_ip, self.__remote_port))
                self.__open = True

            except:
                pass

        return self.__open


    def read(self, timeout=-1):

        if self.__connect():
            current_epoch_time = int(time.time())
            while self.__open:
                try:
                    data = self.__sock.recv(d2dConstants.MTU)
                    return data

                except socket.timeout:
                    if timeout >= 0 and int(time.time()) - current_epoch_time >= timeout:
                        return None

                except socket.error:
                    self.close()
                    if not self.__connect():
                        return None

        return None


    def send(self, msg):
        if self.__connect():

            if isinstance(msg, str):
                msg = msg.encode()

            chn_msg = [msg[idx : idx + d2dConstants.MTU] for idx in range(0, len(msg), d2dConstants.MTU)]
            while True:

                try:
                    for chn in chn_msg:
                        self.__sock.sendall(chn)

                    return True

                except:
                    self.close()
                    if not self.__connect():
                        return False

        return False


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


class d2dCommandResponse(dict):

    def __init__(self, str_response):
        super().__init__()

        try:
            response_dict = json.loads(str_response)
            for item in response_dict:
                self[item] = response_dict[item]
            self.__success = True
            self.__error = None


        except:
            if isinstance(str_response, str):
                self.__error = str_response
            else:
                self.__error = d2dConstants.commandErrorMsg.EXCEPTION_ERROR
            self.__success = False

    @property
    def error(self):
        return self.__error


    @property
    def success(self):
        return self.__success


class d2dCommand():

    def __init__(self,mac, service, category, name, protocol, ip, port, params, response, enable, timeout, service_info):
        self.__name = name
        self.__mac = mac
        self.__service = service
        self.__category = category
        self.__params = params
        self.__response = response
        self.__protocol = protocol
        self.__enable = enable
        self.__timeout = timeout
        self.__service_info = service_info
        if enable and service_info.online:
            if protocol == d2dConstants.commandProtocol.JSON_UDP:
                self.__socket = udpClient(ip, port)

            elif protocol == d2dConstants.commandProtocol.JSON_TCP:
                self.__socket = tcpClient(ip, port)

            else:
                self.__socket = None
        else:
            self.__socket = None


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


    @property
    def enable(self):
        return self.__enable and self.__service_info.online


    @property
    def protocol(self):
        return self.__protocol


    def call(self, args:dict, timeout=None) -> dict:

        if not timeout:
            timeout = self.__timeout

        if self.__socket == None:
            return d2dConstants.commandErrorMsg.NOT_ENABLE_ERROR

        try:
            response = d2dConstants.commandErrorMsg.CONNECTION_ERROR
            self.__socket.send(json.dumps(args, indent=1))
            response = self.__socket.read(timeout)
            if response:
                response = response.decode()
                while response.startswith("{") and not response.endswith("}"):
                    read_response = self.__socket.read(timeout)
                    if read_response:
                        response += read_response.decode()
                    else:
                        break

        except:
            pass

        if not response or response == "":
            response = d2dConstants.commandErrorMsg.TIMEOUT_ERROR

        return d2dCommandResponse(response) 


class d2dInfo():

    def __init__(self,mac, service, category, name, value, valueType, epoch, service_info):
        self.__name = name
        self.__mac = mac
        self.__service = service
        self.__category = category
        self.__value = value
        self.__epoch = epoch
        self.__valueType = valueType
        self.__service_info = service_info

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

    @property
    def online(self):
        return self.__service_info.online


class d2d():

    def __init__(self, broker_discover_timeout=5, broker_discover_retry=-1, service=None):
        self.__mac = hex(uuid.getnode()).replace("0x", "")

        if service:
            self.__service = service
        else:
            process = psutil.Process(os.getpid())
            process_name = process.name()
            self.__service = process_name.split(".")[0]

        self.__broker_discover_timeout = broker_discover_timeout
        self.__broker_discover_retry = broker_discover_retry

        self.__threads = []
        self.__command_sockets = []
        self.__service_container = {}
        self.__local_path = d2dConstants.MQTT_PREFIX + "/" + self.__mac + "/" + self.__service + "/"
        self.__callback_mutex = threading.RLock()
        self.__registered_mutex = threading.RLock()
        self.__command_update_callback = None
        self.__info_update_callback = None
        self.__command_remove_callback = None
        self.__info_remove_callback = None
        self.__registered_commands = {}
        self.__subscribe_patterns = []
        self.__registered_info = {}
        self.__service_used_paths = {}
        self.__services = {}
        self.__info_used_paths = {}
        self.__unused_received_paths = []

        self.__subscriptions = []
        self.__publications = {}
        self.__client = None

        self.__checkBrokerConnection()


    def __del__(self):
        if self.__client:
            self.__client.disconnect()

        for name in self.__service_container:
            self.__service_container[name].run = False

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
        with self.__callback_mutex:
            return self.__command_update_callback


    @onCommandUpdate.setter
    def onCommandUpdate(self, callback):
        with self.__callback_mutex:
            self.__command_update_callback = callback


    @property
    def onCommandRemove(self):
        with self.__callback_mutex:
            return self.__command_remove_callback


    @onCommandRemove.setter
    def onCommandRemove(self, callback):
        with self.__callback_mutex:
            self.__command_remove_callback = callback


    @property
    def onInfoUpdate(self):
        with self.__callback_mutex:
            return self.__info_update_callback


    @onInfoUpdate.setter
    def onInfoUpdate(self, callback):
        with self.__callback_mutex:
            self.__info_update_callback = callback


    @property
    def onInfoRemove(self):
        with self.__callback_mutex:
            return self.__info_remove_callback


    @onInfoRemove.setter
    def onInfoRemove(self, callback):
        with self.__callback_mutex:
            self.__info_remove_callback = callback


    def __brokerMessageReceived(message, weak_self):

        self = weak_self()
        if not self:
            return

        # Remove unregistered device/service data
        with self.__registered_mutex:
            if message.topic.startswith(self.__local_path) and len(message.payload) > 0:
                if message.topic not in self.__service_used_paths.values() \
                    and message.topic not in self.__info_used_paths.values():
                    if message.topic not in self.__unused_received_paths:
                        self.__unused_received_paths.append(message.topic)
                return

        topic_split = message.topic.split("/")
        if len(topic_split) < 4:
            return

        prefix = topic_split[0]
        mac = topic_split[1]
        service = topic_split[2]
        mode = topic_split[3]
        service_path = prefix + "/" + mac + "/" + service

        if prefix != d2dConstants.MQTT_PREFIX:
            return

        with self.__registered_mutex:
            if service_path not in self.__services:
                self.__services[service_path] = container()
            self.__services[service_path].online = True


        if mode == d2dConstants.STATE:
            with self.__registered_mutex:
                self.__services[service_path].online = message.payload.decode() != d2dConstants.state.OFFLINE

                with self.__callback_mutex:
                    if self.__command_update_callback:
                        for command_path in self.__registered_commands:
                            self.__command_update_callback(self.__registered_commands[command_path])
                    if self.__info_update_callback:
                        for info_path in self.__registered_info:
                            self.__info_update_callback(self.__registered_info[info_path])

            return


        if len(topic_split) < 6:
            return
        category = topic_split[4]
        name = "/".join(topic_split[5:])

        ok = False
        for subscriber in self.__subscribe_patterns:

            if re.search(subscriber, message.topic):
                ok = True
                break
        if not ok:
            return



        try:
            command_info = json.loads(message.payload)
        except:
            command_info = None

        if command_info:

            if mode == d2dConstants.COMMAND_LEVEL:

                try:
                    protocol = command_info[d2dConstants.commandField.PROTOCOL]
                    ip = command_info[d2dConstants.commandField.IP]
                    port = command_info[d2dConstants.commandField.PORT]
                    params = command_info[d2dConstants.commandField.INPUT]
                    response = command_info[d2dConstants.commandField.OUTPUT]
                    enable = True if d2dConstants.commandField.ENABLE not in command_info else command_info[d2dConstants.commandField.ENABLE]
                    timeout = 5 if d2dConstants.commandField.TIMEOUT not in command_info else command_info[d2dConstants.commandField.TIMEOUT]
                except:
                    return

                command_object = d2dCommand(mac, service, category, name, protocol, ip, port, params, response, enable, timeout, self.__services[service_path])
                with self.__registered_mutex:
                    self.__registered_commands[message.topic] = command_object

                with self.__callback_mutex:
                    if self.__command_update_callback:
                        self.__command_update_callback(command_object)

            elif mode == d2dConstants.INFO_LEVEL:
                try:
                    value = command_info[d2dConstants.infoField.VALUE]
                    valtype = command_info[d2dConstants.infoField.TYPE]
                    epoch = command_info[d2dConstants.infoField.EPOCH]
                except:
                    return

                info_object = d2dInfo(mac, service, category, name, value, valtype, epoch, self.__services[service_path])
                with self.__registered_mutex:
                    self.__registered_info[message.topic] = info_object

                with self.__callback_mutex:
                    if self.__info_update_callback:
                        self.__info_update_callback(info_object)

        else:
            removed_item = None

            if mode == d2dConstants.COMMAND_LEVEL:
                with self.__registered_mutex:
                    if message.topic in self.__registered_commands:
                        removed_item = self.__registered_commands.pop(message.topic)

                if removed_item:
                    with self.__callback_mutex:
                        if self.__command_remove_callback:
                            self.__command_remove_callback(removed_item)

            elif mode == d2dConstants.INFO_LEVEL:
                with self.__registered_mutex:
                    if message.topic in self.__registered_info:
                        removed_item = self.__registered_info.pop(message.topic)

                if removed_item:
                    with self.__callback_mutex:
                        if self.__info_remove_callback:
                            self.__info_remove_callback(removed_item)


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

        version_array = paho.mqtt.__version__.split(".")
        if version_array[0] == "1":
            client = paho.mqtt.client.Client()
        else:
            client = paho.mqtt.client.Client(paho.mqtt.client.CallbackAPIVersion.VERSION1)

        try:
            client.will_set(self.__local_path + d2dConstants.STATE, payload=d2dConstants.state.OFFLINE, qos=1, retain=True)
            client.connect(broker_ip, d2dConstants.MQTT_BROKER_PORT)
        except:
            return False

        client.on_message = lambda client, weak_self, message : d2d.__brokerMessageReceived(message, weak_self)
        client.on_connect = lambda client, weak_self, flags, rc : d2d.__onConnect(weak_self)
        client.user_data_set(weakref.ref(self))
        client.loop_start()

        self.__client = client

        self.__subscribe(self.__local_path + "#")
        self.__subscribe(d2dConstants.MQTT_PREFIX + "/+/+/" + d2dConstants.STATE)

        return True


    def __onConnect(weak_self):
        self = weak_self()
        if not self:
            return

        with self.__registered_mutex:
            for path in self.__publications:
                try:
                    self.__client.publish(path, payload=self.__publications[path], qos=1, retain=True)
                except:
                    pass

            for path in self.__subscriptions:
                try:
                    self.__client.subscribe(path, qos=1)
                except:
                    pass


    def __checkIfRegEx(string):
        return ".*" in string or "(" in string or "[" in string or ")" in string or "]" in string or "|" in string


    def __createMQTTPath(self, mac, service, category, mode, name) -> str:

        if mode not in [d2dConstants.COMMAND_LEVEL, d2dConstants.INFO_LEVEL]:
            return ""

        if "#" in mac + service + category + mode + name:
            return None

        mqtt_path = d2dConstants.MQTT_PREFIX + "/"

        if mac != "" and not d2d.__checkIfRegEx(mac):

            mqtt_path += mac + "/"
        else:
            mqtt_path += "+/"

        if service != "" and not d2d.__checkIfRegEx(service):
            mqtt_path += service + "/"
        else:
            mqtt_path += "+/"

        mqtt_path += mode + "/"

        if category != "" and not d2d.__checkIfRegEx(category):
            mqtt_path += category + "/"
        else:
            mqtt_path += "+/"

        if name != "" and not d2d.__checkIfRegEx(name):
            mqtt_path += name
        else:
            mqtt_path += "#"

        return mqtt_path


    def __createRegexPath(self, mac, service, category, mode, name) -> str:

        if mode not in [d2dConstants.COMMAND_LEVEL, d2dConstants.INFO_LEVEL]:
            return ""

        regex_path = d2dConstants.MQTT_PREFIX + "/"

        if mac != "":
            regex_path += mac + "/"
        else:
            regex_path += ".*/"

        if service != "":
            regex_path += service + "/"
        else:
            regex_path += ".*/"

        regex_path += mode + "/"

        if category != "":
            regex_path += category + "/"
        else:
            regex_path += ".*/"

        if name != "":
            regex_path += name
        else:
            regex_path += ".*"

        regex_path = regex_path.replace("#", "")

        return regex_path


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


    def __jsonCommandRequest(request, service_container, command_callback, input_params, output_params):

            # json -> map
            try:
                args = json.loads(request)

            except:
                return d2dConstants.commandErrorMsg.BAD_INPUT



            # Ignore if disable
            if not service_container.map[d2dConstants.commandField.ENABLE]:
                return d2dConstants.commandErrorMsg.NOT_ENABLE_ERROR


            # Check args
            if not d2d.__checkInOutField(args, input_params):
                return d2dConstants.commandErrorMsg.BAD_INPUT


            # Call command
            response_dict = command_callback(args)
            if isinstance(response_dict, dict):

                # Check args
                if not d2d.__checkInOutField(response_dict, output_params):
                    return d2dConstants.commandErrorMsg.BAD_OUTPUT

                else:
                    # map -> json
                    response = json.dumps(response_dict, indent=1)
                    return response

            else:
                return d2dConstants.commandErrorMsg.CALLBACK_ERROR


    def __udpListenerThread(socket, service_container, command_callback, input_params, output_params):

        while service_container.run:
            request, ip, port = socket.read()
            if not request:
                break

            response = d2d.__jsonCommandRequest(request, service_container, command_callback, input_params, output_params)
            try:
                socket.send(ip, port, response)

            except:
                pass


    def __tcpListenerThread(socket, service_container, command_callback, input_params, output_params):

        mutex = threading.Lock()
        threads_list = []
        while service_container.run:

            # Wait connection
            connection = socket.waitConnection()
            if not connection:
                break

            # Launch thread
            thread = threading.Thread(target=d2d.__tcpConnectionThread, daemon=True, args=[connection, service_container, command_callback, input_params, output_params, mutex])
            thread.start()

            threads_list.append(thread)

        # Wait connection threads
        socket.close()
        for thread in threads_list:
            thread.join()


    def __tcpConnectionThread(connection, service_container, command_callback, input_params, output_params, mutex):

        while service_container.run:

            request = connection.read()
            if not request:
                break

            with mutex:
                response = d2d.__jsonCommandRequest(request, service_container, command_callback, input_params, output_params)
                try:
                    connection.send(response)

                except:
                    pass


    def __publish(self, path, payload=None):
        if not payload:
            self.__client.publish(path, payload=None, qos=1, retain=True)
            with self.__registered_mutex:
                if path in self.__publications:
                    self.__publications.pop(path)

            return True

        else:
            if path not in self.__publications or self.__publications[path] != payload:
                try:
                    msg_info = self.__client.publish(path, payload=payload, qos=1, retain=True)
                    if msg_info.rc == paho.mqtt.client.MQTT_ERR_SUCCESS:
                        with self.__registered_mutex:
                            self.__publications[path] = payload
                        return True
                    else:
                        return False

                except:
                    return False

            else:
                return True


    def __subscribe(self, mqtt_path):
        if mqtt_path not in self.__subscriptions:
            try:
                self.__client.subscribe(mqtt_path, qos=1)
                with self.__registered_mutex:
                    self.__subscriptions.append(mqtt_path)
            except:
                return False

        return True


    def addServiceCommand(self, cmdCallback, name:str, input_params:dict, output_params:dict, category:str="", enable=True, timeout=5, protocol=d2dConstants.commandProtocol.JSON_UDP)-> bool:

        if not cmdCallback:
            return False

        for field in input_params:
            if not d2d.__checkInOutDefinedField(input_params[field]):
                return False

        for field in output_params:
            if not d2d.__checkInOutDefinedField(output_params[field]):
                return False

        if not self.__checkBrokerConnection():
            return False

        if category == "":
            category = d2dConstants.category.GENERIC


        self.__service_container[name] = container()
        self.__service_container[name].run = True

        if protocol == d2dConstants.commandProtocol.JSON_UDP:
            listen_socket = udpRandomPortListener()
            self.__command_sockets.append(listen_socket)
            thread = threading.Thread(target=d2d.__udpListenerThread, daemon=True, args=[listen_socket, self.__service_container[name], cmdCallback, input_params, output_params])
            thread.start()
            self.__threads.append(thread)

        elif protocol == d2dConstants.commandProtocol.JSON_TCP:
            listen_socket = tcpRandomPortListener()
            self.__command_sockets.append(listen_socket)
            thread = threading.Thread(target=d2d.__tcpListenerThread, daemon=True, args=[listen_socket, self.__service_container[name], cmdCallback, input_params, output_params])
            thread.start()
            self.__threads.append(thread)

        else:
            return False


        mqtt_path = self.__createMQTTPath(self.__mac, self.__service, category, d2dConstants.COMMAND_LEVEL, name)
        if not mqtt_path:
            return False
        self.__service_used_paths[name] = mqtt_path

        self.__service_container[name].map = {}
        self.__service_container[name].map[d2dConstants.commandField.PROTOCOL] = protocol
        self.__service_container[name].map[d2dConstants.commandField.IP] = listen_socket.ip
        self.__service_container[name].map[d2dConstants.commandField.PORT] = listen_socket.port
        self.__service_container[name].map[d2dConstants.commandField.INPUT] = input_params
        self.__service_container[name].map[d2dConstants.commandField.OUTPUT] = output_params
        self.__service_container[name].map[d2dConstants.commandField.ENABLE] = enable
        self.__service_container[name].map[d2dConstants.commandField.TIMEOUT] = timeout

        return self.__publish(self.__service_used_paths[name], payload=json.dumps(self.__service_container[name].map, indent=1))


    def enableCommand(self, name, enable):
        if name not in self.__service_container:
            return False

        self.__service_container[name].map[d2dConstants.commandField.ENABLE] = enable
        return self.__publish(self.__service_used_paths[name], payload=json.dumps(self.__service_container[name].map, indent=1))


    def subscribeComands(self, mac:str="", service:str="", category:str="", command:str="") -> bool:

        if not self.__checkBrokerConnection():
            return False

        regex_path = self.__createRegexPath(mac, service, category, d2dConstants.COMMAND_LEVEL, command)
        mqtt_path = self.__createMQTTPath(mac, service, category, d2dConstants.COMMAND_LEVEL, command)
        if not mqtt_path:
            return False

        if not self.__subscribe(mqtt_path):
            return False

        if regex_path not in self.__subscribe_patterns:
            self.__subscribe_patterns.append(regex_path)

        return True


    def getAvailableComands(self, mac:str="", service:str="", category:str="", command:str="") -> list:

        mqtt_pattern_path = self.__createRegexPath(mac, service, category, d2dConstants.COMMAND_LEVEL, command)

        commands = []
        with self.__registered_mutex:
            for mqtt_path in self.__registered_commands:
                if re.search(mqtt_pattern_path, mqtt_path):
                    commands.append(self.__registered_commands[mqtt_path])

        return commands


    def subscribeInfo(self, mac:str="", service:str="", category="", name:str="") -> bool:
        if not self.__checkBrokerConnection():
            return False

        mqtt_path = self.__createMQTTPath(mac, service, category, d2dConstants.INFO_LEVEL, name)
        regex_path = self.__createRegexPath(mac, service, category, d2dConstants.INFO_LEVEL, name)

        if not self.__subscribe(mqtt_path):
            return False

        if regex_path not in self.__subscribe_patterns:
            self.__subscribe_patterns.append(regex_path)

        return True


    def getSubscribedInfo(self, mac:str="", service:str="", category="", name:str="") -> dict:
        mqtt_pattern_path = self.__createRegexPath(mac, service, category, d2dConstants.INFO_LEVEL, name)

        info = []
        with self.__registered_mutex:
            for mqtt_path in self.__registered_info:
                if re.search(mqtt_pattern_path, mqtt_path):
                    info.append(self.__registered_info[mqtt_path])

        return info


    def publishInfo(self, name:str, value:str, category:str) -> bool:
        if not self.__checkBrokerConnection():
            return False

        if category == "":
            category = d2dConstants.category.GENERIC

        mqtt_path = self.__createMQTTPath(self.__mac, self.__service, category, d2dConstants.INFO_LEVEL, name)
        if not mqtt_path:
            return False
        self.__info_used_paths[name] = mqtt_path

        value_type = self.__getType(value)
        if value_type == "":
            return False

        mqtt_msg = {}
        mqtt_msg[d2dConstants.infoField.VALUE] = value
        mqtt_msg[d2dConstants.infoField.TYPE] = value_type
        mqtt_msg[d2dConstants.infoField.EPOCH] = int(time.time())
        return self.__publish(self.__info_used_paths[name], payload=json.dumps(mqtt_msg, indent=1))


    def removeUnregistered(self):
        with self.__registered_mutex:
            for path in self.__unused_received_paths:
                if path not in self.__service_used_paths.values() \
                    and path not in self.__info_used_paths.values():

                    self.__publish(path)

            self.__unused_received_paths.clear()
