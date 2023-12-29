
import os
import socket
import struct
import threading
import time
import uuid
import psutil


class d2dConstants():
    MCAST_DISCOVER_GRP = '224.1.1.1'
    MCAST_DISCOVER_SERVER_PORT = 5005
    MCAST_DISCOVER_CLIENT_PORT = 5006
    MQTT_BROKER_PORT = 1883
    MULTICAST_TTL = 2
    DISCOVER_MSG_REQUEST = b"Who's broker?"
    DISCOVER_MSG_RESPONSE = b"I'm broker"


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

    def __init__(self):
        self.__name = ""
        self.__mac = ""
        self.__service = ""
        self.__api = {}
        self.__result = {}

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
    def api(self):
        return self.__api

    @property
    def result(self):
        return self.__result

    def call(self, args:dict) -> dict:
        return False


class d2d():

    def __init__(self):
        self.__mac = hex(uuid.getnode()).replace("0x", "")

        process = psutil.Process(os.getpid())
        process_name = process.name()
        self.__service = process_name.split(".")[0]


    @property
    def service(self):
        return self.__service


    @property
    def mac(self):
        return self.__mac


    def getBrokerIP(self) -> str:
        mcast_send_request = mcast(d2dConstants.MCAST_DISCOVER_GRP, d2dConstants.MCAST_DISCOVER_SERVER_PORT)
        mcast_listen_respond = mcast(d2dConstants.MCAST_DISCOVER_GRP, d2dConstants.MCAST_DISCOVER_CLIENT_PORT)

        mcast_send_request.send(d2dConstants.DISCOVER_MSG_REQUEST)
        response, ip, port = mcast_listen_respond.read(5)
        if response == d2dConstants.DISCOVER_MSG_RESPONSE:
            return ip
        else:
            return None


    def addServiceCommand(self, cmdCallback, name:str, args:dict, result:dict, type:str="")-> bool:
        return True


    def getAvailableComands(self, mac:str="", service:str="", type:str="", command:str="") -> list:
        return []


    def subscribeInfo(self, mac:str="", service:str="", type="", name:str="", updateCallback=None) -> bool:
        return False


    def getSubscribedValues(self) -> dict:
        return {}


    def publishInfo(self, name:str, value:str) -> bool:
        return False