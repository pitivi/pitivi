import unittest
from common import TestCase
from pitivi.application import Pitivi


class BasicTest(TestCase):
    """
    Basic test to create the proper creation of the Pitivi object
    """

    def testBasic(self):
        ptv = Pitivi()
        # was the pitivi object created
        self.assert_(ptv)

        # were the contents of pitivi properly created
        self.assertEqual(ptv.current_project, None)
        self.assert_(ptv.effects)

        # close pitivi
        ptv.shutdown()

if __name__ == "__main__":
    unittest.main()
