# PiTiVi , Non-linear video editor
#
#       test_formatter.py
#
# Copyright (c) 2009, Edward Hervey <bilboed@bilboed.com>
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

from xml.etree.ElementTree import Element, SubElement, tostring

from pitivi.reflect import qual
from pitivi.factories.base import SourceFactory
from pitivi.factories.file import FileSourceFactory
from pitivi.timeline.track import SourceTrackObject
from pitivi.formatters.base import Formatter

version = "0.1"

def indent(elem, level=0):
    i = "\n" + level*"  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indent(elem, level+1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i

class ElementTreeFormatterContext(object):
    def __init__(self):
        self.streams = {}
        self.factories = {}
        self.track_objects = {}

class ElementTreeFormatter(Formatter):
    _element_id = 0

    def _new_element_id(self):
        element_id = self._element_id
        self._element_id += 1

        return str(element_id)

    def _saveStream(self, stream, context):
        element = Element("stream")
        element.attrib["id"] = self._new_element_id()
        element.attrib["type"] = qual(stream.__class__)
        element.attrib["caps"] = str(stream.caps)

        context.streams[stream] = element

        return element

    def _saveStreamRef(self, stream, context):
        stream_element = context.streams[stream]
        element = Element("stream-ref")
        element.attrib["id"] = stream_element.attrib["id"]

        return element

    def _saveSource(self, source, context):
        element = self._saveObjectFactory(source, context)
        if isinstance(source, FileSourceFactory):
            return self._saveFileSourceFactory(element, source, context)

        return element

    def _saveObjectFactory(self, factory, context):
        element = Element("source")
        element.attrib["id"] = self._new_element_id()
        element.attrib["type"] = qual(factory.__class__)

        input_streams_element = SubElement(element, "input-streams")
        input_streams = factory.getInputStreams()
        for stream in input_streams:
            stream_element = self._saveStream(stream, context)
            input_streams_element.append(stream_element)

        output_streams_element = SubElement(element, "output-streams")
        output_streams = factory.getOutputStreams()
        for stream in output_streams:
            stream_element = self._saveStream(stream, context)
            output_streams_element.append(stream_element)

        context.factories[factory] = element

        return element

    def _saveFileSourceFactory(self, element, source, context):
        element.attrib["filename"] = source.filename

        return element

    def _saveFactoryRef(self, factory, context):
        element = Element("factory-ref")
        element.attrib["id"] = context.factories[factory].attrib["id"]

        return element

    def _saveFactories(self, factories, context):
        element = Element("factories")
        sources = SubElement(element, "sources")
        for factory in factories:
            if isinstance(factory, SourceFactory):
                source_element = self._saveSource(factory, context)
                sources.append(source_element)

        return element

    def _saveTrackObject(self, track_object, context):
        element = Element("track-object")
        element.attrib["id"] = self._new_element_id()
        element.attrib["type"] = qual(track_object.__class__)
        for attribute in ("start", "duration",
                "in_point", "media_duration", "priority"):
            element.attrib[attribute] = str(getattr(track_object, attribute))

        factory_ref = \
                self._saveFactoryRef(track_object.factory, context)
        stream_ref = self._saveStreamRef(track_object.stream, context)

        element.append(factory_ref)
        element.append(stream_ref)

        context.track_objects[track_object] = element

        return element

    def _saveTrackObjectRef(self, track_object, context):
        element = Element("track-object-ref")
        element.attrib["id"] = context.track_objects[track_object].attrib["id"]

        return element

    def _saveTrackObjectRefs(self, track_objects, context):
        element = Element("track-object-refs")

        for track_object in track_objects:
            if track_object is track_object.track.default_track_object:
                continue

            track_object_ref = self._saveTrackObjectRef(track_object, context)
            element.append(track_object_ref)

        return element

    def _saveTrack(self, track, context):
        element = Element("track")
        track_objects = SubElement(element, "track-objects")

        for track_object in track.track_objects:
            if track_object is track.default_track_object:
                continue

            track_object_element = self._saveTrackObject(track_object, context)
            track_objects.append(track_object_element)

        return element

    def _saveTimelineObject(self, timeline_object, context):
        element = Element("timeline-object")
        factory_ref = self._saveFactoryRef(timeline_object.factory, context)
        element.append(factory_ref)
        track_object_refs = SubElement(element, "track-object-refs")
        for track_object in timeline_object.track_objects:
            track_object_ref = self._saveTrackObjectRef(track_object, context)
            track_object_refs.append(track_object_ref)

        return element

    def _saveTimelineObjects(self, timeline_objects, context):
        element = Element("timeline-objects")
        for timeline_object in timeline_objects:
            timeline_object_element = self._saveTimelineObject(timeline_object)
            element.append(timeline_object_element)

        return element

    def _saveTracks(self, tracks, context):
        element = Element("tracks")
        for track in tracks:
            track_element = self._saveTrack(track, context)
            element.append(track_element)

        return element

    def _saveTimeline(self, timeline, context):
        element = Element("timeline")

        tracks = self._saveTracks(timeline.tracks, context)
        element.append(tracks)

        timeline_objects = \
                self._saveTimelineObjects(timeline.timeline_objects, context)
        element.append(timeline_objects)

        return element

    def _saveMainTag(self, context):
        element = Element("pitivi")
        element.attrib["formatter"] = "etree"
        element.attrib["version"] = version

        return element

    def _saveProject(self, project, context):
        root = self._saveMainTag(context)

        factories = project.sources.sources.values()
        factories_element = self._saveFactories(factories, context)
        root.append(factories_element)

        timeline_element = self._saveTimeline(project.timeline, context)
        root.append(timeline_element)

        return root
