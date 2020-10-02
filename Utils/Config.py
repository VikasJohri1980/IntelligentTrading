from os.path import join as path_join
from os.path import dirname
import configparser

from Utils.Singleton import Singleton

class Config(metaclass=Singleton):
    
    def __init__(self):
        path = path_join(dirname(dirname(__file__)), "config.ini")
        self.__config = configparser.ConfigParser()
        self.__config.read(path)
        
    def get(self, section=None, parameter=None):
        try:
            return self.__config.get(section, parameter)
        except:
            print("No parameter {} in section: {}".format(parameter, section))
            return ""