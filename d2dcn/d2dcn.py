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
import SharedTableBroker
import weakref
import struct

if os.name != 'nt':
    from pyroute2 import IPRoute

if not hasattr(socket, "IP_ADD_SOURCE_MEMBERSHIP"):
    setattr(socket, "IP_ADD_SOURCE_MEMBERSHIP", 39)


version = "0.5.0"


class d2dConstants():
    BROKER_SERVICE_NAME = "D2D_TABLE"
    BROKER_PORT = 18832
    CLIENT_DISCOVER_WAIT = 5
    MTU = 4096
    END_OF_TX = b'\xFF'
    MAX_LISTEN_TCP_SOKETS = -1
    MQTT_PREFIX = "d2dcn"
    PREFIX = "d2dcn"
    COMMAND_LEVEL = "command"
    INFO_LEVEL = "info"
    STATE = "state"
    INFO_MULTICAST_GROUP = "232.10.10.10"
    INFO_REQUEST = b"req"

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

    class infoField():
        PROTOCOL = "protocol"
        IP = "ip"
        REQUEST_PORT = "req_port"
        UPDATE_PORT = "update_port"
        TYPE = "type"

        # Remove
        EPOCH = "epoch"
        VALUE = "value"

    class commandProtocol():
        JSON_UDP = "json-udp"
        JSON_TCP = "json-tcp"

    class infoProtocol():
        ASCII = "ASCII"

    class field():
        TYPE = "type"
        OPTIONAL = "optional"

    class valueTypes():
        ARRAY = "array"
        BOOL = "bool"
        BOOL_ARRAY = "bool_" + ARRAY
        INT = "int"
        INT_ARRAY = "int_" + ARRAY
        STRING = "string"
        STRING_ARRAY = "string_" + ARRAY
        FLOAT = "float"
        FLOAT_ARRAY = "float_" + ARRAY


class container():
    pass


class mcast():

    def __init__(self, ip:str, port:int=0, src:str=""):
        self.__ip = ip
        self.__open = True
        self.__sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)

        self.__sock.settimeout(0.1)

        self.__sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if src != "":
            self.__sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_SOURCE_MEMBERSHIP,
                struct.pack("=4sl4s", socket.inet_aton(ip), socket.INADDR_ANY, socket.inet_aton(src)))
        else:
            self.__sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP,
                struct.pack("=4sl", socket.inet_aton(ip), socket.INADDR_ANY))

        if os.name != 'nt':
            self.__sock.bind((ip, port))
        else:
            self.__sock.bind(('', port))

        self.__port = self.__sock.getsockname()[1]


    def __del__(self):
        self.close()


    @property
    def port(self):
        return self.__port


    def read(self, timeout=-1):

        current_epoch_time = float(time.time())
        while self.__open:
            try:
                data, (ip, port) = self.__sock.recvfrom(4096)
                return data, ip, port

            except socket.timeout:
                if timeout >= 0 and float(time.time()) - current_epoch_time >= timeout:
                    return None, None, None

            except socket.error:
                return None, None, None


        return None, None, None


    def send(self, msg):
        if isinstance(msg, str):
            msg = msg.encode()
        try:
            self.__sock.sendto(msg, (self.__ip, self.__port))
            return True

        except:
            return False


    def close(self):
        self.__open = False
        self.__sock.close()


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


class tcpListener():


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

                    if len(data) > 0:
                        return data

                    else:
                        self.close()
                        self.__open = False
                        return None

                except socket.timeout:
                    if timeout >= 0 and int(time.time()) - current_epoch_time >= timeout:
                        return None

                except socket.error:
                    self.close()
                    self.__open = False
                    return None


        def send(self, msg):
            if isinstance(msg, str):
                msg = msg.encode()

            chn_msg = [msg[idx : idx + d2dConstants.MTU] for idx in range(0, len(msg), d2dConstants.MTU)]

            try:
                for chn in chn_msg:
                    self.__sock.sendall(chn)

            except:
                return False

            return True


        def isConnected(self):
            return self.__open


        @property
        def port(self):
            return self.__sock.getsockname()[1]


        @property
        def clientIp(self):
            return self.__ip


        @property
        def clientPort(self):
            return self.__port


        def close(self):
            self.__open = False
            self.__sock.close()


    def __init__(self, port=0, max_connections=d2dConstants.MAX_LISTEN_TCP_SOKETS):
        super().__init__()
        self.__open = True
        self.__sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.__sock.bind(('', port))
        self.__sock.settimeout(0.1)
        self.__sock.listen(max_connections)


    def __del__(self):
        self.close()


    @property
    def port(self):
        return self.__sock.getsockname()[1]


    def waitConnection(self, timeout=-1):

        current_epoch_time = int(time.time())
        while self.__open:
            try:
                connection, (ip, port) = self.__sock.accept()
                return tcpListener.connection(connection, ip, port)


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


    def connect(self):
        if not self.__open:
            self.__open = self.__sock.connect_ex((self.__remote_ip, self.__remote_port)) == 0
        return self.__open


    def read(self, timeout=-1):

        if self.connect():
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
        if self.connect():

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
    def connected(self):
        return self.__open


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


