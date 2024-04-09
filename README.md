
# iotlib

"Less is More - Powering Your IoT Solutions with MQTT integration"

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

## Documentation

You can access the full documentation at [slassabe.github.io/iotlib](https://slassabe.github.io/iotlib)

## Getting Started

```bash
git clone https://github.com/slassabe/iotlib.git

cd iotlib
sudo pip3 install -r requirements.txt
```

## Related projects

- [paho-mqtt](https://github.com/eclipse/paho.mqtt.python) : Eclipse Paho™ MQTT Python Client
- [miflora-mqtt-daemon](https://github.com/ThomDietrich/miflora-mqtt-daemon) : Xiaomi Mi Flora Plant Sensor MQTT Client/Daemon
- [ring-mqtt](https://github.com/tsightler/ring-mqtt) : Ring devices to MQTT Bridge
- [zigbee2mqtt](https://github.com/Koenkk/zigbee2mqtt) : Allows you to use your Zigbee devices without the vendor's bridge or gateway.