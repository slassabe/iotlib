#!/usr/local/bin/python3
# coding=utf-8

import enum


class BaseTopic(enum.Enum):
    """
    Enumeration for base MQTT topics used in the library.

    This enumeration defines the base topics for two types of MQTT messages:
    - `Z2M_BASE_TOPIC`: Base topic for Zigbee2MQTT messages.
    - `TASMOTA_DISCOVERY_TOPIC`: Base topic for Tasmota discovery messages.
    """
    Z2M_BASE_TOPIC = 'zigbee2mqtt'

    TASMOTA_DISCOVERY_TOPIC = 'tasmota/discovery'
