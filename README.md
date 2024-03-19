
# iotlib

"Powering Your IoT Solutions with Simplicity and Efficiency"


## Description

iotlib is a versatile library built upon Paho™ MQTT, designed to streamline the development of IoT applications. 

Key features includes:

- Offers a programmatic alternative to traditional home automation platforms such as openHAB, Home Assistant, and Jeedom, providing more flexibility and control.
- A robust communication bridge leveraging the MQTT protocol, ensuring reliable data transfer between devices.
- Protocol-agnostic design, with support for Zigbee, Shelly MQTT, Tasmota MQTT, and Homie, offering flexibility in device integration.
- Comprehensive support for the creation and management of virtual devices, simplifying the integration between devices models, providers et protocols.
- Implementation of the Observer design pattern, enabling automatic triggering of actions on switches based on sensor value changes.
- The provision of 'availability processors', which allow for the execution of actions when a device's availability status changes.
- The inclusion of 'virtual device processors', offering a solution for handling changes in device values effectively.

## Installation

```bash
git clone https://github.com/slassabe/Domotic.git

cd iotlib
sudo pip3 install -r requirements.txt
```

## Usage

### Usage with Docker

## Contributing

## License

## Related projects

- [paho-mqtt](https://github.com/eclipse/paho.mqtt.python) : Eclipse Paho™ MQTT Python Client
- [miflora-mqtt-daemon](https://github.com/ThomDietrich/miflora-mqtt-daemon) : Xiaomi Mi Flora Plant Sensor MQTT Client/Daemon