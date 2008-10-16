import unittest
import pitivi
from pitivi.pitivi import Pitivi

class BasicTest(unittest.TestCase):
    """
    Basic test to create the proper creation of the Pitivi object
    """

    def testBasic(self):
        ptv = pitivi.pitivi.Pitivi()
        # was the pitivi object created
        self.assert_(ptv)

        # were the contents of pitivi properly created
        self.assert_(ptv.playground)
        self.assert_(ptv.current)
        self.assert_(ptv.effects)

        # was the unique instance object properly set
        self.assertEquals(pitivi.instance.PiTiVi, ptv)

        # close pitivi
        ptv.shutdown()

        # make sure the instance has been unset
        self.assertEquals(pitivi.instance.PiTiVi, None)

if __name__ == "__main__":
    unittest.main()
