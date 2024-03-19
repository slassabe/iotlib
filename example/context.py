# -*- coding: utf-8 -*-

import sys, os, inspect
from pathlib import Path

class Loader():
    '''https://stackoverflow.com/questions/17211078/how-to-temporarily-modify-sys-path-in-python'''
    def __init__(self):
        self.path = str(Path(__file__).parent.parent.resolve())

    def __enter__(self):
        sys.path.insert(0, self.path)

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            sys.path.remove(self.path)
        except ValueError:
            pass