class typeTools():

    def getType(data) -> str:

        if isinstance(data, float):
            return d2dConstants.valueTypes.FLOAT

        elif isinstance(data, bool):
            return d2dConstants.valueTypes.BOOL

        elif isinstance(data, int):
            return d2dConstants.valueTypes.INT

        elif isinstance(data, str):
            return d2dConstants.valueTypes.STRING

        elif isinstance(data, list):

            detected_type = ""
            for item in data:
                if detected_type == "":
                    detected_type = typeTools.getType(item)
                    if detected_type == "":
                        return ""
                else:
                    aux = typeTools.getType(item)
                    if aux != detected_type:
                        return ""

            if len(data) == 0:
                return d2dConstants.valueTypes.ARRAY
            
            elif detected_type == d2dConstants.valueTypes.FLOAT:
                return d2dConstants.valueTypes.FLOAT_ARRAY

            elif detected_type == d2dConstants.valueTypes.BOOL:
                return d2dConstants.valueTypes.BOOL_ARRAY

            elif detected_type == d2dConstants.valueTypes.INT:
                return d2dConstants.valueTypes.INT_ARRAY

            elif detected_type == d2dConstants.valueTypes.STRING:
                return d2dConstants.valueTypes.STRING_ARRAY

            else:
                return ""

        else:
            return ""


    def checkFieldType(field, field_type):
        detected_type = typeTools.getType(field)

        if detected_type == field_type:
            return True

        elif detected_type == d2dConstants.valueTypes.ARRAY and d2dConstants.valueTypes.ARRAY in field_type:
            return True
        
        else:
            return False


    def convevertFromASCII(data, data_type):

        try:
            if data_type == d2dConstants.valueTypes.BOOL:
                return bool(int(data))

            elif data_type == d2dConstants.valueTypes.INT:
                return int(data)

            elif data_type == d2dConstants.valueTypes.STRING:
                return str(data)

            elif data_type == d2dConstants.valueTypes.FLOAT:
                return float(data)

            elif data_type == d2dConstants.valueTypes.ARRAY or d2dConstants.valueTypes.ARRAY in data_type:
                
                rl = []
                aux_list = json.loads(data)
                for item in aux_list:
                    if data_type == d2dConstants.valueTypes.BOOL_ARRAY:
                        rl.append(bool(item))

                    elif data_type == d2dConstants.valueTypes.INT_ARRAY:
                        rl.append(int(item))

                    elif data_type == d2dConstants.valueTypes.STRING_ARRAY:
                        rl.append(str(item))

                    elif data_type == d2dConstants.valueTypes.FLOAT_ARRAY:
                        rl.append(float(item))

                return rl

            else:
                return None

        except:
            return None


    def convertToASCII(data, data_type):
        try:
            if data_type == d2dConstants.valueTypes.BOOL:
                return str(1 if data else 0)

            elif data_type == d2dConstants.valueTypes.INT:
                return str(data)

            elif data_type == d2dConstants.valueTypes.STRING:
                return str(data)

            elif data_type == d2dConstants.valueTypes.FLOAT:
                return str(data)

            elif data_type == d2dConstants.valueTypes.ARRAY or d2dConstants.valueTypes.ARRAY in data_type:
                if not isinstance(data, list):
                    return None

                return json.dumps(data)

            else:
                return None

        except:
            return None


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

    def __init__(self, mac, service, category, name, protocol, ip, port, params, response, enable, timeout, service_info=None):
        self.__name = name
        self.__mac = mac
        self.__service = service
        self.__category = category
        self.configure(enable, params, response, protocol, ip, port, timeout)


    def configure(self, enable, params=None, response=None, protocol=None, ip=None, port=None, timeout=None):

        if params:
            self.__params = params
        if response:
            self.__response = response

        self.__protocol = protocol
        self.__enable = enable
        self.__timeout = timeout

        if enable:
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
            return d2dCommandResponse(d2dConstants.commandErrorMsg.NOT_ENABLE_ERROR)

        try:
            response = d2dConstants.commandErrorMsg.CONNECTION_ERROR
            self.__socket.send(json.dumps(args, indent=1))
            socket_response = self.__socket.read(timeout)
            if socket_response:
                response = socket_response.decode()
                while response.startswith("{") and not response.endswith("}"):
                    read_response = self.__socket.read(timeout)
                    if read_response:
                        response += read_response.decode()
                    else:
                        break
            else:
                response = d2dConstants.commandErrorMsg.TIMEOUT_ERROR

        except:
            pass


        return d2dCommandResponse(response) 


