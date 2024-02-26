#!/usr/local/bin/python3
# coding=utf-8

"""Client test

$ source .venv/bin/activate
$ python -m unittest test.test_client_perf
"""
import unittest
import time
from iotlib.client import MQTTClientBase

from .utils import log_it, logger, get_broker_name

class PerfMeter:
    def __init__(self, client):
        self.client = client
        self.topic = "TEST/sync_client"
        self.max_loop = None
        self.nb_loop = None

    def prologue(self):
        self.client.start()

        self.client.subscribe(self.topic)
        self.client.message_callback_add(self.topic, self.on_message_increment)
        self.client.connect_handler_add(self._on_connect_cb)
        self.client.disconnect_handler_add(self._on_disconnect_cb)
        self.client.subscribe_handler_add(self._on_subscribe_cb)

    def on_message_increment(self, client, userdata, message):
        payload = message.payload.decode("utf-8")
        logger.debug("Message received on topic '%s': %s",
                      message.topic, payload)
        self.nb_loop = int(payload)
        if self.nb_loop > self.max_loop:
            self.client.stop()
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

    def launch(self, max_loop: int = 200):
        self.max_loop = max_loop
        self.nb_loop = 0
        self.prologue()

        _exc_start = time.perf_counter()
        _process_start = time.process_time_ns()
        while self.nb_loop < self.max_loop:
            time.sleep(1)
        # self.client.loop_forever()
        _process_end = time.process_time_ns()
        _exc_end = time.perf_counter()
        _exec_delta = _exc_end - _exc_start
        _process_delta = (_process_end - _process_start) / 1000000  # millisec.
        logger.info(f"{self.nb_loop} loops in {_exec_delta:.2f}s"
                     f" -> {self.nb_loop / (_exec_delta * 2):.2f} messages/s"
                     f" - {_process_delta:.2f} ms")
        return self.nb_loop


class TestMQTTClient(unittest.TestCase):
    target = get_broker_name()

    def test_perf(self):
        log_it(f"Testing launch to {self.target}")
        perf = PerfMeter(MQTTClientBase('TestPerf', self.target))
        nb_loop = perf.launch(max_loop=200)
        self.assertTrue(nb_loop > 0)


if __name__ == "__main__":
    unittest.main()
