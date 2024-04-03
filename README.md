
# iotlib

"Less is More - Powering Your IoT Solutions with Simplicity and Efficiency"


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

## Contents

- [iotlib](#iotlib)
  - [Description](#description)
  - [Contents](#contents)
  - [Getting Started](#getting-started)
  - [Usage Examples](#usage-examples)
    - [MQTT connection](#mqtt-connection)
    - [Device discovery](#device-discovery)
    - [Usage with Docker](#usage-with-docker)
  - [Contributing Guidelines](#contributing-guidelines)
  - [License Information](#license-information)
  - [Related projects](#related-projects)

## Getting Started

```bash
git clone https://github.com/slassabe/iotlib.git

cd iotlib
sudo pip3 install -r requirements.txt
```

## Usage Examples

### MQTT connection 

In this example, we establish a connection to the local MQTT broker, initiate the process, wait for 2 seconds, and then stop the process. This brief pause allows for any pending operations to complete before the connection is closed.

```python
import time
import iotlib

if __name__ == "__main__":
    BROKER = 'localhost'
    # Create MQTT client
    client = iotlib.client.MQTTClient('', BROKER)
    client.start()
    time.sleep(2)
    client.stop()
```

### Device discovery

The `iotlib.discoverer` module provides discoverers that can be instantiated to find and identify connected IoT devices in your network. These discoverers use various protocols and techniques to detect a wide range of devices, providing a comprehensive overview of the IoT landscape within your network.

In this basic example, we utilize the `get_devices()` method from the `UnifiedDiscoverer` class. This method is used to retrieve all connected devices after a specified waiting period. It provides a simple and efficient way to discover and interact with all available devices in your network.

```python
import time
import iotlib

def basic_discovery(mqtt_client: iotlib.client.MQTTClient):
    _discoverer = iotlib.discoverer.UnifiedDiscoverer(mqtt_client)
    time.sleep(2)
    devices = _discoverer.get_devices()
    print(f"Basic discovery - length : {len(devices)}")
    for device in devices:
        print(f" - device: {repr(device)}")

if __name__ == "__main__":
    # Create MQTT client
    client = iotlib.client.MQTTClient('', 'localhost')
    client.start()

    basic_discovery(client)
    
    time.sleep(2)
```

This example will output :

```bash
Basic discovery - length : 14
 - device: <Device : SWITCH_CAVE, address : 0x00124b0025e23b21, model: Model.ZB_MINI, protocol: Protocol.Z2M>
 - device: <Device : SWITCH_CHAUFFERIE, address : 0x00124b00257b862a, model: Model.ZB_MINI, protocol: Protocol.Z2M>
  ...
 - device: <Device : tasmota_577591, address : tasmota-577591-5521, model: Model.SHELLY_PLUGS, protocol: Protocol.TASMOTA>
 - device: <Device : tasmota_D6590C, address : tasmota-D6590C-6412, model: Model.SHELLY_UNI, protocol: Protocol.TASMOTA>
```

However, keep in mind that the list of devices can change over time. To handle this, a `DiscoveryProcessor` is available, which allows you to customize the behavior when new devices are discovered. Each time a device is found, the `process_discovery_update(self, devices)` method is called with the updated list of devices. This provides a flexible way to handle changes in the device landscape.

```python
import time
import iotlib

class BasicDiscoveryProc(iotlib.discoverer.DiscoveryProcessor):
    def process_discovery_update(self, devices):
        print(f"Discovered {len(devices) :} devices")
        for device in devices:
            print(f" * device: {repr(device)}")

def discover_it(mqtt_client: iotlib.client.MQTTClient):
    _discoverer = iotlib.discoverer.UnifiedDiscoverer(mqtt_client)
    _discoverer.add_discovery_processor(BasicDiscoveryProc())

if __name__ == "__main__":
    # Create MQTT client
    client = iotlib.client.MQTTClient('', 'localhost')
    client.start()

    discover_it(client)
    
    client.loop_forever()
```

This example will output :

```bash
Discovered 10 devices
 * device: <Device : SWITCH_CAVE, address : 0x00124b0025e23b21, model: Model.ZB_MINI, protocol: Protocol.Z2M>
 * device: <Device : SWITCH_CHAUFFERIE, address : 0x00124b00257b862a, model: Model.ZB_MINI, protocol: Protocol.Z2M>
  ...
Discovered 1 devices
 * device: <Device : tasmota_577591, address : tasmota-577591-5521, model: Model.SHELLY_PLUGS, protocol: Protocol.TASMOTA>
Discovered 1 devices
 * device: <Device : tasmota_D6590C, address : tasmota-D6590C-6412, model: Model.SHELLY_UNI, protocol: Protocol.TASMOTA>
  ...
```

Please note that the `process_discovery_update` method is executed sequentially, first for devices supported by Zigbee2MQTT, and then for devices supported by Tasmota. This sequence occurs over a period of time, allowing for a systematic update of all connected devices.

### Usage with Docker

## Contributing Guidelines

## License Information

## Related projects

- [paho-mqtt](https://github.com/eclipse/paho.mqtt.python) : Eclipse Paho™ MQTT Python Client
- [miflora-mqtt-daemon](https://github.com/ThomDietrich/miflora-mqtt-daemon) : Xiaomi Mi Flora Plant Sensor MQTT Client/Daemon