class d2dInfoWriter():

    def __init__(self,mac, service, category, name, valueType):

        self.__shared = container()
        self.__shared.run = True
        self.__shared.udp_socket = None
        self.__shared.mcast_socket = None
        self.__shared.name = name
        self.__shared.mac = mac
        self.__shared.service = service
        self.__shared.category = category
        self.__shared.valueType = valueType


        if valueType == d2dConstants.valueTypes.BOOL or valueType == d2dConstants.valueTypes.BOOL_ARRAY:
            self.__shared.default_value = bool()

        elif valueType == d2dConstants.valueTypes.INT or valueType == d2dConstants.valueTypes.INT_ARRAY:
            self.__shared.default_value = int()

        elif valueType == d2dConstants.valueTypes.STRING or valueType == d2dConstants.valueTypes.STRING_ARRAY:
            self.__shared.default_value = str()

        elif valueType == d2dConstants.valueTypes.FLOAT or valueType == d2dConstants.valueTypes.FLOAT_ARRAY:
            self.__shared.default_value = float()

        else:
            self.__shared.default_value = None


        if valueType.endswith(d2dConstants.valueTypes.ARRAY):
            self.__shared.value = []

        else:
            self.__shared.value = self.__shared.default_value


        if self.__shared.default_value != None:
            self.__shared.udp_socket = udpRandomPortListener()
            self.__shared.mcast_socket = mcast(d2dConstants.INFO_MULTICAST_GROUP)
            self.__thread = threading.Thread(target=d2dInfoWriter.__listetenUpdateReq, daemon=True, args=[self.__shared])
            self.__thread.start()


    def __del__(self):
        self.__shared.run = False

        if self.__shared.udp_socket:
            self.__shared.udp_socket.close()

        if self.__shared.mcast_socket:
            self.__shared.mcast_socket.close()

        if self.__thread:
            self.__thread.join()


    @property
    def name(self):
        return self.__shared.name


    @property
    def mac(self):
        return self.__shared.mac


    @property
    def service(self):
        return self.__shared.service


    @property
    def category(self):
        return self.__shared.category


    @property
    def value(self):
        return self.__shared.value


    @property
    def valueType(self):
        return self.__shared.valueType


    @property
    def requestPort(self):
        if self.__shared.udp_socket:
            return self.__shared.udp_socket.port

        else:
            return None

    @property
    def updatePort(self):
        if self.__shared.mcast_socket:
            return self.__shared.mcast_socket.port

        else:
            return None


    @property
    def value(self):
        return self.__shared.value


    @value.setter
    def value(self, value):
        if type(self.__shared.value) == type(list()):
            ok = True
            for it in value:
                if type(it) != type(self.__shared.default_value):
                    raise Exception("Invalid asigned list type")

        elif type(self.__shared.value) != type(value):
            raise Exception("Invalid asigned type")


        if self.__shared.value != value:
            self.__shared.value = value
            self.__shared.mcast_socket.send(typeTools.convertToASCII(self.__shared.value, self.__shared.valueType))


    def __listetenUpdateReq(shared):

        while shared.run:
            data, ip, port = shared.udp_socket.read()
            if data == d2dConstants.INFO_REQUEST:
                shared.udp_socket.send(ip, port, typeTools.convertToASCII(shared.value, shared.valueType))


