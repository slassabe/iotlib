#!/usr/local/bin/python3
# coding=utf-8

import logging
import threading
from typing import Any, Type, TypeVar

iotlib_logger = logging.getLogger("iotlib")

T = TypeVar("T")


class Singleton(type):
    """ref : Python Cookbook Recipes for Mastering Python 3, (David Beazley, Brian K. Jones)
    Using a Metaclass to Control Instance Creation
    """

    def __init__(cls: Type[T], *args, **kwargs) -> None:
        cls.__instance = None
        super().__init__(*args, **kwargs)

    def __call__(cls: Type[T], *args: Any, **kwargs: Any) -> T:
        if cls.__instance is None:
            cls.__instance = super().__call__(*args, **kwargs)
            return cls.__instance
        else:
            return cls.__instance


class InfiniteTimer:
    """A Timer class that does not stop, unless you want it to.
    https://stackoverflow.com/questions/12435211/threading-timer-repeat-function-every-n-seconds
    """

    def __init__(self, seconds, target):
        self._should_continue = False
        self.is_running = False
        self.seconds = seconds
        self.target = target
        self.thread = None

    def _handle_target(self):
        self.is_running = True
        self.target()
        self.is_running = False
        self._start_timer()

    def _start_timer(self):
        if (
            self._should_continue
        ):  # Code could have been running when cancel was called.
            self.thread = threading.Timer(self.seconds, self._handle_target)
            self.thread.start()

    def start(self):
        if not self._should_continue and not self.is_running:
            self._should_continue = True
            self._start_timer()
        else:
            iotlib_logger.error("Timer already running, wait if you're restarting.")

    def cancel(self):
        """Cancels the timer if it is running."""
        if self.thread is not None:
            # Just in case thread is running and cancel fails.
            self._should_continue = False
            self.thread.cancel()
        else:
            iotlib_logger.error("Timer never started or failed to initialize.")
