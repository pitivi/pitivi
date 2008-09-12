import unittest
import pitivi
from pitivi.ui.util import ProxyItem
import goocanvas

class TestProxy(unittest.TestCase):
    """
    Tests that the proxy object functions propertyly
    """

    def setUp(self):
        self.r = goocanas.Rect()
        self.p = ProxyItem(delegate=r)

    def tearDown(self):
        self.r = None
        self.p = None

    def testDelegation(self):
        self.p.set_delegate_property("x", 100)
        self.p.set_delegate_property("y", 100)
        self.assertEquals(r.x, p.x)
        self.assertEquals(r.y, p.y)
        self.assertEquals(r.x, 100)
        self.assertEquals(r.y, 200)

    def testDefault(self):
        self.p.props.x = 100
        self.p.props.y = 200
        self.assertEquals(r.x, p.x)
        self.assertEquals(r.y, p.y)
        self.assertEquals(r.x, 100)
        self.assertEquals(r.y, 200)

    def testOverrides(self):
        def x_prop_handler(value):
            self.assertEquals(value, 100)
        def y_prop_handler(value):
            self.assertEquals(value, 200)
        p.set_property_handler("x", x_prop_handler)
        p.set_property_handler("y", y_prop_handler)
        p.props.x = 100
        p.prpos.y = 200
        assertNotEqual(p.props.x, 100)
        assertNotEqual(p.props.y, 200)

if __name__ == "__main__":
    unittest.main()
