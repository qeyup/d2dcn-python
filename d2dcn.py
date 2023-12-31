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
import struct
import threading
import time
import uuid
import psutil
import json
import re
import paho.mqtt.client


class d2dConstants():
    MCAST_DISCOVER_GRP = '224.1.1.1'
    MCAST_DISCOVER_SERVER_PORT = 5005
    MCAST_DISCOVER_CLIENT_PORT = 5006
    MQTT_BROKER_PORT = 1883
    MULTICAST_TTL = 2
    DISCOVER_MSG_REQUEST = b"Who's broker?"
    DISCOVER_MSG_RESPONSE = b"I'm broker"
    MQTT_PREFIX = "d2dcn"
    COMMAND_LEVEL = "command"
    INFO_LEVEL = "info"
    GENERIC_TYPE = "generic"

    class commandField():
        PROTOCOL = "protocol"
        IP = "ip"
        PORT = "port"
        PARAMS = "params"
        RESPONSE = "response"

    class commandProtocol():
        JSON_UDP = "json-udp"

    class infoField():
        VALUE = "value"
        TYPE = "type"
        EPOCH = "epoch"

    class valueTypes():
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

            except:
                return None, None, None

        return None, None, None


    def send(self, msg):
        self.__sock.sendto(msg, (self.__ip, self.__port))


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


class mcast():

    def __init__(self, ip, port):
        self.__ip = ip
        self.__port = port
        self.__open = True
        self.__sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.__sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.__sock.bind((ip, port))
        self.__sock.settimeout(0.1)

        mreq = struct.pack("4sl", socket.inet_aton(ip), socket.INADDR_ANY)
        self.__sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)


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

            except:
                return None, None, None

        return None, None, None


    def send(self, msg):
        self.__sock.sendto(msg, (self.__ip, self.__port))


    def close(self):
        self.__open = False
        self.__sock.close()


class d2dBrokerDiscover():

    def __init__(self):
        self.__thread = None
        self.__shared_container = container()
        self.__shared_container.run = True
        self.__shared_container.mcast_listen_request = mcast(d2dConstants.MCAST_DISCOVER_GRP, d2dConstants.MCAST_DISCOVER_SERVER_PORT)
        self.__shared_container.mcast_send_respond = mcast(d2dConstants.MCAST_DISCOVER_GRP, d2dConstants.MCAST_DISCOVER_CLIENT_PORT)


    def __del__(self):
        self.stop()
        if self.__thread:
            self.__thread.join()


    def __run(shared_container):

        while shared_container.run:
            read, ip, port = shared_container.mcast_listen_request.read()
            if not read:
                break

            if read == d2dConstants.DISCOVER_MSG_REQUEST:
                shared_container.mcast_send_respond.send(d2dConstants.DISCOVER_MSG_RESPONSE)


    def run(self, thread=False):
        if thread:
            self.__thread  = threading.Thread(target=d2dBrokerDiscover.__run, daemon=True, args=[self.__shared_container])
            self.__thread .start()
            return self.__thread
        else:
            d2dBrokerDiscover.__run(self.__mcast)
            return None


    def stop(self):
        self.__shared_container.run = False
        self.__shared_container.mcast_listen_request.close()
        self.__shared_container.mcast_send_respond.close()


class d2dCommand():

    def __init__(self,mac, service, type, name, protocol, ip, port, params, response):
        self.__name = name
        self.__mac = mac
        self.__service = service
        self.__type = type
        self.__params = params
        self.__response = response

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
    def type(self):
        return self.__type

    @property
    def params(self):
        return self.__params

    @property
    def response(self):
        return self.__response

    def call(self, args:dict) -> dict:
        return False


