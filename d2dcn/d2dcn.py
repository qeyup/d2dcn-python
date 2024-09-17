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


version = "0.5.5"


class constants():
    BROKER_SERVICE_NAME = "D2D_TABLE"
    BROKER_PORT = 18832
    CLIENT_DISCOVER_WAIT = 5
    MTU = 500
    END_OF_TX = b'\xFF'
    MAX_LISTEN_TCP_SOKETS = -1
    MQTT_PREFIX = "d2dcn"
    PREFIX = "d2dcn"
    COMMAND_LEVEL = "command"
    INFO_LEVEL = "info"
    STATE = "state"
    INFO_MULTICAST_GROUP = "232.10.10.10"
    INFO_REQUEST = b"req"
    TX_TIMEOUT = 0.1
    TX_TIMEOUT_MAX_COUNT = 50
    RX_TIMEOUT = 0.1

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
        INCOMPLETE_RESPONSE = "Incomplete response"
        INVALID_RESPONSE = "Invalid response"

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

        self.__sock.settimeout(constants.RX_TIMEOUT)

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
        self.__sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.__sock.bind(('', 0))
        self.__sock.settimeout(constants.RX_TIMEOUT)


    def __del__(self):
        self.close()


    def read(self, timeout=-1):

        current_epoch_time = int(time.time())
        while self.__open:
            try:
                data, (ip, port) = self.__sock.recvfrom(constants.MTU)
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

        bytes_send = 0
        timeout_retry = 0
        while len(msg) > bytes_send:
            try:
                bytes_send += self.__sock.sendto(msg[bytes_send:], (ip, port))
                timeout_retry = 0

            except socket.timeout:
                if timeout_retry >= constants.TX_TIMEOUT_MAX_COUNT:
                    return False

                else:
                    timeout_retry += 1
                    time.sleep(constants.TX_TIMEOUT)

            except:
                return False

        return True


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
        self.__sock.settimeout(constants.RX_TIMEOUT)


    def __del__(self):
        self.close()


    def read(self, timeout=-1):

        current_epoch_time = int(time.time())
        while self.__open:
            try:
                data = self.__sock.recv(constants.MTU)
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

        bytes_send = 0
        timeout_retry = 0
        while len(msg) > bytes_send:
            try:
                bytes_send += self.__sock.sendto(msg[bytes_send:], (self.__remote_ip, self.__remote_port))
                timeout_retry = 0

            except socket.timeout:
                if timeout_retry >= constants.TX_TIMEOUT_MAX_COUNT:
                    return False

                else:
                    timeout_retry += 1
                    time.sleep(constants.TX_TIMEOUT)

            except:
                return False

        return True


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
            self.__sock.settimeout(constants.RX_TIMEOUT)


        def read(self, timeout=-1):

            current_epoch_time = int(time.time())
            while self.__open:
                try:
                    data = self.__sock.recv(constants.MTU)

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

            bytes_send = 0
            timeout_retry = 0
            while len(msg) > bytes_send:
                try:
                    bytes_send += self.__sock.send(msg[bytes_send:])
                    timeout_retry = 0

                except socket.timeout:
                    if timeout_retry >= constants.TX_TIMEOUT_MAX_COUNT:
                        return False

                    else:
                        timeout_retry += 1
                        time.sleep(constants.TX_TIMEOUT)

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


    def __init__(self, port=0, max_connections=constants.MAX_LISTEN_TCP_SOKETS):
        super().__init__()
        self.__open = True
        self.__sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.__sock.bind(('', port))
        self.__sock.settimeout(constants.RX_TIMEOUT)
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
        self.__sock.settimeout(constants.RX_TIMEOUT)


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
                    data = self.__sock.recv(constants.MTU)
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

            bytes_send = 0
            timeout_retry = 0
            while len(msg) > bytes_send:
                try:
                    bytes_send += self.__sock.send(msg[bytes_send:])
                    timeout_retry = 0

                except socket.timeout:
                    if timeout_retry >= constants.TX_TIMEOUT_MAX_COUNT:
                        return False

                    else:
                        timeout_retry += 1
                        time.sleep(constants.TX_TIMEOUT)

                except:
                    return False

        return True


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
            return constants.valueTypes.FLOAT

        elif isinstance(data, bool):
            return constants.valueTypes.BOOL

        elif isinstance(data, int):
            return constants.valueTypes.INT

        elif isinstance(data, str):
            return constants.valueTypes.STRING

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
                return constants.valueTypes.ARRAY
            
            elif detected_type == constants.valueTypes.FLOAT:
                return constants.valueTypes.FLOAT_ARRAY

            elif detected_type == constants.valueTypes.BOOL:
                return constants.valueTypes.BOOL_ARRAY

            elif detected_type == constants.valueTypes.INT:
                return constants.valueTypes.INT_ARRAY

            elif detected_type == constants.valueTypes.STRING:
                return constants.valueTypes.STRING_ARRAY

            else:
                return ""

        else:
            return ""


    def checkFieldType(field, field_type):
        detected_type = typeTools.getType(field)

        if detected_type == field_type:
            return True

        elif detected_type == constants.valueTypes.ARRAY and constants.valueTypes.ARRAY in field_type:
            return True
        
        else:
            return False


    def convevertFromASCII(data, data_type):

        try:
            if data_type == constants.valueTypes.BOOL:
                return bool(int(data))

            elif data_type == constants.valueTypes.INT:
                return int(data)

            elif data_type == constants.valueTypes.STRING:
                return str(data)

            elif data_type == constants.valueTypes.FLOAT:
                return float(data)

            elif data_type == constants.valueTypes.ARRAY or constants.valueTypes.ARRAY in data_type:
                
                rl = []
                aux_list = json.loads(data)
                for item in aux_list:
                    if data_type == constants.valueTypes.BOOL_ARRAY:
                        rl.append(bool(item))

                    elif data_type == constants.valueTypes.INT_ARRAY:
                        rl.append(int(item))

                    elif data_type == constants.valueTypes.STRING_ARRAY:
                        rl.append(str(item))

                    elif data_type == constants.valueTypes.FLOAT_ARRAY:
                        rl.append(float(item))

                return rl

            else:
                return None

        except:
            return None


    def convertToASCII(data, data_type):
        try:
            if data_type == constants.valueTypes.BOOL:
                return str(1 if data else 0)

            elif data_type == constants.valueTypes.INT:
                return str(data)

            elif data_type == constants.valueTypes.STRING:
                return str(data)

            elif data_type == constants.valueTypes.FLOAT:
                return str(data)

            elif data_type == constants.valueTypes.ARRAY or constants.valueTypes.ARRAY in data_type:
                if not isinstance(data, list):
                    return None

                return json.dumps(data)

            else:
                return None

        except:
            return None


