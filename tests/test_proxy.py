import unittest
import pitivi
from pitivi.ui.util import ProxyItem
import goocanvas

class TestProxy(unittest.TestCase):
    """
    Tests that the proxy object functions propertyly
    """

    def setUp(self):
        self.r = goocanvas.Rect()
        self.p = ProxyItem(delegate=self.r)

    def tearDown(self):
        self.r = None
        self.p = None

    def testDelegation(self):
        self.p.set_delegate_property("x", 100.0)
        self.p.set_delegate_property("y", 200.0)
        self.assertEquals(self.r.props.x, self.p.props.x)
        self.assertEquals(self.r.props.y, self.p.props.y)
        self.assertEquals(self.r.props.x, 100.0)
        self.assertEquals(self.r.props.y, 200.0)

    def testDefault(self):
        self.p.props.x = 100
        self.p.props.y = 200
        self.assertEquals(self.r.props.x, self.p.props.x)
        self.assertEquals(self.r.props.y, self.p.props.y)
        self.assertEquals(self.r.props.x, 100.0)
        self.assertEquals(self.r.props.y, 200.0)

    def testOverrides(self):
        self.got_x = False
        self.got_y = False
        def x_prop_handler(value):
            self.got_x = True
            self.assertEquals(value, 100.0)
        def y_prop_handler(value):
            self.got_y = True
            self.assertEquals(value, 200.0)
        self.p.set_property_handler("x", x_prop_handler)
        self.p.set_property_handler("y", y_prop_handler)
        self.p.props.x = 100.0
        self.p.props.y = 200.0
        self.assertTrue(self.got_x)
        self.assertTrue(self.got_y)
        self.assertNotEqual(self.p.props.x, 100.0)
        self.assertNotEqual(self.p.props.y, 200.0)

if __name__ == "__main__":
    unittest.main()
