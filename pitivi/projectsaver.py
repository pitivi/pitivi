
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
This module handles conversion from project files/edit decision lists
to intermediate representations. It provides a base class which can be
derived to implement different file formats, exception classes for
representing errors, and a sample implementation which uses cPickle to
load and store data
"""

from cPickle import load, dump, PicklingError, UnpicklingError
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
    """Provides minimal base functionality for saving project
    files. Other file formats can be implemented by deriving from this
    class"""

    @classmethod
    def newProjectSaver(cls, fmt="pickle"):
        """Returns a new instance of a project saver derivative.

        fmt      -- format string which represents the file format module
        returns  -- instance of project saver or None if format
        unavailable"""

        if fmt != "pickle":
            return None
        return PickleFormat()

    # This may be redundant now with the advent of plugin manager
    @classmethod
    def listFormats(cls):
        """Returns a list of implemented file formats
        """
        #FIXME: this is crack
        return ("pickle",)

    def __init__(self, format=None):
        pass

    def saveToFile(self, tree, output_stream):
        """The public method for saving files. Users of this class should
        call this method to save projects to an open file object.

        tree          -- a representation of a project file in the
                         intermediate format
        output_stream -- a file object open for writing.

        throws: ProjectSaveError if project not successfully saved"""

        if not self.dump(tree, output_stream):
            raise ProjectSaveError ("Error Saving File: ")

    def openFromFile(self, input_stream):
        """Public method for loading files. Users of this class should
        call this method to load a file from an open file object.

        input_stream -- open file object from which to read

        throws: ProjectLoadError if stream cannot be read"""
        
        tree = self.load(input_stream)
        self.validate(tree)
        return tree

    
    def validate(self, tree):
        """Used internally to validate the project data structure
        before it is used by the application.

        tree -- the unvalidated file in the intermediate format

        throws: ProjectLoadError if tree is invalid"""
        #TODO: implement this
        pass

    def load(self, input_stream):
        """Subclasses should implement this method

        Reads input_stream, and returns a project tree in the
        intermediate format.

        input_stream -- open file object containing data to read
        returns      -- an intermediate format representation of the
                        project if file successfully read, or None"""
        
        raise Exception("Not Implemented!")

    def dump(self, tree, output_stream):
        """Subclasses should implement this method

        Takes a tree, and a reference to an open file object and
        writes a representation of the tree to the output
        stream.

        tree          -- intermediate format representation of project
        output_stream -- file object open for writing returns True on
                         success, False otherwise."""
        
        raise Exception("Not Implemented!")
    
    
class PickleFormat(ProjectSaver):
    """ Implements default file format project files using cpickle"""
    file_format = "pickle"
    
    def load(self, input_stream):
        try:
            tree = load(input_stream)
            return tree
        except UnpicklingError:
            return None

    def dump(self, tree, output_stream):
        try:
            dump(tree, output_stream, protocol=2)
            return True
        except PicklingError:
            return False