class commandArgsDef(dict):

    def __init__(self, data={}):
        super().__init__()

        if len(data) > 0:
            for it in data:
                self[it] = data[it]
            self.__editable = False

        else:
            self.__editable = True


    def add(self, arg_name:str, arg_type:str, optional:bool=False):
        if self.__editable:
            self[arg_name] = {}
            self[arg_name][constants.field.TYPE] = arg_type

            if optional:
                self[arg_name][constants.field.OPTIONAL] = optional
            return True

        else:
            return False

    @property
    def names(self):
        return self.keys()


    def getArgType(self, name):
        return self[name][constants.field.TYPE] if name in self else None


    def isArgOptional(self, name):
        return self[name][constants.field.OPTIONAL] if name in self and constants.field.OPTIONAL in self[name] else False


class commandResponse(dict):

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
                self.__error = constants.commandErrorMsg.EXCEPTION_ERROR
            self.__success = False

    @property
    def error(self):
        return self.__error


    @property
    def success(self):
        return self.__success


class commandInterface():

    def __init__(self, mac:str, service:str, category:str, name:str, protocol:str, ip:str, 
        port:int, params:commandArgsDef, response:commandArgsDef, enable:bool, timeout:int):
        self.__name = name
        self.__mac = mac
        self.__ip = ip
        self.__service = service
        self.__category = category
        self.configure(enable, params, response, protocol, ip, port, timeout)


    def configure(self, enable, params=None, response=None, protocol=None, ip=None, port=None, timeout=None):

        if params:
            self.__params = params
        else:
            self.__params = commandArgsDef()

        if response:
            self.__response = response
        else:
            self.__response = commandArgsDef()

        self.__protocol = protocol
        self.__enable = enable
        self.__timeout = timeout

        if enable:
            if protocol == constants.commandProtocol.JSON_UDP:
                self.__socket = udpClient(ip, port)

            elif protocol == constants.commandProtocol.JSON_TCP:
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
    def ip(self):
        return self.__ip


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
        return self.__enable


    @property
    def protocol(self):
        return self.__protocol


    def call(self, args:dict, timeout=None) -> dict:

        if not timeout:
            timeout = self.__timeout

        if self.__socket == None:
            return commandResponse(constants.commandErrorMsg.NOT_ENABLE_ERROR)

        try:
            response = constants.commandErrorMsg.CONNECTION_ERROR
            self.__socket.send(json.dumps(args, indent=1))
            socket_response = self.__socket.read(timeout)
            if socket_response:
                response = socket_response.decode()
                while response.startswith("{") and not response.endswith("}"):
                    read_response = self.__socket.read(timeout)
                    if read_response:
                        response += read_response.decode()
                    else:
                        if response.startswith("{"):
                            response = constants.commandErrorMsg.INCOMPLETE_RESPONSE
                        break
            else:
                response = constants.commandErrorMsg.TIMEOUT_ERROR

        except:
            response = constants.commandErrorMsg.INVALID_RESPONSE


        return commandResponse(response) 


