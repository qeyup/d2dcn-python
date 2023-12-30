
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


class mcast():

    def __init__(self, ip, port):
        self.__ip = ip
        self.__port = port
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
        while True:
            try:
                data, (ip, port) = self.__sock.recvfrom(4096)
                return data, ip, port

            except socket.timeout:
                if timeout >= 0 and int(time.time()) - current_epoch_time >= timeout:
                    return None, None, None

            except:
                return None, None, None


    def send(self, msg):
        self.__sock.sendto(msg, (self.__ip, self.__port))


    def close(self):
        self.__sock.close()


class d2dBrokerDiscover():

    def __init__(self):
        self.__mcast_listen_request = mcast(d2dConstants.MCAST_DISCOVER_GRP, d2dConstants.MCAST_DISCOVER_SERVER_PORT)
        self.__mcast_send_respond = mcast(d2dConstants.MCAST_DISCOVER_GRP, d2dConstants.MCAST_DISCOVER_CLIENT_PORT)


    def __del__(self):
        self.stop()


    def __run(mcast_listen_request, mcast_send_respond):

        while True:
            read, ip, port = mcast_listen_request.read()
            if not read:
                break

            if read == d2dConstants.DISCOVER_MSG_REQUEST:
                mcast_send_respond.send(d2dConstants.DISCOVER_MSG_RESPONSE)


    def run(self, thread=False):
        if thread:
            t1 = threading.Thread(target=d2dBrokerDiscover.__run, daemon=False, args=[self.__mcast_listen_request, self.__mcast_send_respond])
            t1.start()
            return t1
        else:
            d2dBrokerDiscover.__run(self.__mcast)
            return None


    def stop(self):
        self.__mcast_listen_request.close()
        self.__mcast_send_respond.close()


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


class d2d():

    def __init__(self):
        self.__mac = hex(uuid.getnode()).replace("0x", "")

        process = psutil.Process(os.getpid())
        process_name = process.name()
        self.__service = process_name.split(".")[0]

        self.__client = None
        self.__registered_commands = {}


    @property
    def service(self):
        return self.__service


    @property
    def mac(self):
        return self.__mac


    def __brokerDisconnected(self):
        self.__client = None


    def __brokerMessaheReceived(self, message):

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
            self.__registered_commands[message.topic] = command_object

        return


    def __checkBrokerConnection(self):

        if self.__client:
            return True

        broker_ip = self.getBrokerIP()
        if not broker_ip:
            return False


        client = paho.mqtt.client.Client()
        try:
            client.connect(broker_ip, d2dConstants.MQTT_BROKER_PORT)
        except:
            return False

        client.on_message = lambda client, userdata, message : self.__brokerMessaheReceived(message)
        client.on_disconnect = lambda client, userdata, rc : self.__brokerDisconnected()
        client.loop_start()

        self.__client = client
        return True


    def __createMQTTPath(self, mac, service, type, mode, name):

        if mode not in [d2dConstants.COMMAND_LEVEL]:
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


    def getBrokerIP(self) -> str:
        mcast_send_request = mcast(d2dConstants.MCAST_DISCOVER_GRP, d2dConstants.MCAST_DISCOVER_SERVER_PORT)
        mcast_listen_respond = mcast(d2dConstants.MCAST_DISCOVER_GRP, d2dConstants.MCAST_DISCOVER_CLIENT_PORT)

        mcast_send_request.send(d2dConstants.DISCOVER_MSG_REQUEST)
        response, ip, port = mcast_listen_respond.read(5)
        if response == d2dConstants.DISCOVER_MSG_RESPONSE:
            return ip
        else:
            return None


    def addServiceCommand(self, cmdCallback, name:str, params:dict, response:dict, type:str="")-> bool:

        if not self.__checkBrokerConnection():
            return False

        mqtt_path = d2dConstants.MQTT_PREFIX + "/"

        mqtt_path += self.__mac + "/"

        mqtt_path += self.__service + "/"

        mqtt_path += d2dConstants.COMMAND_LEVEL + "/"

        if type == "":
            mqtt_path += d2dConstants.GENERIC_TYPE + "/"
        else:
            mqtt_path += type + "/"

        mqtt_path += name

        mqtt_path = mqtt_path.replace("#", "")


        mqtt_msg = {}
        mqtt_msg[d2dConstants.commandField.PROTOCOL] = d2dConstants.commandProtocol.JSON_UDP
        mqtt_msg[d2dConstants.commandField.IP] = ""
        mqtt_msg[d2dConstants.commandField.PORT] = ""
        mqtt_msg[d2dConstants.commandField.PARAMS] = params
        mqtt_msg[d2dConstants.commandField.RESPONSE] = response


        self.__client.publish(mqtt_path, payload=json.dumps(mqtt_msg), qos=0, retain=True)

        #self.__command_map[mqtt_path] = cmdCallback


        return True


    def subscribeComands(self, mac:str="", service:str="", type:str="", command:str="") -> bool:

        if not self.__checkBrokerConnection():
            return False

        mqtt_path = d2dConstants.MQTT_PREFIX + "/"

        if mac != "":
            mqtt_path += mac + "/"
        else:
            mqtt_path += "+/"

        if service != "":
            mqtt_path += service + "/"
        else:
            mqtt_path += "+/"

        mqtt_path += d2dConstants.COMMAND_LEVEL + "/"

        if type != "":
            mqtt_path += type + "/"
        else:
            mqtt_path += "+/"

        if command != "":
            mqtt_path += command + "/"
        else:
            mqtt_path += "+"

        mqtt_path = mqtt_path.replace("#", "")

        try:
            self.__client.subscribe(mqtt_path)
        except:
            return False

        return True


    def getAvailableComands(self, mac:str="", service:str="", type:str="", command:str="") -> list:

        mqtt_pattern_path = self.__createMQTTPath(mac, service, type, d2dConstants.COMMAND_LEVEL, command)
        mqtt_pattern_path = mqtt_pattern_path.replace("+", ".*")

        commands = []
        for mqtt_path in self.__registered_commands:
            if re.search(mqtt_pattern_path, mqtt_path):
                commands.append(self.__registered_commands[mqtt_path])

        return commands


    def subscribeInfo(self, mac:str="", service:str="", type="", name:str="", updateCallback=None) -> bool:
        return False


    def getSubscribedValues(self) -> dict:
        return {}


    def publishInfo(self, name:str, value:str) -> bool:
        return False