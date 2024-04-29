#!/usr/local/bin/python3
# coding=utf-8

"""
This module contains the MQTTClient class which implements the IMQTTService interface.

The MQTTClient class is responsible for handling MQTT-specific operations. It uses the 
paho.mqtt.client library for MQTT operations and provides methods for connecting, disconnecting, 
and handling MQTT events.

"""

import socket
import dataclasses

from typing import Callable, Any, Optional, List
import certifi
import paho.mqtt.client as mqtt

from iotlib.abstracts import IMQTTService
from iotlib.utils import iotlib_logger


@dataclasses.dataclass
class MQTTClient(IMQTTService):
    """
    MQTTClient is a class that implements the IMQTTService interface.

    This class is responsible for handling MQTT-specific operations. It uses the paho.mqtt.client 
    library for MQTT operations and provides methods for connecting, disconnecting, and handling 
    MQTT events.

    :ivar client: The MQTT client instance.
    :vartype client: mqtt.Client
    :ivar host: The MQTT broker host.
    :vartype host: str
    :ivar port: The MQTT broker port.
    :vartype port: int
    :ivar keepalive: The keepalive timeout value for the client.
    :vartype keepalive: int
    """
    client_id: str
    hostname: str = "127.0.0.1"
    port: int = 1883
    user_name: Optional[str] = None
    user_pwd: Optional[str] = None
    keepalive: int = 60
    tls: bool = False
    clean_start: bool = False

    def __post_init__(self) -> None:
        """
        Initializes a new instance of the `Client` class.
        """
        if not isinstance(self.client_id, str):
            raise TypeError(
                f"Expected client_id to be a str, got {type(self.client_id).__name__}")
        if not isinstance(self.hostname, str):
            raise TypeError(
                f"Expected hostname to be a str, got {type(self.hostname).__name__}")
        if not isinstance(self.port, int):
            raise TypeError(
                f"Expected port to be an int, got {type(self.port).__name__}")
        if self.user_name is not None and not isinstance(self.user_name, str):
            raise TypeError(
                f"Expected user_name to be a str or None, got {type(self.user_name).__name__}")
        if self.user_pwd is not None and not isinstance(self.user_pwd, str):
            raise TypeError(
                f"Expected user_pwd to be a str or None, got {type(self.user_pwd).__name__}")
        if not isinstance(self.keepalive, int):
            raise TypeError(
                f"Expected keepalive to be an int, got {type(self.keepalive).__name__}")
        if not isinstance(self.tls, bool):
            raise TypeError(
                f"Expected tls to be a bool, got {type(self.tls).__name__}")
        if not isinstance(self.clean_start, bool):
            raise TypeError(
                f"Expected clean_start to be a bool, got {type(self.clean_start).__name__}")

        self._connected = False
        self._started = False
        self._loop_forever_used = False

        self._mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                                        client_id=self.client_id,
                                        userdata=None,
                                        protocol=mqtt.MQTTv5,
                                        transport="tcp")

        if self.tls:
            # enable TLS for secure connection
            self._mqtt_client.tls_set(certifi.where())
        self._mqtt_client.username_pw_set(self.user_name,
                                          self.user_pwd)

        self._mqtt_client.on_connect = self._handle_on_connect
        self._mqtt_client.on_disconnect = self._handle_on_disconnect

        self.on_connect_handlers: List[Callable[..., None]] = []
        self.on_disconnect_handlers: List[Callable[..., None]] = []
        self._mqtt_client.enable_logger(iotlib_logger)

    @property
    def mqtt_client(self) -> mqtt.Client:
        # Implement IMQTTService interface
        return self._mqtt_client

    @property
    def connected(self) -> bool:
        """
        Returns the connection status of the client.

        :return: True if the client is connected, False otherwise.
        :rtype: bool
        """
        return self._connected

    @property
    def started(self) -> bool:
        """
        Returns the current status of the client.

        :return: True if the client has started, False otherwise.
        :rtype: bool
        """
        return self._started

    def __str__(self) -> str:
        return f'<{self.__class__.__name__} "{self._mqtt_client._client_id}">'

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__} obj.  "{self._mqtt_client._client_id}" | "{self.hostname}:{self.port}">'

    def loop_forever(self) -> mqtt.MQTTErrorCode:
        ''' Start a new thread to run the network loop. '''
        self._loop_forever_used = True
        return self._mqtt_client.loop_forever()

    def start(self, properties: Optional[mqtt.Properties] = None) -> mqtt.MQTTErrorCode:
        """
        Starts the client MQTT network loop.

        Connects the client if not already connected, starts the network loop

        :param properties: The properties to be used for the CONNECT message.
        :type properties: Optional[mqtt.Properties]
        :return: The result of calling client.loop_start().
        :rtype: mqtt.MQTTErrorCode
        :raises RuntimeError: If loop_start fails or connection is refused.
        """
        try:
            _rc = self.connect(properties=properties)
            if self._mqtt_client.loop_start() != mqtt.MQTTErrorCode.MQTT_ERR_SUCCESS:
                iotlib_logger.error('[%s] loop_start failed : %s',
                                    self,
                                    mqtt.error_string(mqtt.MQTTErrorCode))
                raise RuntimeError('loop_start failed')
            self._started = True
            return _rc
        except ConnectionRefusedError as exp:
            iotlib_logger.fatal('[%s] cannot connect host %s',
                                exp, self.hostname)
            raise RuntimeError('[%s] connection refused') from exp

    def stop(self) -> mqtt.MQTTErrorCode:
        """
        Stops the client MQTT connection.

        Stops the async loop if it was not already running. Calls disconnect() 
        to close the client connection.

        :return: The result of calling disconnect().
        :rtype: mqtt.MQTTErrorCode
        :raises RuntimeError: If loop_stop fails.
        """
        if not self._connected:
            iotlib_logger.error(
                '[%s] Unable to stop disconnected client', self)
            raise RuntimeError('loop_stop failed')
        _rc = self.disconnect()
        if not self._loop_forever_used:
            if self._mqtt_client.loop_stop() != mqtt.MQTTErrorCode.MQTT_ERR_SUCCESS:
                iotlib_logger.error('[%s] loop_stop failed : %s',
                                    self,
                                    mqtt.error_string(mqtt.MQTTErrorCode))
                raise RuntimeError('loop_stop failed')
            self._started = False
        return _rc

    def connect(self, properties: Optional[mqtt.Properties] = None) -> mqtt.MQTTErrorCode:
        # Implement IMQTTService interface
        try:
            _rc = self._mqtt_client.connect(self.hostname,
                                            port=self.port,
                                            keepalive=self.keepalive,
                                            clean_start=self.clean_start,
                                            properties=properties,
                                            )
            iotlib_logger.debug('[%s] Connection request returns : %s',
                                self, _rc)
            return _rc
        except socket.gaierror as exp:
            iotlib_logger.fatal('[%s] cannot connect host %s',
                                exp, self.hostname)
            raise RuntimeError('connect failed') from exp

    def _handle_on_connect(self,
                           client: mqtt.Client,
                           userdata: Any,
                           flags: mqtt.ConnectFlags,
                           reason_code: mqtt.ReasonCode,
                           properties: mqtt.Properties) -> None:
        ''' Define the default connect callback implementation. 
        '''
        if reason_code == 0:
            self._connected = True
        for on_connect_handler in self.on_connect_handlers:
            try:
                on_connect_handler(client, userdata, flags,
                                   reason_code, properties)
            except Exception as error:
                iotlib_logger.exception(
                    "Failed handling connect %s", error)

    def connect_handler_add(self, handler: Callable) -> None:
        # Implement IMQTTService interface
        self.on_connect_handlers.append(handler)

    def disconnect(self) -> mqtt.MQTTErrorCode:
        # Implement IMQTTService interface
        _rc = self._mqtt_client.disconnect()
        iotlib_logger.debug('[%s] Disconnection request returns : %s',
                            self, _rc)
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
                iotlib_logger.exception(
                    "Failed handling disconnect %s", error)

    def disconnect_handler_add(self, handler: Callable) -> None:
        # Implement IMQTTService interface
        self.on_disconnect_handlers.append(handler)

