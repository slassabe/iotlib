#!/usr/local/bin/python3
# coding=utf-8

import os
import sys
from pathlib import Path

from configparser import ConfigParser, NoSectionError, NoOptionError

from .utils import Singleton
from . import package_level_logger


class MQTTConfig(metaclass=Singleton):
    """ Parse the MQTT configuation file 
    """
    _logger = package_level_logger

    def __init__(self):
        """ Parse config file

        Args:
            config_dir (str): directory 
            config_name (str): file name
        """
        CONFIG_DIR = 'config'
        CONFIG_NAME = 'iotlib.ini'

        root_dir = Path(__file__).parent.parent.absolute()
        _config_path = os.path.join(root_dir, CONFIG_DIR, CONFIG_NAME)
        self._logger.debug('Config path : %s', _config_path)

        self.config = ConfigParser()
        self.config.read(_config_path)
        try:
            _section = self.config.get('BASE', 'HOSTING')

            self.hostname = self.config.get(_section, 'HOSTNAME')
            self.port = self.config.getint(_section, 'PORT')
            self.user_name = self.config.get(_section, 'USR')
            self.user_pwd = self.config.get(_section, 'PWD')
            self.tls = self.config.getboolean(_section, 'TLS')
            self.keepalive = self.config.getint(_section, 'KEEPALIVE')
            self.clean_start = self.config.getboolean(_section, 'CLEAN_START')

            self.domotic_base_topic = self.config.get('MQTT_TOPICS', 'BASE_DOMOTIC')
            self.z2m_sub_topic = self.config.get('MQTT_TOPICS', 'BASE_Z2M')
            self.shelly_sub_topic = self.config.get('MQTT_TOPICS', 'BASE_SHELLY')
            self.tasmota_cmd_topic = self.config.get('MQTT_TOPICS', 'CMND_TASMOTA')
            self.tasmota_status_topic = self.config.get('MQTT_TOPICS', 'STATUS_TASMOTA')
            self.tasmota_telemetry_topic = self.config.get('MQTT_TOPICS', 'TELEMETRY_TASMOTA')
            self.homie_sub_topic = self.config.get('MQTT_TOPICS', 'BASE_HOMIE')
            self.ring_sub_topic = self.config.get('MQTT_TOPICS', 'BASE_RING')
        except NoSectionError as exp:
            self._logger.fatal('[%s] malformatted config file %s -> exit', exp, _config_path)
            self._logger.error('Sections : %s', self.config.sections())
            sys.exit(1)
        except NoOptionError as exp:
            self._logger.fatal('%s malformatted config file %s -> exit', exp, _config_path)
            self._logger.fatal('Defined options : %s',
                               self.config.options(_section))
            sys.exit(1)
        self._logger.debug('Configuration file :')
        self._logger.debug('HOSTING : %s', _section)
        self._logger.debug('ROOT_TOPIC : %s', self.domotic_base_topic)

        for k in self.config[_section]:
            self._logger.debug('\t - ' + k + ' : ' + self.config[_section][k])
