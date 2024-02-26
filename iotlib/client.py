#!/usr/local/bin/python3
# coding=utf-8

"""Module for MQTT communication.

This module provides a MQTTClient class for publishing messages to and subscribing to topics on an MQTT broker.

Key features:

- Connects to broker based on configuration settings
- Supports TLS encryption and authentication
- Automatic reconnect on connection failure
- Publish messages with various QoS levels
- Subscribe to topics and process messages in callbacks
- Logging of connection state changes and errors

Typical usage:

- Create MQTTClient instance, passing client ID
- client.start()
- client.subscribe(self.topic)
- client.message_callback_add(self.topic, self.on_message_cb)
- client.connect_handler_add(self._on_connect_cb)
- client.subscribe_handler_add(self._on_subscribe_cb)
- client.disconnect_handler_add(self._on_disconnect_cb)
- loop
- client.stop()

"""

import socket

from collections.abc import Callable  
import certifi
import paho.mqtt.client as mqtt

from . import package_level_logger
from iotlib.config import MQTTConfig

class MQTTClientBase():
    _logger = package_level_logger

    def __init__(self,
                 client_id,
                 hostname="127.0.0.1",
                 port=1883,
                 user_name: str = None,
                 user_pwd: str = None,
                 keepalive=60,
                 tls=False,
                 clean_start=False,
                 ):
        self.hostname = hostname
        self.port = port
        self.user_name = user_name
        self.user_pwd = user_pwd
        self.keepalive = keepalive
        self.tls = tls
        self.clean_start = clean_start
        #
        self.connected = False
        #
        self._loop_forever_used = False

        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                                  client_id=client_id,
                                  userdata=None,
                                  protocol=mqtt.MQTTv5,
                                  transport="tcp")

        if self.tls:
            # enable TLS for secure connection
            self.client.tls_set(certifi.where())
        self.client.username_pw_set(self.user_name,
                                    self.user_pwd)

        self.client.on_connect = self._handle_on_connect
        self.client.on_disconnect = self._handle_on_disconnect
        self.client.on_message = self._handle_on_message
        self.client.on_subscribe = self._handle_on_subscribe

        self.on_connect_handlers: List[Callable] = []
        self.on_disconnect_handlers: List[Callable] = []
        self._default_message_callbacks: List[Callable] = []
        self.on_subscribe_handlers: List[Callable] = []

    def __str__(self):
        #return f'<{self.__class__.__name__} object "{self.hostname}:{self.port}">'
        return f'<{self.__class__.__name__} obj.">'

    def start(self, properties: mqtt.Properties | None=None) -> mqtt.MQTTErrorCode:
        """Starts the client MQTT network loop.

        Connects the client if not already connected, starts the network loop

        Returns:
            mqtt.MQTTErrorCode: The result of calling client.loop_start().
        """
        if self.client.loop_start() != mqtt.MQTTErrorCode.MQTT_ERR_SUCCESS:
            self._logger.error('[%s] loop_start failed', self)
            raise RuntimeError('loop_start failed')
        _rc = self.connect(properties=properties)
        return _rc

    def stop(self) -> mqtt.MQTTErrorCode:
        """Stops the client MQTT connection. 

        Stops the async loop if it was not already running. Calls disconnect() 
        to close the client connection.

        Raises:
            RuntimeError: If loop_stop fails.
        """
        _rc = self.disconnect()
        if not self._loop_forever_used:
            if self.client.loop_stop() != mqtt.MQTTErrorCode.MQTT_ERR_SUCCESS:
                self._logger.error('[%s] loop_stop failed', self)
                raise RuntimeError('loop_stop failed')
        return _rc

    def connect(self, properties: mqtt.Properties | None=None) -> mqtt.MQTTErrorCode:
        ''' Connect to a remote broker according to the init properties :
        '''
        try:
            _rc = self.client.connect(self.hostname,
                                      port=self.port,
                                      keepalive=self.keepalive,
                                      clean_start=self.clean_start,
                                      properties=properties
                                      )
            self._logger.debug('Connection request returns : %s', _rc)
            return _rc
        except socket.gaierror as exp:
            self._logger.fatal('[%s] cannot connect host %s',
                               exp, self.hostname)
            raise RuntimeError('connect failed')

    def _handle_on_connect(self, client, userdata, flags, reason_code, properties) -> None:
        if reason_code == 0:
            self._logger.info('Connection accepted -> launch connect handlers')
            self.connected = True
            for on_connect_handler in self.on_connect_handlers:
                try:
                    on_connect_handler(client, userdata, flags,
                                       reason_code, properties)
                except Exception as error:
                    self._logger.exception("Failed handling connect %s", error)
        else:
            self._logger.error('[%s] connection refused - reason : %s',
                               self,
                               mqtt.connack_string(reason_code))

    def connect_handler_add(self, handler):
        self.on_connect_handlers.append(handler)

    def disconnect(self) -> mqtt.MQTTErrorCode:
        ''' Disconnect from a remote broker.
        '''
        _rc = self.client.disconnect()
        self._logger.debug('Disconnection request returns : %s', _rc)
        return _rc

    def _handle_on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties) -> None:
        ''' Define the default disconnect callback implementation. 
        '''
        if reason_code == 0:
            self._logger.warning('Disconnection occures - rc : %s -> stop loop',
                                 reason_code)
            self.connected = False
            self.client.loop_stop()
            for on_disconnect_handler in self.on_disconnect_handlers:
                try:
                    on_disconnect_handler(client,
                                          userdata,
                                          disconnect_flags,
                                          reason_code,
                                          properties)
                except Exception as error:
                    self._logger.exception(
                        "Failed handling disconnect %s", error)
        else:
            self._logger.warning('[%s] disconnection not required with rc "%s"',
                                 self,
                                 reason_code)

    def disconnect_handler_add(self, handler):
        self.on_disconnect_handlers.append(handler)

    def _handle_on_message(self, client: mqtt.Client,
                           userdata: any,
                           message: mqtt.MQTTMessage) -> None:
        ''' Define the message received callback implementation.

        client:     the client instance for this callback
        userdata:   the private user data as set in Client() or userdata_set()
        message:    the received message with members : topic, payload, qos, retain
        '''
        for on_message_handler in self._default_message_callbacks:
            try:
                on_message_handler(client, userdata, message)
            except Exception as error:
                self._logger.exception("Exception occured : %s", error)

    def default_message_callback_add(self, callback: Callable) -> None:
        self._default_message_callbacks.append(callback)

    def message_callback_add(self, topic: str, callback: Callable) -> None:
        self.client.message_callback_add(topic, callback)

    def subscribe(self, topic, **kwargs):
        ''' Subscribes to the specified topic. '''
        self._logger.debug('Subscribes to topic "%s"', topic)
        return self.client.subscribe(topic, **kwargs)

    def _handle_on_subscribe(self, client, userdata, mid, reason_code_list, properties):
        self._logger.info('Subscribe request accepted with reason code %s',
                          reason_code_list)
        for on_subscribe_handler in self.on_subscribe_handlers:
            try:
                on_subscribe_handler(client, userdata, mid,
                                     reason_code_list, properties)
            except Exception as error:
                self._logger.exception("Failed handling subscribe %s", error)

    def subscribe_handler_add(self, handler):
        self.on_subscribe_handlers.append(handler)

    def publish(self, topic, payload, **kwargs):
        ''' Publish a message on a topic. '''
        self._logger.debug('Publish on topic : %s - payload : %s', topic, payload)
        return self.client.publish(topic, payload, **kwargs)

    def loop_forever(self) -> mqtt.MQTTErrorCode:
        ''' Start a new thread to run the network loop. '''
        self._loop_forever_used = True
        return self.client.loop_forever()

    def will_set(self,
                 topic: str,
                 payload: str,
                 qos: int = 1,
                 retain: bool = False):
        return self.client.will_set(topic,
                                    payload=payload,
                                    qos=qos,
                                    retain=retain)


class MQTTClient(MQTTClientBase):
    """Initializes an MQTTClient instance with configured parameters.
    """
    def __init__(self, client_id):
        super().__init__(client_id,
                         MQTTConfig().hostname,
                         MQTTConfig().port,
                         MQTTConfig().user_name,
                         MQTTConfig().user_pwd,
                         MQTTConfig().keepalive,
                         MQTTConfig().tls,
                         MQTTConfig().clean_start,
                         )
