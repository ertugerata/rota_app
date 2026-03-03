import unittest
import test_app

if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromModule(test_app)
    unittest.TextTestRunner(verbosity=2).run(suite)
