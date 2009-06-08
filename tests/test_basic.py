import unittest
import pitivi
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
        self.assertEqual(ptv.current, None)
        self.assert_(ptv.effects)

        # was the unique instance object properly set
        self.assertEquals(pitivi.instance.PiTiVi, ptv)

        # close pitivi
        ptv.shutdown()

        # make sure the instance has been unset
        self.assertEquals(pitivi.instance.PiTiVi, None)

if __name__ == "__main__":
    unittest.main()
