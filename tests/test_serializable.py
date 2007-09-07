import unittest
import common
from pitivi.serializable import Serializable, to_object_from_data_type
import weakref
import gobject
import gst
import gc

class TestSerializableObject(gobject.GObject, Serializable):
    __data_type__ = "test-serializable-object"

    __objects__ = weakref.WeakValueDictionary()

    def __init__(self, int1=0, string2=None):
        gobject.GObject.__init__(self)
        self.int1 = int1
        self.string2 = string2
        TestSerializableObject.__objects__[int1] = self

    def toDataFormat(self):
        ret = Serializable.toDataFormat(self)
        ret["int1"] = self.int1
        ret["string2"] = self.string2
        return ret

    def fromDataFormat(self, data):
        Serializable.fromDataFormat(self, data)
        self.int1 = data["int1"]
        self.string2 = data["string2"]

gobject.type_register(TestSerializableObject)

class TestSerializedObjects(unittest.TestCase):

    def testNonSubclassedObject(self):
        obj = Serializable()

        #serialization
        data = obj.toDataFormat()
        self.assertEquals(data, { "datatype" : "serializable"})

        #deserialization
        obj2 = to_object_from_data_type(data)
        self.assertTrue(isinstance(obj2, Serializable))

    def testSubclassedObject(self):
        self.assertEquals(len(TestSerializableObject.__objects__), 0)
        obj = TestSerializableObject(5, "hello")
        self.assertEquals(len(TestSerializableObject.__objects__), 1)
        del obj
        gc.collect()
        self.assertEquals(len(TestSerializableObject.__objects__), 0)
        obj = TestSerializableObject(5, "hello")

        #serialization
        data = obj.toDataFormat()
        self.assertEquals(data, { "datatype" : TestSerializableObject.__data_type__,
                                  "int1" : 5,
                                  "string2" : "hello" })

        #deserialization
        obj2 = to_object_from_data_type(data)
        self.assertTrue(isinstance(obj2, TestSerializableObject))
        self.assertEquals(obj.int1, obj2.int1)
        self.assertEquals(obj.string2, obj2.string2)
