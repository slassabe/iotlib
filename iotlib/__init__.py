__version__ = "2.0.0"

import logging

package_level_logger = logging.getLogger('iotlib')
print(f'{__name__} : version {__version__}')