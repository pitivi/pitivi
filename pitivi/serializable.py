# PiTiVi , Non-linear video editor
#
#       pitivi/serializable.py
#
# Copyright (c) 2005, Edward Hervey <bilboed@bilboed.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.


class Serializable(object):
    """An interface which all objects expected to be saved/loaded into project
    files must implement."""
    __data_type__ = "serializable"

    def toDataFormat(self):
        """
        Return the Data Format dictionnary containing serializable information for
        this object.

        All serializable objects must chain up to the parent class function before
        filling in the returned dictionnary.
        """
        return { "datatype" : self.__data_type__ }

    def fromDataFormat(self, obj):
        """
        Fill self with the information contained in the 'obj' dictionnary.

        All serializable objects must chain up to the parent class function before
        extracting their information.
        """
        if not obj["datatype"]:
            raise Exception("dictionnary doesn't contain the type information !!")
        if not obj["datatype"] == self.__data_type__:
            raise Exception("Mismatch in dictionnary data-type (%s) and class data-type (%s)" % (obj["datatype"],                                                                                                 self.__data_type__))
        return


def get_serialized_classes():
    """
    Returns a dictionnary of serialized classes.
    Mapping is type-name (string) => class
    """
    def get_valid_subclasses(cls):
        res = [(cls.__data_type__, cls)]
        for i in cls.__subclasses__():
            res.extend(get_valid_subclasses(i))
        return res
    listclasses = get_valid_subclasses(Serializable)

    # add a little check for duplicates here !
    check = {}
    for i,j in listclasses:
        if not i in check:
            check[i] = j
        else:
            raise Exception("ERROR ! Type %r and %r share the same __data_type__ : %s" % (j, check[i], i))

    return dict(listclasses)

def to_object_from_data_type(data):
    """
    Attempts to create an object from the given intermediary data set.
    """
    # 1. Find class for data-type
    dt = data["datatype"]
    classes = get_serialized_classes()
    if not dt in classes:
        raise Exception, "Don't have a class to handle data-type %r" % dt
    obj = classes[dt]()
    obj.fromDataFormat(data)
    return obj
