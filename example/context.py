# -*- coding: utf-8 -*-

import sys, os, inspect
from pathlib import Path

class add_path():
    '''https://stackoverflow.com/questions/17211078/how-to-temporarily-modify-sys-path-in-python'''
    def __init__(self, path):
        print(path)
        self.path = path

    def __enter__(self):
        sys.path.insert(0, self.path)
        print(f'sys.path : {sys.path}')

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            sys.path.remove(self.path)
        except ValueError:
            pass

with add_path(os.path.join(Path(__file__).parent.parent, "src")):

    from iotlib.client import AsyncClientBase