class d2dInfoReader():

    def __init__(self,mac, service, category, name, valueType, ip, req_port, update_port):
        self.__shared = container()
        self.__shared.run = True
        self.__shared.name = name
        self.__shared.mac = mac
        self.__shared.service = service
        self.__shared.category = category
        self.__shared.valueType = valueType
        self.__shared.value = None
        self.__shared.epoch = None
        self.__shared.online = True
        self.__shared.on_update_callback_list = []
        self.__shared.callback_mutex = threading.RLock()
        self.__shared.udp_socket = udpClient(ip, req_port)
        self.__shared.mcast_socket = mcast(d2dConstants.INFO_MULTICAST_GROUP, update_port, ip)
        self.__thread = threading.Thread(target=d2dInfoReader.__read_updates_thread, daemon=True, args=[self.__shared])
        self.__thread.start()


    def __del__(self):
        self.__shared.run = False
        self.__shared.mcast_socket.close()
        self.__shared.udp_socket.close()
        self.__thread.join()


    def __read_updates_thread(shared):
        while shared.run:
            data, ip, port = shared.mcast_socket.read()
            if data != None:
                shared.value = typeTools.convevertFromASCII(data.decode(), shared.valueType)
                shared.epoch = int(time.time())
                with shared.callback_mutex:
                    for callback in shared.on_update_callback_list:
                        callback()

    @property
    def name(self):
        return self.__shared.name


    @property
    def mac(self):
        return self.__shared.mac


    @property
    def service(self):
        return self.__shared.service


    @property
    def category(self):
        return self.__shared.category


    @property
    def value(self):
        return self.__shared.value


    @property
    def valueType(self):
        return self.__shared.valueType


    @property
    def epoch(self):
        return self.__shared.epoch


    @property
    def online(self):
        return self.__shared.online


    def addOnUpdateCallback(self, callback):
        with self.__shared.callback_mutex:
            if callback not in self.__shared.on_update_callback_list:
                self.__shared.on_update_callback_list.append(callback)


    def removeOnUpdateCallback(self, callback):
        with self.__shared.callback_mutex:
            if callback in self.__shared.on_update_callback_list:
                self.__shared.on_update_callback_list.remove(callback)


    @property
    def value(self):
        if self.__shared.value == None:
            self.__shared.udp_socket.send(d2dConstants.INFO_REQUEST)
            data = self.__shared.udp_socket.read(timeout=5)
            if data != None:
                self.__shared.value = typeTools.convevertFromASCII(data.decode(), self.__shared.valueType)
                self.__shared.epoch = int(time.time())

        return self.__shared.value


