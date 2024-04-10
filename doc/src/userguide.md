# User Guide

## MQTT connection 

In this example, we establish a connection to the local MQTT broker, initiate the process, wait for 2 seconds, and then stop the process. This brief pause allows for any pending operations to complete before the connection is closed.

```python
import time
import iotlib

client = iotlib.client.MQTTClient('', 'localhost')
client.start()
time.sleep(2)
client.stop()
```

## Device discovery

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

However, keep in mind that the list of devices can change over time. To handle this, a `DiscoveryProcessor` is available, 
which allows you to customize the behavior when new devices are discovered. Each time a device is found, the `process_discovery_update(self, devices)` 
method is called with the updated list of devices. This provides a flexible way to handle changes in the device landscape.

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

## Monitoring Device Availability

This section demonstrates how to utilize the `MQTTBridge` and `AvailabilityProcessor` to monitor and log the availability of a device. Instead of employing an active loop, we will configure the behavior based on the device state using processors.

1) **Create a Codec for Airsensor**: This step involves setting up a codec for a Sonoff model device that is connected via the default Zigbee protocol.
2) **Instantiate a Bridge**: Here, we create an instance of MQTTBridge. This serves as the communication facilitator between the virtual sensor and the MQTT broker.
3) **Set up an Availability Logger**: This logger is responsible for tracking the device's availability.
4) **Register the Availability Logger with the Bridge**: This step involves adding the previously created logger to the bridge.
5) **Initiate the MQTT Client**: This will establish a connection with the broker and start listening for messages.


```python
import time
import logging

import iotlib


DEVICE_NAME = 'TEMP_SALON'
logging.basicConfig(level=logging.INFO)

client = iotlib.client.MQTTClient('', 'localhost')
# 1) Create a codec for the device model and protocol
codec = iotlib.factory.CodecFactory().create_instance(model=iotlib.factory.Model.ZB_AIRSENSOR,
                                                      protocol=iotlib.factory.Protocol.Z2M,
                                                      device_name=DEVICE_NAME)
# 2) Create a bridge instance to connect the codec to the MQTT client
bridge = iotlib.bridge.MQTTBridge(client, codec)
# 3) Create an availability logger, which logs the availability of the device
logger = iotlib.processor.AvailabilityLogger(debug=True)
# 4) Add the availability logger to the bridge
bridge.add_availability_processor(logger)
# 5) Start the MQTT client, which will connect to the broker and start
# listening for messages
client.start()
# 6) Start an infinite loop to handle messages
while True:
    time.sleep(2)
# Should display ;
#  - if the device is configured and available : [INFO] [TEMP_SALON] is available
#  - if the device is configured and unavailable : [INFO] [TEMP_SALON] is unavailable
#  Nothing is displayed if the device is not not configured in Zigbee2MQTT

```

The output will display one of the following messages:

- If the device is configured and available, it will display: "[INFO] [TEMP_SALON] is available".
- If the device is configured but unavailable, it will display: "[INFO] [TEMP_SALON] is unavailable".
- If the device is not configured in Zigbee2MQTT, there will be no output.

## Switch state Logging

This example demonstrates how to create a Sonoff ZBMINI switch and log its values via the Zigbee2MQTT gateway. The steps include creating a virtual switch, a codec instance, a bridge instance, and a logger instance, setting the virtual switch to ON, and starting the main loop.

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

## Switch Management

This example extends the previous one by controlling a Switch with two sensors: a button and a motion sensor.

The steps are as follows:

- Steps 1 to 3 are the same as in the previous example.
- Step 4: Set up a motion sensor with `MotionTrigger` processing support. This action will turn the light ON when motion is detected.
    - 4.1: **Instantiate a virtual motion sensor**, create a codec instance, and establish a bridge instance for the virtual motion sensor.
    - 4.2: **Generate a processor instance** for the virtual motion sensor that can detect motion.
    - 4.3: **Add the switch** to the list of observers for the virtual motion sensor.
- Step 5: Establish a button sensor with `ButtonTrigger` processing support. This action will turn the light ON when the button is pressed.
    - 5.1: **Instantiate a virtual button sensor**, create a codec instance, and establish a bridge instance for the virtual button sensor.
    - 5.2: **Generate a processor instance** for the virtual button sensor that can detect a key press.
    - 5.3: **Add the switch** to the list of observers for the virtual button sensor.

```python
import time
import iotlib

client = iotlib.client.MQTTClient('switch_mgr', 'localhost')
client.start()
# 1) Create a virtual switch 
v_switch = iotlib.virtualdev.Switch(quiet_mode=True,    # debouncing mode
                                    countdown=10)
# 2) Create a codec instance 
factory = iotlib.factory.CodecFactory()
switch_codec = factory.create_instance(model=iotlib.factory.Model.ZB_MINI,
                                       protocol=iotlib.factory.Protocol.Z2M,
                                       device_name='SWITCH_PLUG',
                                       v_switch=v_switch)
# 3) Create a bridge instance 
iotlib.bridge.MQTTBridge(client, switch_codec)
# 4.1) Instantiate a virtual motion sensor
v_motion = iotlib.virtualdev.Motion()
motion_codec = factory.create_instance(iotlib.factory.Model.ZB_MOTION,
                                       iotlib.factory.Protocol.Z2M,
                                       device_name='MOTION_CAVE',
                                       v_motion=v_motion)
iotlib.bridge.MQTTBridge(client, motion_codec)
# 4.2) Generate a processor instance
v_motion.processor_append(iotlib.processor.MotionTrigger(mqtt_service=client))
# 4.3) Add the switch 
v_motion.add_observer(v_switch)

# 5.1) Instantiate a virtual button sensor
v_button = iotlib.virtualdev.Button()
button_codec = factory.create_instance(iotlib.factory.Model.ZB_BUTTON,
                                       iotlib.factory.Protocol.Z2M,
                                       device_name='INTER_CAVE',
                                       v_button=v_button)
iotlib.bridge.MQTTBridge(client, button_codec)
# 5.2) Generate a processor instance 
v_button.processor_append(iotlib.processor.ButtonTrigger(mqtt_service=client,
                                                         countdown_long=60*1))
# 5.3) Add the switch
v_button.add_observer(v_switch)

# 6) Start the main loop
while True:
    time.sleep(1)

```

