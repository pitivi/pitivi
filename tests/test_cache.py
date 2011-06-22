import unittest
import pitivi
from common import TestCase
from pitivi.thumbnailcache import ThumbnailCache


class CacheTest(TestCase):
    """
    Basic test to create the proper creation of the Pitivi object
    """

    def testCache(self):
        c = ThumbnailCache(size=32)
        for i in xrange(0, 64):
            c[i] = i
        assert len(c.cache) == 32
        assert not 31 in c
        assert 32 in c

        # touch the LRU item, and then add something to the queue
        # the item should still remain in the queue

        c[32]
        c[65] = 65

        assert 32 in c
        assert not 33 in c

if __name__ == "__main__":
    unittest.main()