class d2d():

    def __init__(self, service=None, master=True):
        self.__mac = hex(uuid.getnode()).replace("0x", "")

        if service:
            self.__service = service
        else:
            process = psutil.Process(os.getpid())
            process_name = process.name()
            self.__service = process_name.split(".")[0]

        self.__threads = []
        self.__command_sockets = []
        self.__service_container = {}

        self.__callback_mutex = threading.RLock()
        self.__registered_mutex = threading.RLock()

        self.__command_update_callback = None
        self.__command_remove_callback = None
        self.__command_add_callback = None

        self.__info_added_callback = None
        self.__info_remove_callback = None

        self.__service_used_paths = {}
        self.__info_writer_objects = {}

        self.__shared = container()
        self.__commands = {}
        self.__shared.info_readers = {}

        self.__shared_table = SharedTableBroker.SharedTableBroker(d2dConstants.BROKER_SERVICE_NAME, master)
        self.__shared_table.onRemoveTableEntry = self.__entryRemoved
        self.__shared_table.onNewTableEntry = self.__entryUpdated
        self.__shared_table.onUpdateTableEntry = self.__entryUpdated


    def __del__(self):

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
    def onCommandAdd(self):
        with self.__callback_mutex:
            return self.__command_add_callback


    @onCommandAdd.setter
    def onCommandAdd(self, callback):
        with self.__callback_mutex:
            self.__command_add_callback = callback


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
    def onInfoAdd(self):
        with self.__callback_mutex:
            return self.__info_added_callback


    @onInfoAdd.setter
    def onInfoAdd(self, callback):
        with self.__callback_mutex:
            self.__info_added_callback = callback


    @property
    def onInfoRemove(self):
        with self.__callback_mutex:
            return self.__info_remove_callback


    @onInfoRemove.setter
    def onInfoRemove(self, callback):
        with self.__callback_mutex:
            self.__info_remove_callback = callback


    def __entryRemoved(self, client_id, entry_key):

        path_info = d2d.__extractPathInfo(entry_key)
        if path_info.mode == d2dConstants.COMMAND_LEVEL:

            with self.__registered_mutex:
                if entry_key in self.__commands:
                    shared_ptr = self.__commands[entry_key]()
                    if shared_ptr:
                        shared_ptr.configure(False)


            # Notify
            with self.__callback_mutex:
                if self.__info_remove_callback:
                    self.__info_remove_callback(path_info.mac, path_info.service, path_info.category, path_info.name)

        elif path_info.mode == d2dConstants.INFO_LEVEL:

            # Notify
            with self.__callback_mutex:
                if self.__info_remove_callback:
                    self.__info_remove_callback(path_info.mac, path_info.service, path_info.category, path_info.name)


    def __entryUpdated(self, client_id, entry_key, data):

        path_info = d2d.__extractPathInfo(entry_key)
        if path_info.mode == d2dConstants.COMMAND_LEVEL:

            command_info = d2d.__extractCommandInfo(data[0])
            command_updated = False

            with self.__registered_mutex:
                if entry_key in self.__commands:
                    shared_ptr = self.__commands[entry_key]()
                    if shared_ptr:
                        shared_ptr.configure(command_info.enable, command_info.params, command_info.response, command_info.protocol, command_info.ip, command_info.port, command_info.timeout)
                        command_updated = True


            # Notify
            with self.__callback_mutex:
                if command_updated:
                    if self.__command_update_callback:
                        self.__command_update_callback(path_info.mac, path_info.service, path_info.category, path_info.name)

                else:
                    if self.__command_add_callback:
                        self.__command_add_callback(path_info.mac, path_info.service, path_info.category, path_info.name)


        elif path_info.mode == d2dConstants.INFO_LEVEL:

            # Notify
            with self.__callback_mutex:
                if self.__info_added_callback:
                    self.__info_added_callback(path_info.mac, path_info.service, path_info.category, path_info.name)


    def __createPath(mac:str, service:str, category:str, mode:str, name:str) -> str:

        if mode not in [d2dConstants.COMMAND_LEVEL, d2dConstants.INFO_LEVEL]:
            return None

        path = d2dConstants.PREFIX + "/"
        path += mac + "/"
        path += service + "/"
        path += mode + "/"
        path += category + "/"
        path += name

        return path


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


    def __checkInOutDefinedField(field) -> bool:

        if d2dConstants.field.TYPE not in field:
            return False

        elif not isinstance(field[d2dConstants.field.TYPE], str):
            return False

        elif d2dConstants.field.OPTIONAL in field and not isinstance(field[d2dConstants.field.OPTIONAL], bool):
            return False

        return True


    def __checkInOutField(data_dict, prototipe_dict) -> bool:

        # Chect type and non-exists
        for field in data_dict:
            if field not in prototipe_dict:
                return False
            if not typeTools.checkFieldType(data_dict[field], prototipe_dict[field][d2dConstants.field.TYPE]):
                return False

        # Check optional
        for field in prototipe_dict:
            field_prototipe = prototipe_dict[field]
            mandatory = d2dConstants.field.OPTIONAL not in field_prototipe or not field_prototipe[d2dConstants.field.OPTIONAL]
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


    def __extractCommandInfo(data):

        try:
            command_info = json.loads(data)
            rc = container()
            rc.protocol = command_info[d2dConstants.commandField.PROTOCOL]
            rc.ip = command_info[d2dConstants.commandField.IP]
            rc.port = command_info[d2dConstants.commandField.PORT]
            rc.params = command_info[d2dConstants.commandField.INPUT]
            rc.response = command_info[d2dConstants.commandField.OUTPUT]
            rc.enable = True if d2dConstants.commandField.ENABLE not in command_info else command_info[d2dConstants.commandField.ENABLE]
            rc.timeout = 5 if d2dConstants.commandField.TIMEOUT not in command_info else command_info[d2dConstants.commandField.TIMEOUT]
            return rc

        except:
            return None


    def __extractInfoDescription(data):

        try:
            command_info = json.loads(data)
            rc = container()
            rc.protocol = command_info[d2dConstants.infoField.PROTOCOL]
            rc.ip = command_info[d2dConstants.infoField.IP]
            rc.req_port = command_info[d2dConstants.infoField.REQUEST_PORT]
            rc.update_port = command_info[d2dConstants.infoField.UPDATE_PORT]
            rc.valueType = command_info[d2dConstants.infoField.TYPE]

            return rc

        except:
            return None


    def __extractPathInfo(path):

        path_split = path.split("/")
        if len(path_split) < 6:
            return None

        rc = container()

        rc.prefix = path_split[0]
        if rc.prefix != d2dConstants.PREFIX:
            return

        rc.mac = path_split[1]
        rc.service = path_split[2]
        rc.mode = path_split[3]
        rc.category = path_split[4]
        rc.name = path_split[5]

        return rc


    def __getOwnIP(self, dst='127.0.0.1'):

        if not dst:
            return ""

        elif os.name != 'nt':
            ipr = IPRoute().route('get', dst=dst)
            if len(ipr) > 0:
                return ipr[0].get_attr('RTA_PREFSRC')
            else:
                return "127.0.0.1"

        else:
            return ""


    def addServiceCommand(self, cmdCallback, name:str, input_params:dict, output_params:dict, category:str="", enable=True, timeout=5, protocol=d2dConstants.commandProtocol.JSON_UDP)-> bool:

        # Checks
        if not cmdCallback:
            return False

        for field in input_params:
            if not d2d.__checkInOutDefinedField(input_params[field]):
                return False

        for field in output_params:
            if not d2d.__checkInOutDefinedField(output_params[field]):
                return False


        # Set defaults
        if category == "":
            category = d2dConstants.category.GENERIC


        # Check if already registered
        if name in self.__service_container:
            return False


        # Create listen thread
        self.__service_container[name] = container()
        self.__service_container[name].run = True

        if protocol == d2dConstants.commandProtocol.JSON_UDP:
            listen_socket = udpRandomPortListener()
            self.__command_sockets.append(listen_socket)
            thread = threading.Thread(target=d2d.__udpListenerThread, daemon=True, args=[listen_socket, self.__service_container[name], cmdCallback, input_params, output_params])
            thread.start()
            self.__threads.append(thread)

        elif protocol == d2dConstants.commandProtocol.JSON_TCP:
            listen_socket = tcpListener()
            self.__command_sockets.append(listen_socket)
            thread = threading.Thread(target=d2d.__tcpListenerThread, daemon=True, args=[listen_socket, self.__service_container[name], cmdCallback, input_params, output_params])
            thread.start()
            self.__threads.append(thread)

        else:
            return False


        # Register command
        command_path = d2d.__createPath(self.__mac, self.__service, category, d2dConstants.COMMAND_LEVEL, name)
        if not command_path:
            return False

        self.__service_used_paths[name] = command_path

        self.__service_container[name].map = {}
        self.__service_container[name].map[d2dConstants.commandField.PROTOCOL] = protocol
        self.__service_container[name].map[d2dConstants.commandField.IP] = self.__getOwnIP(self.__shared_table.masterIP())
        self.__service_container[name].map[d2dConstants.commandField.PORT] = listen_socket.port
        self.__service_container[name].map[d2dConstants.commandField.INPUT] = input_params
        self.__service_container[name].map[d2dConstants.commandField.OUTPUT] = output_params
        self.__service_container[name].map[d2dConstants.commandField.ENABLE] = enable
        self.__service_container[name].map[d2dConstants.commandField.TIMEOUT] = timeout

        return self.__shared_table.updateTableEntry(self.__service_used_paths[name], [json.dumps(self.__service_container[name].map)])


    def enableCommand(self, name, enable):
        if name not in self.__service_container:
            return False

        self.__service_container[name].map[d2dConstants.commandField.ENABLE] = enable
        return self.__shared_table.updateTableEntry(self.__service_used_paths[name], [json.dumps(self.__service_container[name].map)])


    def getAvailableComands(self, mac:str="", service:str="", category:str="", command:str="", wait:int=0) -> list:

        search_command_path = self.__createRegexPath(mac, service, category, d2dConstants.COMMAND_LEVEL, command)

        commands = []
        start = time.time()

        # Get commands from table
        while True:
            with self.__registered_mutex:
                d2d_map = self.__shared_table.geMapData()
                for client in d2d_map:
                    for d2d_path in d2d_map[client]:
                        if re.search(search_command_path, d2d_path):

                            # Command already setup
                            if d2d_path in self.__commands:
                                command_object = self.__commands[d2d_path]()

                            else:
                                command_object = None


                            if not command_object:
                                command_info = d2d.__extractCommandInfo(d2d_map[client][d2d_path][0])
                                path_info = d2d.__extractPathInfo(d2d_path)

                                command_object = d2dCommand(path_info.mac, path_info.service, path_info.category, path_info.name,
                                                            command_info.protocol, command_info.ip, command_info.port, command_info.params,
                                                            command_info.response, command_info.enable, command_info.timeout)


                                # Save weak reference
                                self.__commands[d2d_path] = weakref.ref(command_object)

                            # Append to list
                            commands.append(command_object)


            # Check return value
            end = time.time()
            if len(commands) > 0 or wait < 0 or (wait > 0 and (end - start) > wait):
                break

            else:
                time.sleep(0.1)

        return commands


    def addInfoWriter(self, name:str, category:str, valueType:str, protocol:str=d2dConstants.infoProtocol.ASCII) -> d2dInfoWriter:

        # Set defaults
        if category == "":
            category = d2dConstants.category.GENERIC

        info_path = d2d.__createPath(self.__mac, self.__service, category, d2dConstants.INFO_LEVEL, name)


        with self.__registered_mutex:
            if info_path not in self.__info_writer_objects:
                info_writer = d2dInfoWriter(self.__mac, self.__service, category, name, valueType)
                self.__info_writer_objects[info_path] = weakref.ref(info_writer)

            else:
                info_writer = self.__info_writer_objects[info_path]()

                if not info_writer:
                    info_writer = d2dInfoWriter(self.__mac, self.__service, category, name, valueType)
                    self.__info_writer_objects[info_path] = weakref.ref(info_writer)

        info_description = {}
        info_description[d2dConstants.infoField.PROTOCOL] = protocol
        info_description[d2dConstants.infoField.IP] = self.__getOwnIP(self.__shared_table.masterIP())
        info_description[d2dConstants.infoField.REQUEST_PORT] = info_writer.requestPort
        info_description[d2dConstants.infoField.UPDATE_PORT] = info_writer.updatePort
        info_description[d2dConstants.infoField.TYPE] = valueType


        if self.__shared_table.updateTableEntry(info_path, [json.dumps(info_description)]):
            return info_writer

        else:
            return None


    def getAvailableInfoReaders(self, mac:str="", service:str="", category:str="", name:str="", wait:int=0) -> list:


        search_info_path = self.__createRegexPath(mac, service, category, d2dConstants.INFO_LEVEL, name)

        info_reader_objs = []
        start = time.time()

        # Get commands from table
        while True:
            with self.__registered_mutex:
                d2d_map = self.__shared_table.geMapData()
                for client in d2d_map:
                    for d2d_path in d2d_map[client]:
                        if re.search(search_info_path, d2d_path):

                            # Command already setup
                            if d2d_path in self.__shared.info_readers:
                                info_reader_object = self.__shared.info_readers[d2d_path]()

                            else:
                                info_reader_object = None


                            if not info_reader_object:
                                info_description = d2d.__extractInfoDescription(d2d_map[client][d2d_path][0])
                                path_info = d2d.__extractPathInfo(d2d_path)

                                info_reader_object = d2dInfoReader(path_info.mac, path_info.service, path_info.category, path_info.name,
                                    info_description.valueType, info_description.ip, info_description.req_port, info_description.update_port)


                                # Save weak reference
                                self.__shared.info_readers[d2d_path] = weakref.ref(info_reader_object)


                            # Append to list
                            info_reader_objs.append(info_reader_object)


            # Check return value
            end = time.time()
            if len(info_reader_objs) > 0 or wait < 0 or (wait > 0 and (end - start) > wait):
                break

            else:
                time.sleep(0.1)

        return info_reader_objs


    def waitThreads(self):
        for thread in self.__threads:
            thread.join()