class MQTTClientHelper(MQTTClient):
    """
    This class provides additional helper methods for MQTT operations, not directly related to the 
    IMQTTService interface.
    Could evolve to a more generic class in the future.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._mqtt_client.on_message = self._handle_on_message
        self._mqtt_client.on_subscribe = self._handle_on_subscribe

        self._default_message_callbacks: List[Callable] = []
        self.on_subscribe_handlers: List[Callable] = []

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
                iotlib_logger.exception("Exception occured : %s", error)

    def default_message_callback_add(self, callback: Callable) -> None:
        """
        Adds a callback function to the list of default message callbacks.

        Parameters:
        - callback (Callable): The callback function to be added.

        Returns:
        - None
        """
        self._default_message_callbacks.append(callback)

    def subscribe(self, topic, **kwargs):
        ''' Subscribes to the specified topic. '''
        return self._mqtt_client.subscribe(topic, **kwargs)

    def publish(self, topic, payload, **kwargs):
        ''' Publish a message on a topic. '''
        iotlib_logger.debug(
            'Publish on topic : %s - payload : %s', topic, payload)
        return self._mqtt_client.publish(topic, payload, **kwargs)

    def _handle_on_subscribe(self,
                             client: mqtt.Client,
                             userdata: Any,
                             mid: int,
                             reason_code_list: List[mqtt.ReasonCode],
                             properties: mqtt.Properties) -> None:
        ''' Define the default subscribtion callback implementation. 
        '''
        for reason_code in reason_code_list:
            if reason_code.is_failure:
                iotlib_logger.warning('[%s] subscribe refused - reason code : %s',
                                    self,
                                    reason_code)
                return
        iotlib_logger.debug('[%s] subscribe accepted', client)
        for on_subscribe_handler in self.on_subscribe_handlers:
            try:
                on_subscribe_handler(client, userdata, mid,
                                    reason_code_list, properties)
            except Exception as error:
                iotlib_logger.exception(
                    "Failed handling subscribe %s", error)

    def subscribe_handler_add(self, handler: Callable):
        """
        Adds a subscribe handler.

        Subscribe handlers are called when a subscription
        is received from the MQTT broker.

        :param handler: The callback function to handle the subscribe event.
        :type handler: Callable
        :return: None
        """
        self.on_subscribe_handlers.append(handler)

