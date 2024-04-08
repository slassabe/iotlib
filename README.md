
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

## Table of Contents

- [iotlib](#iotlib)
  - [Description](#description)
  - [Table of Contents](#table-of-contents)
  - [Getting Started](#getting-started)
  - [Core Concepts](#core-concepts)
    - [MQTT Service](#mqtt-service)
    - [MQTT Bridge](#mqtt-bridge)
    - [Coding and decoding message](#coding-and-decoding-message)
    - [Virtual Devices](#virtual-devices)
    - [Codec Factory](#codec-factory)
    - [Processor](#processor)
  - [Usage Examples](#usage-examples)
    - [MQTT connection](#mqtt-connection)
    - [Device discovery](#device-discovery)
    - [Switch Management](#switch-management)
  - [Related projects](#related-projects)

## Getting Started

```bash
git clone https://github.com/slassabe/iotlib.git

cd iotlib
sudo pip3 install -r requirements.txt
```

## Core Concepts

This section provides an overview of the fundamental concepts and principles that underpin this project. Understanding these concepts will help you to use and contribute to the project more effectively.

![Alt text](_internals/stack.png)

### MQTT Service

The MQTT service is essential for establishing a connection to an MQTT broker and handling events such as connect and disconnect. It also allows for the addition of custom handlers for these events. Furthermore, main loop facilities are necessary for the continuous processing of these events. This support is provided by the `MQTTClient` class.

### MQTT Bridge

MQTT Bridges serve as the intermediary between the MQTT Services and the decoding layer. They manage several key tasks:

- **MQTT Connections**: Establish and maintain connections with the MQTT broker.
- **Message Callbacks**: Handle incoming MQTT messages and pass them to the appropriate decoder.
- **Availability Updates**: Monitor and report the online/offline status of MQTT clients.
- **Value Handling**: Process the decoded values and pass them to the appropriate handlers.

For example, when a message is received from an MQTT client, the MQTT Bridge will pass the message to the appropriate decoder based on the topic of the message. Once the message is decoded, the MQTT Bridge will then pass the decoded values to the appropriate handlers for further processing.

### Coding and decoding message

Each device model and protocol uses its own unique MQTT-based exchange format for encoding and decoding messages.

- Decoding functionalities are essential for extracting values from messages received from `sensors` and `operables` devices.
- Encoding functionalities are utilized by `operables` to send commands to the devices.

A separate codec is required to handle each protocol, ensuring accurate and efficient communication.

### Virtual Devices 

Virtual devices serve as an abstraction layer over physical devices, facilitating interoperability across different types of devices. These virtual devices are organized into a hierarchical structure as follows:

- **Sensors**: These virtual devices are responsible for measuring and reporting various environmental conditions. They include:
  - Temperature Sensor
  - Humidity Sensor
  - Light Sensor
  - Conductivity Sensor
  - Button Sensor
  - Motion Sensor
  - Analog-to-Digital Converter

- **Operables**: These virtual devices are capable of performing certain actions. They include:
  - Alarm
  - Switch

Each physical device is associated with one or more virtual devices, which handle the processing and management of data. For instance, an air sensor might be associated with a Temperature Sensor and a Humidity Sensor virtual device, which handle temperature and humidity data respectively.
This support is provided by the `VirtualDevice` class.

### Codec Factory

The process of codec instantiation can be tedious as it requires knowledge of the class name and the necessary arguments. To simplify this process, a codec factory is provided. By specifying the protocol and model you need, the factory will create the required instance for you.

```python
import iotlib
factory = iotlib.factory.CodecFactory()
codec = factory.create_instance(model=Model.TUYA_TS0002,
                                protocol=Protocol.Z2M,
                                device_name=DEVICE_NAME,
                                v_switch0=v_switch0,
                                v_switch1=v_switch1,
```

Below is a table outlining the available codecs.

|Protocol| Model        | Codec Class   | Virtual Device Parameters |
| ------ | ------------ | ------------- | --------------------------|
| Z2M    | TUYA_TS0002  | TuYaTS0002    | v_switch0, v_switch1      |
| Homie  | MIFLORA      | In progress   |                           |
| Z2M    | NEO_ALARM    | NeoNasAB02B2  | v_alarm                   |
| RING   | RING_CAMERA  | In progress   |                           |
| TASMOTA| SHELLY_PLUGS | In progress   |                           |
| SHELLY | SHELLY_PLUGS | In progress   |                           |
| TASMOTA| SHELLY_UNI   | In progress   |                           |
| SHELLY | SHELLY_UNI   | In progress   |                           |
| Z2M    | TUYA_SOIL    | Ts0601Soil    | v_temp, v_humi            |
| Z2M    | ZB_AIRSENSOR | SonoffSnzb02  |                           |
| Z2M    | ZB_BUTTON    | SonoffSnzb01  | v_button                  |
| Z2M    | ZB_MOTION    | SonoffSnzb3   | v_motion                  |
| Z2M    | ZB_MINI      | SonoffZbminiL | v_switch                  |


### Processor

Processors are utilized to customize the behavior of devices for processing updates from virtual devices and sensors. They perform the following functions:

- **On Device Availability**:
  - Log the availability status of the device.
  - Publish the availability status to an MQTT topic for real-time tracking.

- **On Virtual Device Updates**:
  - Log updates from virtual devices for record-keeping and debugging.
  - Process button press actions on registered switches and alarms, allowing for interactive control.
  - Handle motion sensor state changes and trigger registered switches when occupancy is detected, enabling automated responses.
  - Publish property updates to an MQTT broker for monitoring purpose.

The predefined behavior provided by these processors can be extended with your own code by subclassing the `AvailabilityProcessor` and `VirtualDeviceProcessor` classes. This allows for greater flexibility and customization to meet specific needs.

## Usage Examples

### MQTT connection 

In this example, we establish a connection to the local MQTT broker, initiate the process, wait for 2 seconds, and then stop the process. This brief pause allows for any pending operations to complete before the connection is closed.

```python
import time
import iotlib

client = iotlib.client.MQTTClient('', 'localhost')
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

client = iotlib.client.MQTTClient('', 'localhost')
client.start()
time.sleep(1)
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

### Switch Management

This example demonstrates how to interact with a Sonoff ZBMINI switch via the Zigbee2MQTT gateway. The steps include creating a virtual switch, a codec instance, a bridge instance, and a logger instance, setting the virtual switch to ON, and starting the main loop.

1) **Create a Virtual Switch**: This switch is configured with a 2-second countdown, meaning it will automatically turn off 2 seconds after being turned on.
2) **Create a Codec Instance**: The CodecFactory is used to create a codec instance associated with the virtual switch. This codec is configured for the device named `SWITCH_CAVE`, the ZB_MINI model and the Z2M protocol.
3) **Create a Bridge Instance**: The MQTTBridge is used to facilitate communication between the virtual switch and the MQTT broker.
4) **Create a Logger Instance**: A logger is created to log updates from the virtual switch. This is useful for debugging and record-keeping.
5) **Set the Virtual Switch to ON**: The virtual switch is manually triggered to start in the ON state.
6) **Start the Main Loop**: The main loop is started, which keeps the program running indefinitely.

```python
import time
import logging
import iotlib
logging.basicConfig(level=logging.INFO)

client = iotlib.client.MQTTClient('', 'localhost')
client.start()
# 1) Create a virtual switch 
v_switch = iotlib.virtualdev.Switch(friendly_name='switch',
                                    quiet_mode=True,    # debouncing mode
                                    countdown=2) 
# 2) Create a codec instance 
factory = iotlib.factory.CodecFactory()
codec = factory.create_instance(model=iotlib.factory.Model.ZB_MINI,
                                protocol=iotlib.factory.Protocol.Z2M,
                                device_name='SWITCH_CAVE',
                                v_switch=v_switch)
# 3) Create a bridge instance 
iotlib.bridge.MQTTBridge(client, codec)
# 4) Create a logger instance 
logger = iotlib.processor.VirtualDeviceLogger(debug=True) 
v_switch.processor_append(logger)
# 5) Set the virtual switch to ON
v_switch.trigger_start(client)  
# 6) Start the main loop
while True:
    time.sleep(1)
```

Once the Zigbee switch is set to ON, it will automatically turn OFF after 2 seconds. The log output will show the power state changes of the virtual switch:

```bash
- Logging virtual device (friendly_name : "switch" - property : "power" - value : "True")
- Logging virtual device (friendly_name : "switch" - property : "power" - value : "False")
```

## Related projects

- [paho-mqtt](https://github.com/eclipse/paho.mqtt.python) : Eclipse Paho™ MQTT Python Client
- [miflora-mqtt-daemon](https://github.com/ThomDietrich/miflora-mqtt-daemon) : Xiaomi Mi Flora Plant Sensor MQTT Client/Daemon