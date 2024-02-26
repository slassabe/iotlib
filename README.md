# iotlib

## TO DO

- remove hook.PropertyProcessor
  - move processing on processor
- remove virtualdev.concrete_device
  - add bridge in virtualdev.handle_new_value(self, value, device)
- remove virtualdev.AckSwitch
- unable only one message handler per topic
  - Connector._message_handler_list -> Connector._message_handler
  - Connector._get_message_handlers -> Connector._get_message_handler
  - DeviceOnZigbee2MQTT._decode_values -> Connector._decode_values
    - without loop
  - merge SonoffSnzb02._decode_temp_pl and SonoffSnzb02._decode_humi_pl
  - 