
#!/usr/local/bin/python3
# coding=utf-8

from abc import ABC, abstractmethod

import logging
import schedule
import threading

iotlib_logger = logging.getLogger(__name__)


class Singleton(type):
    """ ref : Python Cookbook Recipes for Mastering Python 3, (David Beazley, Brian K. Jones)
        Using a Metaclass to Control Instance Creation
    """
    def __init__(cls, *args, **kwargs):
        cls.__instance = None
        super().__init__(*args, **kwargs)

    def __call__(cls, *args, **kwargs):
        if cls.__instance is None:
            cls.__instance = super().__call__(*args, **kwargs)
            return cls.__instance
        else:
            return cls.__instance


class InfiniteTimer():
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
        if self._should_continue:   # Code could have been running when cancel was called.
            self.thread = threading.Timer(self.seconds, self._handle_target)
            self.thread.start()

    def start(self):
        if not self._should_continue and not self.is_running:
            self._should_continue = True
            self._start_timer()
        else:
            iotlib_logger.error(
                "Timer already running, wait if you're restarting.")

    def cancel(self):
        if self.thread is not None:
            # Just in case thread is running and cancel fails.
            self._should_continue = False
            self.thread.cancel()
        else:
            iotlib_logger.error(
                "Timer never started or failed to initialize.")


class Trigger(ABC):

    def __init__(self, name: str):
        self._name = name
        self._registered_list = []

    def registers(self, device):
        self._registered_list.append(device)

    def __repr__(self):
        _sep = ''
        _res = ''
        for _attr, _val in self.__dict__.items():
            _res += f'{_sep}{_attr} : {_val}'
            _sep = ' | '
        return f'{self.__class__.__name__} ({self._name})'


class Timer(Trigger):
    def __init__(self, name: str, every: int):
        super().__init__(name)
        self._timer = InfiniteTimer(every, self._handle_switches)
        self._timer.start()

    @abstractmethod
    def _handle_switches(self):
        raise NotImplementedError


class Scheduler(Trigger):
    def __init__(self, name: str, at: str):
        super().__init__(name)
        self._schedule = schedule.every().day.at(at).do(self._handle_switches)

    @abstractmethod
    def _handle_switches(self):
        raise NotImplementedError
