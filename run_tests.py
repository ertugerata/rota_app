import sys
from unittest.mock import MagicMock

# Mock pandas and other potentially missing libraries
sys.modules['pandas'] = MagicMock()
sys.modules['openpyxl'] = MagicMock()
sys.modules['requests'] = MagicMock()

import unittest
import test_app

if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromModule(test_app)
    unittest.TextTestRunner(verbosity=2).run(suite)
