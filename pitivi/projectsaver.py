
# PiTiVi , Non-linear video editor
#
#       pitivi/projectsaver.py
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

"""
Project File Serialization and Deserialization
"""
from cPickle import load, dump, PicklingError, UnpicklingError
import timeline.objects
import timeline.source
import timeline.composition
import settings

class ProjectError(Exception):
    def __init__(self, reason):
        self.reason = reason
    def __str__(self):
        return self.reason
    def getReason(self):
        return self.reason

class ProjectSaveError(ProjectError):
    pass

class ProjectLoadError(ProjectError):
    pass

class ProjectSaver:
    _formats = {}
    _classes = {}

    #TODO: make listFormats, registerFormat, and newProjectSaver thread safe
    @classmethod
    def registerFormat(cls, format, description, extensions, implementation):
        assert(format not in cls._formats.keys())
        assert(type(format) == str)
        assert(type(description) == str)
        assert(type(extensions) in (list, tuple))
        cls._formats[format] = (description, extensions, implementation)

    @classmethod
    def listFormats(cls):
        """return a generator of all registered formats as list of 
        (format, description, extensions) tuples."""
        return [((key, ) + value)[:-1] for key, value in cls._formats.items()]

    @classmethod
    def newProjectSaver(cls, format="pickle", *args):
        assert(format in cls._formats)
        instance = cls._formats[format][-1](*args)
        assert(instance.serialize)
        assert(instance.deserialize)
        return instance

    #FIXME: make this dynamagical instead of hard-coded crack
    @classmethod
    def buildClassList(cls):
        crack = [("file-source", timeline.source.TimelineFileSource),
                 ("composition", timeline.composition.TimelineComposition),
                 ("project-source", ),
                 ("project-settings", settings.ExportSettings)]

        cls.classes = dict(crack)

    @classmethod
    def findObject(cls, type):
        return cls._classes[type]

    @classmethod
    def objectFromDataType(cls, obj):
        cls = findObject(obj["type"])
        instance = cls()
        instance.fromDataType(obj)
        return

    def __init__(self, format=None):
        pass

    def serialize(self, tree, output_stream):
        try:
            dump(tree, output_stream, protocol = 2)
        except PicklingError, e:
            raise ProjectSaveError, "Error Saving File: " + e

    def deserialize(self, input_stream):
        try:
            tree = load(input_stream)
            #TODO: some more validation on the returned python object.
            # I.E. is it in fact a dictionary? does it have the appropriate
            # elements? basically make sure that PiTiVi won't crash when we
            # hand off this data structure
            return tree
        except UnpicklingError, e:
            raise ProjectLoadError, "Error Loading File: " + e

#registerFormat("pickle", "PiTiVi Native Format (pickle)", ("pptv",), ProjectSaver)

#ProjectSaver.buildClassDict()

