#!/usr/local/bin/python3
# coding=utf-8

import enum


class BaseTopic(enum.Enum):
    """Enumeration for base topics used in the library."""
    Z2M_BASE_TOPIC = 'zigbee2mqtt'
    TASMOTA_DISCOVERY_TOPIC = 'tasmota/discovery'
