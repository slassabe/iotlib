
from enum import Enum

class PropertyConfig(Enum):
    """Enumeration defining property names and types for virtual devices.

    This class defines enum members that represent property names and 
    associated types for different virtual device types. The enum members
    have the property name and type attributes to allow easy access.

    For example:

    PropertyConfig.ADC_PROPERTY.property_name gives 'voltage'
    PropertyConfig.ADC_PROPERTY.property_type gives float
    
    This allows using PropertyConfig to generically access property 
    details between 'processors' et 'virtualdev' modules
    """
    
    ADC_PROPERTY = 'voltage', float
    BUTTON_PROPERTY = 'action', str
    CONDUCTIVITY_PROPERTY = 'conductivity', int
    DUMMY_PROPERTY = 'dummy', str
    HUMIDITY_PROPERTY = 'humidity', int
    LIGHT_PROPERTY = 'light', int
    MOTION_PROPERTY = 'occupancy', bool
    SWITCH_PROPERTY = 'power', bool
    TEMPERATURE_PROPERTY = 'temperature', float
    ALARM_PROPERTY = 'alarm', bool

    def __new__(cls, property_name, property_type):
        member = object.__new__(cls)
        member.property_name = property_name
        member.property_type = property_type
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

