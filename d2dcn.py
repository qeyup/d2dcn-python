
import os

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

    def __init__(self, broker_ip="", brocker_port=1883):
        self.__mac = ""
        self.__service = ""

    @property
    def service(self):
        return self.__service

    @property
    def mac(self):
        return self.__mac


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