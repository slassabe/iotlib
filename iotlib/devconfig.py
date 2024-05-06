#!/usr/local/bin/python3
# coding=utf-8

"""
This module defines the `PropertyConfig` and `ButtonValues` enums.

The `PropertyConfig` enum defines property names, types, and owning nodes for different 
virtual device types. 
It allows generic access to property configuration details.

The `ButtonValues` enum defines string constants for possible button actions like single 
press, double press, long press etc. Using this enum allows code to refer to button actions 
through constant values rather than string literals.

"""

from enum import Enum


class PropertyConfig(Enum):
    """
    Defines property name enums for virtual devices.

    This enum defines property names, types, and owning node
    for different virtual device types. Allows generic access
    to property configuration details.

    :ivar ALARM_PROPERTY: Represents the 'alarm.power' property of type bool.
    :ivar ADC_PROPERTY: Represents the 'sensor.voltage' property of type float.
    :ivar BUTTON_PROPERTY: Represents the 'sensor.action' property of type str.
    :ivar CONDUCTIVITY_PROPERTY: Represents the 'sensor.conductivity' property of type int.
    :ivar HUMIDITY_PROPERTY: Represents the 'sensor.humidity' property of type int.
    :ivar LIGHT_PROPERTY: Represents the 'sensor.light' property of type int.
    :ivar MOTION_PROPERTY: Represents the 'sensor.occupancy' property of type bool.
    :ivar SWITCH_PROPERTY: Represents the 'switch.power' property of type bool.
    :ivar SWITCH0_PROPERTY: Represents the 'switch0.power' property of type bool.
    :ivar SWITCH1_PROPERTY: Represents the 'switch1.power' property of type bool.
    :ivar TEMPERATURE_PROPERTY: Represents the 'sensor.temperature' property of type float.

    """

    ALARM_PROPERTY = "alarm.power", bool
    ADC_PROPERTY = "sensor.voltage", float
    BUTTON_PROPERTY = "sensor.action", str
    CONDUCTIVITY_PROPERTY = "sensor.conductivity", int
    HUMIDITY_PROPERTY = "sensor.humidity", int
    LIGHT_PROPERTY = "sensor.light", int
    MOTION_PROPERTY = "sensor.occupancy", bool
    SWITCH_PROPERTY = "switch.power", bool
    SWITCH0_PROPERTY = "switch0.power", bool
    SWITCH1_PROPERTY = "switch1.power", bool
    TEMPERATURE_PROPERTY = "sensor.temperature", float

    def __new__(cls, qualified_property: str, property_type: type):
        member = object.__new__(cls)
        member.property_name = qualified_property.split(".")[1]
        member.property_type = property_type
        member.property_node = qualified_property.split(".")[0]
        return member

    def __str__(self):
        return f"{self.property_name}"


class ButtonValues(Enum):
    """
    Enumeration defining button action values.

    This enum defines string constants for possible button actions
    like single press, double press, long press etc.

    Using this enum allows code to refer to button actions
    through constant values rather than string literals.

    :ivar SINGLE_ACTION: Represents a single button press action.
    :ivar DOUBLE_ACTION: Represents a double button press action.
    :ivar LONG_ACTION: Represents a long button press action.
    :ivar OFF: Represents the button off state.
    """

    SINGLE_ACTION = "single"
    DOUBLE_ACTION = "double"
    LONG_ACTION = "long"
    OFF = "off"