class d2dInfo():

    def __init__(self,mac, service, type, name, value, valueType, epoch):
        self.__name = name
        self.__mac = mac
        self.__service = service
        self.__type = type
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
    def type(self):
        return self.__type

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

    def __init__(self):
        self.__mac = hex(uuid.getnode()).replace("0x", "")

        process = psutil.Process(os.getpid())
        process_name = process.name()
        self.__service = process_name.split(".")[0]

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
        type = topic_split[4]
        name = topic_split[5]

        if prefix != d2dConstants.MQTT_PREFIX:
            return

        if mode == d2dConstants.COMMAND_LEVEL:

            try:
                protocol = command_info[d2dConstants.commandField.PROTOCOL]
                ip = command_info[d2dConstants.commandField.IP]
                port = command_info[d2dConstants.commandField.PORT]
                params = command_info[d2dConstants.commandField.PARAMS]
                response = command_info[d2dConstants.commandField.RESPONSE]
            except:
                return

            command_object = d2dCommand(mac, service, type, name, protocol, ip, port, params, response)
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

            info_object = d2dInfo(mac, service, type, name, value, valtype, epoch)
            with shared_container.registered_mutex:
                shared_container.registered_info[message.topic] = info_object

            with shared_container.callback_mutex:
                if shared_container.info_update_callback:
                    shared_container.info_update_callback(info_object)


    def __checkBrokerConnection(self) -> bool:

        if self.__client:
            return self.__client.is_connected()


        broker_ip = self.getBrokerIP()
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


    def __createMQTTPath(self, mac, service, type, mode, name) -> str:

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

        if type != "":
            mqtt_path += type + "/"
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
        elif isinstance(data, int):
            return d2dConstants.valueTypes.INT
        elif isinstance(data, str):
            return d2dConstants.valueTypes.STRING
        else:
            return ""


    def __commandListenThead(socket, shared_container):
        while shared_container.run:
            read, ip, port = socket.read()
            if not read:
                break

            print(ip, port, read)


    def getBrokerIP(self, timeout=5) -> str:
        mcast_send_request = mcast(d2dConstants.MCAST_DISCOVER_GRP, d2dConstants.MCAST_DISCOVER_SERVER_PORT)
        mcast_listen_respond = mcast(d2dConstants.MCAST_DISCOVER_GRP, d2dConstants.MCAST_DISCOVER_CLIENT_PORT)

        mcast_send_request.send(d2dConstants.DISCOVER_MSG_REQUEST)
        response, ip, port = mcast_listen_respond.read(timeout)
        if response == d2dConstants.DISCOVER_MSG_RESPONSE:
            return ip
        else:
            return None


    def addServiceCommand(self, cmdCallback, name:str, params:dict, response:dict, type:str="")-> bool:

        if not self.__checkBrokerConnection():
            return False

        if type == "":
            type = d2dConstants.GENERIC_TYPE


        listen_socket = udpRandomPortListener()
        self.__command_sockets.append(listen_socket)
        thread = threading.Thread(target=d2d.__commandListenThead, daemon=True, args=[listen_socket, self.__shared_container])
        thread.start()
        self.__threads.append(thread)


        mqtt_path = self.__createMQTTPath(self.__mac, self.__service, type, d2dConstants.COMMAND_LEVEL, name)

        mqtt_msg = {}
        mqtt_msg[d2dConstants.commandField.PROTOCOL] = d2dConstants.commandProtocol.JSON_UDP
        mqtt_msg[d2dConstants.commandField.IP] = listen_socket.ip
        mqtt_msg[d2dConstants.commandField.PORT] = listen_socket.port
        mqtt_msg[d2dConstants.commandField.PARAMS] = params
        mqtt_msg[d2dConstants.commandField.RESPONSE] = response

        self.__client.publish(mqtt_path, payload=json.dumps(mqtt_msg), qos=0, retain=True)

        return True


    def subscribeComands(self, mac:str="", service:str="", type:str="", command:str="") -> bool:

        if not self.__checkBrokerConnection():
            return False

        mqtt_path = self.__createMQTTPath(mac, service, type, d2dConstants.COMMAND_LEVEL, command)

        try:
            self.__client.subscribe(mqtt_path)
        except:
            return False

        return True


    def getAvailableComands(self, mac:str="", service:str="", type:str="", command:str="") -> list:

        mqtt_pattern_path = self.__createMQTTPath(mac, service, type, d2dConstants.COMMAND_LEVEL, command)
        mqtt_pattern_path = mqtt_pattern_path.replace("+", ".*")

        commands = []
        with self.__shared_container.registered_mutex:
            for mqtt_path in self.__shared_container.registered_commands:
                if re.search(mqtt_pattern_path, mqtt_path):
                    commands.append(self.__shared_container.registered_commands[mqtt_path])

        return commands


    def subscribeInfo(self, mac:str="", service:str="", type="", name:str="") -> bool:
        if not self.__checkBrokerConnection():
            return False

        mqtt_path = self.__createMQTTPath(mac, service, type, d2dConstants.INFO_LEVEL, name)

        try:
            self.__client.subscribe(mqtt_path)
        except:
            return False

        return True


    def getSubscribedInfo(self, mac:str="", service:str="", type="", name:str="") -> dict:
        mqtt_pattern_path = self.__createMQTTPath(mac, service, type, d2dConstants.INFO_LEVEL, name)
        mqtt_pattern_path = mqtt_pattern_path.replace("+", ".*")

        info = []
        with self.__shared_container.registered_mutex:
            for mqtt_path in self.__shared_container.registered_info:
                if re.search(mqtt_pattern_path, mqtt_path):
                    info.append(self.__shared_container.registered_info[mqtt_path])

        return info


    def publishInfo(self, name:str, value:str, type:str) -> bool:
        if not self.__checkBrokerConnection():
            return False

        if type == "":
            type = d2dConstants.GENERIC_TYPE

        mqtt_path = self.__createMQTTPath(self.__mac, self.__service, type, d2dConstants.INFO_LEVEL, name)

        value_type = self.__getType(value)
        if value_type == "":
            return False

        mqtt_msg = {}
        mqtt_msg[d2dConstants.infoField.VALUE] = value
        mqtt_msg[d2dConstants.infoField.TYPE] = value_type
        mqtt_msg[d2dConstants.infoField.EPOCH] = int(time.time())
        self.__client.publish(mqtt_path, payload=json.dumps(mqtt_msg), qos=0, retain=True)

        return True