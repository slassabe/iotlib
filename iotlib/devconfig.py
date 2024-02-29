
from enum import Enum



class PropertyConfig(Enum):
    """Defines property name enums for virtual devices.

    This enum defines property names, types, and owning node 
    for different virtual device types. Allows generic access 
    to property configuration details.

    Properties can be accessed like:

    PropertyConfig.ADC_PROPERTY.property_name
    PropertyConfig.ADC_PROPERTY.property_type  
    PropertyConfig.ADC_PROPERTY.node
    """

    ALARM_PROPERTY = 'alarm.alarm', bool
    ADC_PROPERTY = 'sensor.voltage', float
    BUTTON_PROPERTY = 'sensor.action', str
    CONDUCTIVITY_PROPERTY = 'sensor.conductivity', int
    HUMIDITY_PROPERTY = 'sensor.humidity', int
    LIGHT_PROPERTY = 'sensor.light', int
    MOTION_PROPERTY = 'sensor.occupancy', bool
    SWITCH_PROPERTY = 'switch.power', bool
    SWITCH0_PROPERTY = 'switch0.power', bool
    SWITCH1_PROPERTY = 'switch1.power', bool
    TEMPERATURE_PROPERTY = 'sensor.temperature', float

    def __new__(cls, qualified_property:str, property_type:type):
        member = object.__new__(cls)
        member.property_name = qualified_property.split('.')[1]
        member.property_type = property_type
        member.property_node = qualified_property.split('.')[0]
        return member

    def __str__(self):
        return f'{self.property_name}'


class ButtonValues(Enum):
    """Enumeration defining button action values.
    
    This enum defines string constants for possible button actions
    like single press, double press, long press etc.

    For example:

    ButtonValues.BUTTON_SINGLE_ACTION: 'single'

    Using this enum allows code to refer to button actions
    through constant values rather than string literals.
    """
    SINGLE_ACTION = 'single'
    DOUBLE_ACTION = 'double'
    LONG_ACTION = 'long'
    OFF = 'off'