class infoWriter():

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
        self.__thread = None


        if valueType == constants.valueTypes.BOOL or valueType == constants.valueTypes.BOOL_ARRAY:
            self.__shared.default_value = bool()

        elif valueType == constants.valueTypes.INT or valueType == constants.valueTypes.INT_ARRAY:
            self.__shared.default_value = int()

        elif valueType == constants.valueTypes.STRING or valueType == constants.valueTypes.STRING_ARRAY:
            self.__shared.default_value = str()

        elif valueType == constants.valueTypes.FLOAT or valueType == constants.valueTypes.FLOAT_ARRAY:
            self.__shared.default_value = float()

        else:
            self.__shared.default_value = None


        if valueType.endswith(constants.valueTypes.ARRAY):
            self.__shared.value = []

        else:
            self.__shared.value = self.__shared.default_value


        if self.__shared.default_value != None:
            self.__shared.udp_socket = udpRandomPortListener()
            self.__shared.mcast_socket = mcast(constants.INFO_MULTICAST_GROUP)
            self.__thread = threading.Thread(target=infoWriter.__listetenUpdateReq, daemon=True, args=[self.__shared])
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
            if data == constants.INFO_REQUEST:
                shared.udp_socket.send(ip, port, typeTools.convertToASCII(shared.value, shared.valueType))

        shared.udp_socket.close()


class infoReader():

    def __init__(self,mac, service, category, name, valueType, ip, req_port, update_port):
        self.__shared = container()
        self.__shared.name = name
        self.__shared.mac = mac
        self.__shared.ip = ip
        self.__shared.service = service
        self.__shared.category = category
        self.__shared.valueType = valueType
        self.__shared.epoch = None
        self.__shared.on_update_callback_list = []
        self.__shared.callback_mutex = threading.RLock()
        self.__shared.value_mutex = threading.RLock()

        self.__shared.value = None
        self.__thread = None
        self.__shared.udp_socket = None
        self.__shared.mcast_socket = None
        self.__shared.run = False
        self.configure(ip, req_port, update_port)


    def configure(self, ip, req_port, update_port):

        self.__shared.run = False

        if self.__shared.udp_socket != None:
            self.__shared.udp_socket.close()

        if self.__shared.mcast_socket != None:
            self.__shared.mcast_socket.close()

        if self.__thread != None:
            self.__thread.join()

        # Lauch thread
        if ip != None:
            self.__shared.run = True
            self.__shared.udp_socket = udpClient(ip, req_port)
            self.__shared.mcast_socket = mcast(constants.INFO_MULTICAST_GROUP, update_port, ip)
            self.__thread = threading.Thread(target=infoReader.__read_updates_thread, daemon=True, args=[self.__shared])
            self.__thread.start()

        else:
            self.__shared.udp_socket = None
            self.__shared.mcast_socket = None
            self.__thread = None


            if self.__shared.value != None:
                self.__shared.value = None

                infoReader.__callbackExec(self.__shared)


    def __del__(self):
        self.__shared.run = False

        if self.__shared.udp_socket != None:
            self.__shared.udp_socket.close()

        if self.__shared.mcast_socket != None:
            self.__shared.mcast_socket.close()

        if self.__thread != None:
            self.__thread.join()


    def __callbackExec(shared):
        with shared.callback_mutex:

            remove_list = []
            for weak_callback in shared.on_update_callback_list:
                shared_calback = weak_callback()

                if shared_calback:
                    shared_calback()

                else:
                    remove_list.append(weak_callback)

            for weak_callback in remove_list:
                shared.on_update_callback_list.remove(weak_callback)


    def __read_updates_thread(shared):

        shared.udp_socket.send(constants.INFO_REQUEST)
        data = shared.udp_socket.read(timeout=5)
        if data != None:
            with shared.value_mutex:
                shared.value = typeTools.convevertFromASCII(data.decode(), shared.valueType)
                shared.epoch = int(time.time())

            infoReader.__callbackExec(shared)


        while shared.run:
            data, ip, port = shared.mcast_socket.read()
            if data != None:
                with shared.value_mutex:
                    shared.value = typeTools.convevertFromASCII(data.decode(), shared.valueType)
                    shared.epoch = int(time.time())

                infoReader.__callbackExec(shared)

        shared.mcast_socket.close()
        shared.udp_socket.close()


    @property
    def name(self):
        return self.__shared.name


    @property
    def mac(self):
        return self.__shared.mac


    @property
    def ip(self):
        return self.__shared.ip


    @property
    def service(self):
        return self.__shared.service


    @property
    def category(self):
        return self.__shared.category


    @property
    def value(self):
        with self.__shared.value_mutex:
            return self.__shared.value


    @property
    def valueType(self):
        return self.__shared.valueType


    @property
    def epoch(self):
        with self.__shared.value_mutex:
            return self.__shared.epoch


    @property
    def online(self):
        with self.__shared.value_mutex:
            return self.value != None


    def addOnUpdateCallback(self, callback):
        weak_ptr = weakref.ref(callback)
        with self.__shared.callback_mutex:
            if weak_ptr not in self.__shared.on_update_callback_list:
                self.__shared.on_update_callback_list.append(weak_ptr)


