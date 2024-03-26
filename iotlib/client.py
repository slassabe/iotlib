#!/usr/local/bin/python3
# coding=utf-8

"""
This module provides the MQTTClient class for establishing MQTT connections.

Key features:
- Secure connections via TLS.
- Username/password authentication.
- Event handling for connect, disconnect, message receipt, and subscribe.
- Custom handler support for these events.

Example usage:

    def _on_message_cb(client, userdata, message):
        print(f"Received message: {message.payload.decode('utf-8')}")
    def _on_connect_cb(client, userdata, flags, rc, properties):
        print(f"Connected with result code {rc}")
        client.subscribe("my_topic")
    client = MQTTClient(client_id="my_client", hostname="localhost")
    client.message_callback_add("my_topic", _on_message_cb)
    client.connect_handler_add(self._on_connect_cb)
    client.start()

Author: Serge LASSABE
Date: Creation Date
"""

import socket

from typing import Callable, Any, Optional, List
import certifi
import paho.mqtt.client as mqtt

from . import package_level_logger


class MQTTClient():
    """    A class to handle MQTT connections.

    This class provides methods to establish a connection to an MQTT server,
    handle events such as connect, disconnect, message receipt, and subscribe,
    and add custom handlers for these events.
    """

    def __init__(self,
                 client_id: str,
                 hostname: str = "127.0.0.1",
                 port: int = 1883,
                 user_name: Optional[str] = None,
                 user_pwd: Optional[str] = None,
                 keepalive: int = 60,
                 tls: bool = False,
                 clean_start: bool = False,
                 ) -> None:
        """
        Initializes a new instance of the `Client` class.

        Args:
            client_id (str): The unique identifier for the client.
            hostname (str, optional): The hostname or IP address of the MQTT broker. Defaults to "127.0.0.1".
            port (int, optional): The port number of the MQTT broker. Defaults to 1883.
            user_name (str, optional): The username for authentication. Defaults to None.
            user_pwd (str, optional): The password for authentication. Defaults to None.
            keepalive (int, optional): The keepalive interval in seconds. Defaults to 60.
            tls (bool, optional): Specifies whether to use TLS for secure connection. Defaults to False.
            clean_start (bool, optional): Specifies whether to start with a clean session. Defaults to False.
        """
        self.hostname: str = hostname
        self.port: int = port
        self.user_name: Optional[str] = user_name
        self.user_pwd: Optional[str] = user_pwd
        self.keepalive: int = keepalive
        self.tls: bool = tls
        self.clean_start: bool = clean_start
        #
        self._connected = False
        self._started = False
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
        self.client.enable_logger(package_level_logger)

    @property
    def connected(self) -> bool:
        """
        Returns the connection status of the client.

        Returns:
            bool: True if the client is connected, False otherwise.
        """
        return self._connected

    @property
    def started(self) -> bool:
        """
        Returns the current status of the client.

        Returns:
            bool: True if the client has started, False otherwise.
        """
        return self._started

    def __str__(self) -> str:
        return f'<{self.__class__.__name__} "{self.client._client_id}">'

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__} obj.  "{self.client._client_id}" | "{self.hostname}:{self.port}">'

    def start(self, properties: Optional[mqtt.Properties] = None) -> mqtt.MQTTErrorCode:
        """Starts the client MQTT network loop.

        Connects the client if not already connected, starts the network loop

        Returns:
            mqtt.MQTTErrorCode: The result of calling client.loop_start().

        Raises:
            RuntimeError: If loop_stop fails.
        """
        try:
            _rc = self.connect(properties=properties)
            if self.client.loop_start() != mqtt.MQTTErrorCode.MQTT_ERR_SUCCESS:
                package_level_logger.error('[%s] loop_start failed : %s',
                                           self,
                                           mqtt.error_string(mqtt.MQTTErrorCode))
                raise RuntimeError('loop_start failed')
            self._started = True
            return _rc
        except ConnectionRefusedError as exp:
            package_level_logger.fatal('[%s] cannot connect host %s',
                                       exp, self.hostname)
            raise RuntimeError('[%s] connection refused') from exp

    def stop(self) -> mqtt.MQTTErrorCode:
        """Stops the client MQTT connection. 

        Stops the async loop if it was not already running. Calls disconnect() 
        to close the client connection.

        Raises:
            RuntimeError: If loop_stop fails.
        """
        if not self._connected:
            package_level_logger.error(
                '[%s] Unable to stop disconnected client', self)
            raise RuntimeError('loop_stop failed')
        _rc = self.disconnect()
        if not self._loop_forever_used:
            if self.client.loop_stop() != mqtt.MQTTErrorCode.MQTT_ERR_SUCCESS:
                package_level_logger.error('[%s] loop_stop failed : %s',
                                           self,
                                           mqtt.error_string(mqtt.MQTTErrorCode))
                raise RuntimeError('loop_stop failed')
            self._started = False
        return _rc

    def connect(self, properties: Optional[mqtt.Properties] = None) -> mqtt.MQTTErrorCode:
        ''' Connect to a remote broker according to the init properties :
        '''
        try:
            _rc = self.client.connect(self.hostname,
                                      port=self.port,
                                      keepalive=self.keepalive,
                                      clean_start=self.clean_start,
                                      properties=properties,
                                      )
            package_level_logger.debug(
                '[%s] Connection request returns : %s', self, _rc)
            return _rc
        except socket.gaierror as exp:
            package_level_logger.fatal('[%s] cannot connect host %s',
                                       exp, self.hostname)
            raise RuntimeError('connect failed') from exp

    def _handle_on_connect(self,
                           client: mqtt.Client,
                           userdata: Any,
                           flags: mqtt.ConnectFlags,
                           reason_code: mqtt.ReasonCode,
                           properties: mqtt.Properties) -> None:
        if reason_code == 0:
            self._connected = True
        for on_connect_handler in self.on_connect_handlers:
            try:
                on_connect_handler(client, userdata, flags,
                                   reason_code, properties)
            except Exception as error:
                package_level_logger.exception(
                    "Failed handling connect %s", error)

    def connect_handler_add(self, handler: Callable) -> None:
        """Adds a connect event handler.

        Args:
            handler: The callback function to handle the connect event.
        """
        self.on_connect_handlers.append(handler)

    def disconnect(self) -> mqtt.MQTTErrorCode:
        ''' Disconnect from a remote broker.
        '''
        _rc = self.client.disconnect()
        package_level_logger.debug(
            '[%s] Disconnection request returns : %s', self, _rc)
        return _rc

    def _handle_on_disconnect(self,
                              client: mqtt.Client,
                              userdata: Any,
                              disconnect_flags: mqtt.DisconnectFlags,
                              reason_code: mqtt.ReasonCode,
                              properties: mqtt.Properties) -> None:
        ''' Define the default disconnect callback implementation. 
        '''
        self._connected = False
        for on_disconnect_handler in self.on_disconnect_handlers:
            try:
                on_disconnect_handler(client,
                                      userdata,
                                      disconnect_flags,
                                      reason_code,
                                      properties)
            except Exception as error:
                package_level_logger.exception(
                    "Failed handling disconnect %s", error)

    def disconnect_handler_add(self, handler: Callable) -> None:
        """Adds a disconnect event handler.

        Args:
            handler: The callback function to handle the disconnect event.
        """
        self.on_disconnect_handlers.append(handler)

    def _handle_on_message(self, client: mqtt.Client,
                           userdata: Any,
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
                package_level_logger.exception("Exception occured : %s", error)

    def default_message_callback_add(self, callback: Callable) -> None:
        """
        Adds a callback function to the list of default message callbacks.

        Parameters:
        - callback (Callable): The callback function to be added.

        Returns:
        - None
        """
        self._default_message_callbacks.append(callback)

    def message_callback_add(self, topic: str, callback: Callable) -> None:
        """
        Adds a callback function for a specific topic.

        Args:
            topic (str): The topic to add the callback for.
            callback (Callable): The callback function to be executed when a message is received on the specified topic.

        Returns:
            None
        """
        self.client.message_callback_add(topic, callback)

    def subscribe(self, topic, **kwargs):
        ''' Subscribes to the specified topic. '''
        return self.client.subscribe(topic, **kwargs)

    def _handle_on_subscribe(self,
                             client: mqtt.Client,
                             userdata: Any,
                             mid: int,
                             reason_code_list: List[mqtt.ReasonCode],
                             properties: mqtt.Properties) -> None:
        for on_subscribe_handler in self.on_subscribe_handlers:
            try:
                on_subscribe_handler(client, userdata, mid,
                                     reason_code_list, properties)
            except Exception as error:
                package_level_logger.exception(
                    "Failed handling subscribe %s", error)

    def subscribe_handler_add(self, handler: Callable):
        """
        Adds a handler function to the list of subscribe event handlers.

        Args:
            handler (Callable): The handler function to be added.

        Returns:
            None
        """
        self.on_subscribe_handlers.append(handler)

    def publish(self, topic, payload, **kwargs):
        ''' Publish a message on a topic. '''
        package_level_logger.debug(
            'Publish on topic : %s - payload : %s', topic, payload)
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
        """
        Set the Last Will and Testament (LWT) message for the client.

        Args:
            topic (str): The topic to publish the LWT message to.
            payload (str): The payload of the LWT message.
            qos (int, optional): The quality of service level for the LWT message. Defaults to 1.
            retain (bool, optional): Whether the LWT message should be retained. Defaults to False.

        Returns:
            bool: True if the LWT message was successfully set, False otherwise.
        """
        return self.client.will_set(topic,
                                    payload=payload,
                                    qos=qos,
                                    retain=retain)
