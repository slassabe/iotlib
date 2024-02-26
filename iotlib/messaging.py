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

1. Create MQTTClient instance, passing client ID
2. Override message callback to add custom processing
3. Call connect() to connect to the broker 
4. Publish messages using publish()
5. Subscribe to topics using subscribe()

"""

from socket import gaierror
from typing import List
from collections.abc import Callable

# Non standard lib
import certifi
import paho.mqtt.client as mqtt

from . import package_level_logger
from iotlib.config import MQTTConfig


class MQTTClient():
    '''MQTT client for publishing and subscribing to a broker.

    This class encapsulates connecting to an MQTT broker and publishing/subscribing 
    to topics. It handles connecting, reconnecting, and message callbacks.

        * mqtt.Client : set protocol version V5 over tcp
        * Client.tls_set : if TLS is set
        * Client.username_pw_set : with USR and PWD
        * Client.connect : HOSTNAME, PORT, KEEPALIVE and CLEAN_START
    '''
    config = MQTTConfig()
    _logger = package_level_logger

    def __init__(self, client_id, userdata=None):
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1,
                                  client_id=client_id,
                                  userdata=userdata,
                                  protocol=mqtt.MQTTv5,
                                  transport="tcp")

        if MQTTClient.config.tls:
            # enable TLS for secure connection
            self.client.tls_set(certifi.where())
        self.client.username_pw_set(MQTTClient.config.user_name, 
                                    MQTTClient.config.user_pwd)

        self.client.on_connect = self._handle_on_connect
        self.client.on_disconnect = self._handle_on_disconnect
        self.client.on_subscribe = self._on_subscribe
        self.client.on_publish = self._on_publish

        self.client.on_message = \
            lambda client, userdata, msg: self._handle_on_message(client,
                                                           userdata,
                                                           msg.payload,
                                                           msg.topic,
                                                           msg.qos,
                                                           msg.retain,
                                                           msg.properties)
        self.on_connect_handlers: List[Callable] = []
        self.on_disconnect_handlers: List[Callable] = []
        self.on_message_handlers: List[Callable] = []

        self.listen()

    def listen(self) -> None:
        # Prepare loop then connect
        self.client.loop_start()
        self.connect()
        self._logger.debug('[%s] client ready', self)

    def __str__(self):
        return f'{self.__class__.__name__} object'

    def connect(self):
        ''' Connect to a remote broker according to the configuration file properties :

            * HOST:      is the hostname or IP address of the remote broker.
            * PORT:      is the network port of the server host to connect to.
            * KEEPALIVE: Maximum period in seconds between communications with the \
              broker. If no other messages are being exchanged, this \
              controls the rate at which the client will send ping \
              messages to the broker.
            * CLEAN_START: True, False or MQTT_CLEAN_START_FIRST_ONLY.

        '''
        try:
            self.client.connect(MQTTClient.config.hostname,
                                port=MQTTClient.config.port,
                                keepalive=MQTTClient.config.keepalive,
                                clean_start=MQTTClient.config.clean_start)
        except gaierror as exp:
            self._logger.fatal('[%s] cannot connect to host %s',
                               exp, MQTTClient.config.hostname)

    def subscribe(self, topic, **kwargs):
        ''' Subscribes to the specified topic. '''
        return self.client.subscribe(topic, **kwargs)

    def publish(self, topic, payload=None, qos=1, retain=False, properties=None):
        ''' Publish a message on a topic. '''
        return self.client.publish(topic,
                                   payload=payload,
                                   qos=qos,
                                   retain=retain,
                                   properties=properties)


    def _handle_on_connect(self, client, userdata, flags, rc, properties) -> None:
        if rc == 0:
            self._logger.info('[%s] connection accepted', self)
        else:
            self._logger.error('[%s] connection refused - reason : %s',
                               self,
                               mqtt.connack_string(rc))
            return
        for on_connect_handler in self.on_connect_handlers:
            try:
                on_connect_handler(client, userdata, flags, rc, properties)
            except Exception as error:
                self._logger.exception("Failed handling connect %s", error)

    def connect_handler_add(self, handler):
        self.on_connect_handlers.append(handler)

    def _handle_on_disconnect(self, client, userdata, rc, properties) -> None:
        ''' Define the default disconnect callback implementation. 
        '''
        if rc == 0:
            self._logger.info('[%s] disconnection occures', self)
            self.client.loop_stop()
        else:
            self._logger.warning('[%s] disconnection not required with rc "%s"',
                                 self,
                                 rc)
        for on_disconnect_handler in self.on_disconnect_handlers:
            try:
                on_disconnect_handler(client, userdata, rc, properties)
            except Exception as error:
                self._logger.exception("Failed handling disconnect %s", error)

    def disconnect_handler_add(self, handler):
        self.on_disconnect_handlers.append(handler)


    def _handle_on_message(self, client, userdata, binary_pl, topic, qos, retain, props):
        ''' Define the message received callback implementation.

        client:     the client instance for this callback
        userdata:   the private user data as set in Client() or userdata_set()
        binary_pl:  (not standard) set to msg.payload
        topic:      (not standard) set to msg.topic
        qos:        (not standard) set to msg.qos
        retain:     (not standard) set to msg.retain
        props:      (not standard) set to user msg.property 
        '''
        for on_message_handler in self.on_message_handlers:
            try:
                on_message_handler(client, userdata, binary_pl, topic, qos, retain, props)
            except Exception as error:
                self._logger.exception("Exception occured : %s", error)


    def message_handler_add(self, handler):
        self.on_message_handlers.append(handler)


    def _on_subscribe(self, client, userdata, mid, reasoncodes, props):
        ''' Define the subscribe callback implementation. '''

    def _on_publish(self, client, userdata, mid):
        ''' Define the published message callback implementation. '''

    def will_set(self,
                 topic: str,
                 payload: str,
                 qos: int = 1,
                 retain: bool = False):
        return self.client.will_set(topic,
                                    payload=payload,
                                    qos=qos,
                                    retain=retain)
