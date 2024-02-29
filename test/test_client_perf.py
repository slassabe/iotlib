#!/usr/local/bin/python3
# coding=utf-8

"""Client test

$ source .venv/bin/activate
$ python -m unittest test.test_client_perf
"""
import unittest
import time
from iotlib.client import MQTTClientBase

from .helper import log_it, logger, get_broker_name


class PerfMeter:
    MAX_LOOP = 1000000
    def __init__(self, client):
        self.client = client
        self.topic = "TEST_A2IOT/client_perf"
        self.nb_loop = None

    def prologue(self):
        self.client.subscribe(self.topic)
        self.client.message_callback_add(self.topic, self.on_message_increment)
        self.client.connect_handler_add(self._on_connect_cb)
        self.client.disconnect_handler_add(self._on_disconnect_cb)
        self.client.subscribe_handler_add(self._on_subscribe_cb)
        self.client.start()

    def on_message_increment(self, client, userdata, message):
        payload = message.payload.decode("utf-8")
        logger.debug("Message received on topic '%s': %s",
                     message.topic, payload)
        self.nb_loop = int(payload)
        if self.nb_loop > self.MAX_LOOP:
            self.client.stop()
            raise RuntimeError('Max loop exceeded')
        else:
            client.publish(message.topic, f"{self.nb_loop + 1}")

    def _on_connect_cb(self, client, userdata, flags, rc, properties) -> None:
        logger.debug('Connected -> now subscribe to %s', self.topic)
        self.client.subscribe(self.topic, qos=1)

    def _on_disconnect_cb(self, client, userdata, disconnect_flags, reason_code, properties) -> None:
        logger.debug('Disconnected with reason_code : %s', reason_code)

    def _on_subscribe_cb(self, client, userdata, mid, reason_code_list, properties) -> None:
        logger.debug('Subscribed -> now publish on %s', self.topic)
        self.client.publish(self.topic, "0")

    def launch(self):
        TEST_DURATION = 10 # sec.

        self.nb_loop = 0
        self.prologue()

        _exc_start = time.perf_counter()
        _process_start = time.process_time_ns()
        time.sleep(TEST_DURATION)
        # DONT WORK: self.client.loop_forever()
        _process_end = time.process_time_ns()
        _exc_end = time.perf_counter()
        _exec_delta = _exc_end - _exc_start
        _process_delta = (_process_end - _process_start) / 1000000  # millisec.
        _nb_message = self.nb_loop
        logger.warning(f"MQTT brocker : {get_broker_name()} - "
                    f"{_nb_message} loops in {_exec_delta:.2f}s"
                    f" -> {_nb_message / (_exec_delta):.2f} messages/s"
                    f" - {_process_delta:.2f} ms")
        return self.nb_loop


class TestMQTTClient(unittest.TestCase):
    target = get_broker_name()

    def test_perf(self):
        log_it(f"Testing launch to {self.target}")
        perf = PerfMeter(MQTTClientBase('TestPerf', self.target))
        nb_loop = perf.launch()
        self.assertTrue(nb_loop > 0)


if __name__ == "__main__":
    unittest.main()