class d2d():

    def __init__(self, service=None, master=True, start=True):

        self.__shared = container()

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

        self.__shared.__callback_mutex = threading.RLock()
        self.__shared.__registered_mutex = threading.RLock()

        self.__shared.__command_update_callback = None
        self.__shared.__command_remove_callback = None
        self.__shared.__command_add_callback = None

        self.__shared.__info_added_callback = None
        self.__shared.__info_remove_callback = None
        self.__shared.__info_updated_callback = None

        self.__service_used_paths = {}
        self.__info_writer_objects = {}

        self.__shared.__commands = {}
        self.__shared.info_readers = {}

        self.__shared_table = SharedTableBroker.SharedTableBroker(constants.BROKER_SERVICE_NAME, master, False)
        self.__shared_table.onRemoveTableEntry = lambda client_id, entry_key, shared=self.__shared : d2d.__entryRemoved(client_id, entry_key, shared)
        self.__shared_table.onNewTableEntry = lambda client_id, entry_key, data, shared=self.__shared : d2d.__entryUpdated(client_id, entry_key, data, shared)
        self.__shared_table.onUpdateTableEntry = lambda client_id, entry_key, data, shared=self.__shared : d2d.__entryUpdated(client_id, entry_key, data, shared)


        if start:
            self.start()


    def start(self):
        self.__shared_table.start()


    def stop(self):
        self.__shared_table.stop()


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
        with self.__shared.__callback_mutex:
            return self.__shared.__command_add_callback


    @onCommandAdd.setter
    def onCommandAdd(self, callback):
        with self.__shared.__callback_mutex:
            self.__shared.__command_add_callback = callback


    @property
    def onCommandUpdate(self):
        with self.__shared.__callback_mutex:
            return self.__shared.__command_update_callback


    @onCommandUpdate.setter
    def onCommandUpdate(self, callback):
        with self.__shared.__callback_mutex:
            self.__shared.__command_update_callback = callback


    @property
    def onCommandRemove(self):
        with self.__shared.__callback_mutex:
            return self.__shared.__command_remove_callback


    @onCommandRemove.setter
    def onCommandRemove(self, callback):
        with self.__shared.__callback_mutex:
            self.__shared.__command_remove_callback = callback


    @property
    def onInfoAdd(self):
        with self.__shared.__callback_mutex:
            return self.__shared.__info_added_callback


    @onInfoAdd.setter
    def onInfoAdd(self, callback):
        with self.__shared.__callback_mutex:
            self.__shared.__info_added_callback = callback


    @property
    def onInfoUpdate(self):
        with self.__shared.__callback_mutex:
            return self.__shared.__info_updated_callback


    @onInfoUpdate.setter
    def onInfoUpdate(self, callback):
        with self.__shared.__callback_mutex:
            self.__shared.__info_updated_callback = callback


    @property
    def onInfoRemove(self):
        with self.__shared.__callback_mutex:
            return self.__shared.__info_remove_callback


    @onInfoRemove.setter
    def onInfoRemove(self, callback):
        with self.__shared.__callback_mutex:
            self.__shared.__info_remove_callback = callback


    def __entryRemoved(client_id, entry_key, shared):

        path_info = d2d.__extractPathInfo(entry_key)
        if path_info.mode == constants.COMMAND_LEVEL:

            with shared.__registered_mutex:
                if entry_key in shared.__commands:
                    shared_ptr = shared.__commands[entry_key]()
                    if shared_ptr:
                        shared_ptr.configure(False)


            # Notify
            with shared.__callback_mutex:
                if shared.__command_remove_callback:
                    shared.__command_remove_callback(path_info.mac, path_info.service, path_info.category, path_info.name)

        elif path_info.mode == constants.INFO_LEVEL:

            with shared.__registered_mutex:
                if entry_key in shared.info_readers:
                    shared_ptr = shared.info_readers[entry_key]()
                    if shared_ptr:
                        shared_ptr.configure(None, None, None)


            # Notify
            with shared.__callback_mutex:
                if shared.__info_remove_callback:
                    shared.__info_remove_callback(path_info.mac, path_info.service, path_info.category, path_info.name)


    def __entryUpdated(client_id, entry_key, data, shared):

        path_info = d2d.__extractPathInfo(entry_key)
        updated = False
        if path_info.mode == constants.COMMAND_LEVEL:

            command_info = d2d.__extractCommandInfo(data[0])

            with shared.__registered_mutex:
                if entry_key in shared.__commands:
                    shared_ptr = shared.__commands[entry_key]()
                    if shared_ptr:
                        shared_ptr.configure(command_info.enable, command_info.params, command_info.response, command_info.protocol, command_info.ip, command_info.port, command_info.timeout)
                        updated = True


            # Notify
            with shared.__callback_mutex:
                if updated:
                    if shared.__command_update_callback:
                        shared.__command_update_callback(path_info.mac, path_info.service, path_info.category, path_info.name)

                else:
                    if shared.__command_add_callback:
                        shared.__command_add_callback(path_info.mac, path_info.service, path_info.category, path_info.name)


        elif path_info.mode == constants.INFO_LEVEL:

            info_description = d2d.__extractInfoDescription(data[0])

            with shared.__registered_mutex:
                if entry_key in shared.info_readers:
                    shared_ptr = shared.info_readers[entry_key]()
                    if shared_ptr:
                        shared_ptr.configure(info_description.ip, info_description.req_port, info_description.update_port)
                        updated = True

            # Notify
            with shared.__callback_mutex:
                if updated:
                    if shared.__info_updated_callback:
                        shared.__info_updated_callback(path_info.mac, path_info.service, path_info.category, path_info.name)

                else:
                    if shared.__info_added_callback:
                        shared.__info_added_callback(path_info.mac, path_info.service, path_info.category, path_info.name)


    def createInfoWriterUID(mac, service, category, name) -> str:
        return d2d.__createUID(mac, service, category, constants.INFO_LEVEL, name)


    def createCommandUID(mac, service, category, name) -> str:
        return d2d.__createUID(mac, service, category, constants.COMMAND_LEVEL, name)


    def __createUID(mac, service, category, mode, name) -> str:

        if mode not in [constants.COMMAND_LEVEL, constants.INFO_LEVEL]:
            return ""

        d2d_path = constants.MQTT_PREFIX + "/"

        if mac != "":
            d2d_path += mac.replace("/", "-") + "/"
        else:
            d2d_path += ".*/"

        if service != "":
            d2d_path += service.replace("/", "-")  + "/"
        else:
            d2d_path += ".*/"

        d2d_path += mode + "/"

        if category != "":
            d2d_path += category.replace("/", "-")  + "/"
        else:
            d2d_path += ".*/"

        if name != "":
            d2d_path += name.replace("/", "-") 
        else:
            d2d_path += ".*"


        return d2d_path


    def __checkInOutDefinedField(field) -> bool:

        if constants.field.TYPE not in field:
            return False

        elif not isinstance(field[constants.field.TYPE], str):
            return False

        elif constants.field.OPTIONAL in field and not isinstance(field[constants.field.OPTIONAL], bool):
            return False

        return True


    def __checkInOutField(data_dict, prototipe_dict) -> bool:

        # Chect type and non-exists
        for field in data_dict:
            if field not in prototipe_dict:
                return False
            if not typeTools.checkFieldType(data_dict[field], prototipe_dict[field][constants.field.TYPE]):
                return False

        # Check optional
        for field in prototipe_dict:
            field_prototipe = prototipe_dict[field]
            mandatory = constants.field.OPTIONAL not in field_prototipe or not field_prototipe[constants.field.OPTIONAL]
            if field not in data_dict and mandatory:
                return False

        return True


    def __jsonCommandRequest(request, service_container, command_callback, input_params, output_params):

            # json -> map
            try:
                args = json.loads(request)

            except:
                return constants.commandErrorMsg.BAD_INPUT


            # Ignore if disable
            if not service_container.map[constants.commandField.ENABLE]:
                return constants.commandErrorMsg.NOT_ENABLE_ERROR


            # Check args
            if not d2d.__checkInOutField(args, input_params):
                return constants.commandErrorMsg.BAD_INPUT


            # Call command
            response_dict = command_callback(args)
            if isinstance(response_dict, dict):

                # Check args
                if not d2d.__checkInOutField(response_dict, output_params):
                    return constants.commandErrorMsg.BAD_OUTPUT

                else:
                    # map -> json
                    response = json.dumps(response_dict, indent=1)
                    return response

            else:
                return constants.commandErrorMsg.CALLBACK_ERROR


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

        socket.close()


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

        connection.close()


    def __extractCommandInfo(data):

        try:
            command_info = json.loads(data)
            rc = container()
            rc.protocol = command_info[constants.commandField.PROTOCOL]
            rc.ip = command_info[constants.commandField.IP]
            rc.port = command_info[constants.commandField.PORT]
            rc.params = commandArgsDef(command_info[constants.commandField.INPUT])
            rc.response = commandArgsDef(command_info[constants.commandField.OUTPUT])
            rc.enable = True if constants.commandField.ENABLE not in command_info else command_info[constants.commandField.ENABLE]
            rc.timeout = 5 if constants.commandField.TIMEOUT not in command_info else command_info[constants.commandField.TIMEOUT]
            return rc

        except:
            return None


    def __extractInfoDescription(data):

        try:
            command_info = json.loads(data)
            rc = container()
            rc.protocol = command_info[constants.infoField.PROTOCOL]
            rc.ip = command_info[constants.infoField.IP]
            rc.req_port = command_info[constants.infoField.REQUEST_PORT]
            rc.update_port = command_info[constants.infoField.UPDATE_PORT]
            rc.valueType = command_info[constants.infoField.TYPE]

            return rc

        except:
            return None


    def __extractPathInfo(path):

        path_split = path.split("/")
        if len(path_split) < 6:
            return None

        rc = container()

        rc.prefix = path_split[0]
        if rc.prefix != constants.PREFIX:
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
            route_obj = IPRoute()
            ipr = route_obj.route('get', dst=dst)
            ip = ipr[0].get_attr('RTA_PREFSRC') if len(ipr) > 0 else "127.0.0.1"
            route_obj.close()
            return ip

        else:
            return ""


    def addServiceCommand(self, cmdCallback, name:str, input_params:dict, output_params:dict, category:str="", enable=True, timeout=5, protocol=constants.commandProtocol.JSON_UDP)-> bool:

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
            category = constants.category.GENERIC


        # Check if already registered
        if name in self.__service_container:
            return False


        # Create listen thread
        self.__service_container[name] = container()
        self.__service_container[name].run = True

        if protocol == constants.commandProtocol.JSON_UDP:
            listen_socket = udpRandomPortListener()
            self.__command_sockets.append(listen_socket)
            thread = threading.Thread(target=d2d.__udpListenerThread, daemon=True, args=[listen_socket, self.__service_container[name], cmdCallback, input_params, output_params])
            thread.start()
            self.__threads.append(thread)

        elif protocol == constants.commandProtocol.JSON_TCP:
            listen_socket = tcpListener()
            self.__command_sockets.append(listen_socket)
            thread = threading.Thread(target=d2d.__tcpListenerThread, daemon=True, args=[listen_socket, self.__service_container[name], cmdCallback, input_params, output_params])
            thread.start()
            self.__threads.append(thread)

        else:
            return False


        # Register command
        command_path = d2d.createCommandUID(self.__mac, self.__service, category, name)
        if not command_path:
            return False

        self.__service_used_paths[name] = command_path

        self.__service_container[name].map = {}
        self.__service_container[name].map[constants.commandField.PROTOCOL] = protocol
        self.__service_container[name].map[constants.commandField.IP] = self.__getOwnIP(self.__shared_table.masterIP())
        self.__service_container[name].map[constants.commandField.PORT] = listen_socket.port
        self.__service_container[name].map[constants.commandField.INPUT] = input_params
        self.__service_container[name].map[constants.commandField.OUTPUT] = output_params
        self.__service_container[name].map[constants.commandField.ENABLE] = enable
        self.__service_container[name].map[constants.commandField.TIMEOUT] = timeout

        return self.__shared_table.updateTableEntry(self.__service_used_paths[name], [json.dumps(self.__service_container[name].map)])


    def enableCommand(self, name, enable):
        if name not in self.__service_container:
            return False

        self.__service_container[name].map[constants.commandField.ENABLE] = enable
        return self.__shared_table.updateTableEntry(self.__service_used_paths[name], [json.dumps(self.__service_container[name].map)])


    def getAvailableComands(self, name:str="", service:str="", category:str="", mac:str="", wait:int=0) -> list:

        search_command_path = d2d.createCommandUID(mac, service, category, name)

        commands = []
        start = time.time()

        # Get commands from table
        while True:
            with self.__shared.__registered_mutex:
                d2d_map = self.__shared_table.geMapData()
                for client in d2d_map:
                    for d2d_path in d2d_map[client]:
                        if re.search(search_command_path, d2d_path):

                            # Command already setup
                            if d2d_path in self.__shared.__commands:
                                command_object = self.__shared.__commands[d2d_path]()

                            else:
                                command_object = None


                            if not command_object:
                                command_info = d2d.__extractCommandInfo(d2d_map[client][d2d_path][0])
                                path_info = d2d.__extractPathInfo(d2d_path)

                                command_object = commandInterface(path_info.mac, path_info.service, path_info.category, path_info.name,
                                                            command_info.protocol, command_info.ip, command_info.port, command_info.params,
                                                            command_info.response, command_info.enable, command_info.timeout)


                                # Save weak reference
                                self.__shared.__commands[d2d_path] = weakref.ref(command_object)

                            # Append to list
                            commands.append(command_object)


            # Check return value
            end = time.time()
            if len(commands) > 0 or wait < 0 or (wait > 0 and (end - start) > wait):
                break

            else:
                time.sleep(0.1)

        return commands


    def addInfoWriter(self, name:str, valueType:str, category:str="", protocol:str=constants.infoProtocol.ASCII) -> infoWriter:

        # Set defaults
        if category == "":
            category = constants.category.GENERIC

        info_path = d2d.createInfoWriterUID(self.__mac, self.__service, category, name)


        with self.__shared.__registered_mutex:
            if info_path not in self.__info_writer_objects:
                info_writer = infoWriter(self.__mac, self.__service, category, name, valueType)
                self.__info_writer_objects[info_path] = weakref.ref(info_writer)

            else:
                info_writer = self.__info_writer_objects[info_path]()

                if not info_writer:
                    info_writer = infoWriter(self.__mac, self.__service, category, name, valueType)
                    self.__info_writer_objects[info_path] = weakref.ref(info_writer)

        info_description = {}
        info_description[constants.infoField.PROTOCOL] = protocol
        info_description[constants.infoField.IP] = self.__getOwnIP(self.__shared_table.masterIP())
        info_description[constants.infoField.REQUEST_PORT] = info_writer.requestPort
        info_description[constants.infoField.UPDATE_PORT] = info_writer.updatePort
        info_description[constants.infoField.TYPE] = valueType


        if self.__shared_table.updateTableEntry(info_path, [json.dumps(info_description)]):
            return info_writer

        else:
            return None


    def getAvailableInfoReaders(self, name:str="", service:str="", category:str="", mac:str="", wait:int=0) -> list:


        search_info_path = d2d.createInfoWriterUID(mac, service, category, name)

        info_reader_objs = []
        start = time.time()

        # Get commands from table
        while True:
            with self.__shared.__registered_mutex:
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

                                info_reader_object = infoReader(path_info.mac, path_info.service, path_info.category, path_info.name,
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