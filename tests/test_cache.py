import unittest
import cairo
import tempfile
from gi.repository import Gst
import os

from urllib import unquote
from common import TestCase
import pitivi.settings as settings

from pitivi.timeline.thumbnailer import ThumbnailCache
from pitivi.utils.misc import hash_file


class ThumbnailsCacheTest(TestCase):
    """
    Basic test for thumbnails caching
    """
    def setUp(self):
        self.tmpfile = tempfile.NamedTemporaryFile()
        self.uri = unquote(Gst.uri_construct("file", self.tmpfile.name))
        self.hash = hash_file(self.tmpfile.name)

    def tearDown(self):
        del self.tmpfile
        os.remove(os.path.join(settings.xdg_cache_home(), "thumbs", self.hash))

    def testCache(self):
        c = ThumbnailCache(self.uri, size=32)

        for i in xrange(0, 64):
            c[i] = cairo.ImageSurface(cairo.FORMAT_RGB24, 10, 10)
        assert len(c.cache) == 32

        # 31 should be in the Database, but not in the memory direct cache
        assert not 31 in c.cache
        assert 31 in c
        # 32 is in both
        assert 32 in c.cache

        # touch the LRU item, and then add something to the queue
        # the item should still remain in the queue

        c[32]
        c[65] = cairo.ImageSurface(cairo.FORMAT_RGB24, 10, 10)

        assert 32 in c
        assert 33 not in c.cache


if __name__ == "__main__":
    unittest.main()
