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

import gobject
gobject.threads_init()
import gst

from xml.etree.ElementTree import Element, SubElement, tostring

from pitivi.reflect import qual, namedAny
from pitivi.factories.base import SourceFactory
from pitivi.factories.file import FileSourceFactory
from pitivi.timeline.track import Track, SourceTrackObject
from pitivi.timeline.timeline import Timeline, TimelineObject
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

class ElementTreeFormatterSaveContext(object):
    def __init__(self):
        self.streams = {}
        self.factories = {}
        self.track_objects = {}

class ElementTreeFormatterLoadContext(object):
    def __init__(self):
        self.streams = {}
        self.factories = {}
        self.track_objects = {}

class ElementTreeFormatter(Formatter):
    _element_id = 0
    _our_properties = ["id", "type"]

    def _new_element_id(self):
        element_id = self._element_id
        self._element_id += 1

        return str(element_id)

    def _filterElementProperties(self, element):
        for name, value in element.attrib.iteritems():
            if name in self._our_properties:
                continue

            yield name, value

    def _parsePropertyValue(self, value):
        # nothing to read here, move along
        return gst.Caps("meh, name=%s" % value)[0]["name"]

    def _saveStream(self, stream, context):
        element = Element("stream")
        element.attrib["id"] = self._new_element_id()
        element.attrib["type"] = qual(stream.__class__)
        element.attrib["caps"] = str(stream.caps)

        context.streams[stream] = element

        return element

    def _loadStream(self, element, context):
        id_ = element.attrib["id"]
        klass = namedAny(element.attrib["type"])
        caps = gst.Caps(element.attrib["caps"])

        stream = klass(caps)

        context.streams[id_] = stream

        return stream

    def _saveStreamRef(self, stream, context):
        stream_element = context.streams[stream]
        element = Element("stream-ref")
        element.attrib["id"] = stream_element.attrib["id"]

        return element

    def _loadStreamRef(self, element, context):
        return context.streams[element.attrib["id"]]

    def _saveSource(self, source, context):
        element = self._saveObjectFactory(source, context)
        if isinstance(source, FileSourceFactory):
            return self._saveFileSourceFactory(element, source, context)

        return element

    def _loadFactory(self, element, context):
        klass = namedAny(element.attrib["type"])

        return self._loadObjectFactory(klass, element, context)

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

    def _loadObjectFactory(self, klass, element, context):
        # FIXME
        if isinstance(klass, FileSourceFactory):
            factory = FileSourceFactory(element.attrib["filename"])
        else:
            factory = klass()

        input_streams = element.find("input-streams") or []
        for stream_element in input_streams:
            stream = self._loadStream(stream_element, context)
            factory.addInputStream(stream)

        output_streams = element.find("output-streams")
        for stream_element in output_streams:
            stream = self._loadStream(stream_element, context)
            factory.addOutputStream(stream)

        context.factories[element.attrib["id"]] = factory

        return factory

    def _saveFileSourceFactory(self, element, source, context):
        element.attrib["filename"] = source.filename

        return element

    def _saveFactoryRef(self, factory, context):
        element = Element("factory-ref")
        element.attrib["id"] = context.factories[factory].attrib["id"]

        return element

    def _loadFactoryRef(self, element, context):
        return context.factories[element.attrib["id"]]

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
                "in_point", "media_duration"):
            element.attrib[attribute] = \
                    str("(gint64)%s" % getattr(track_object, attribute))

        element.attrib["priority"] = "(int)%s" % track_object.priority

        factory_ref = \
                self._saveFactoryRef(track_object.factory, context)
        stream_ref = self._saveStreamRef(track_object.stream, context)

        element.append(factory_ref)
        element.append(stream_ref)

        context.track_objects[track_object] = element

        return element

    def _loadTrackObject(self, element, context):
        klass = namedAny(element.attrib["type"])

        factory_ref = element.find("factory-ref")
        factory = self._loadFactoryRef(factory_ref, context)

        stream_ref = element.find("stream-ref")
        stream = self._loadStreamRef(stream_ref, context)

        track_object = klass(factory, stream)
        for name, value_string in self._filterElementProperties(element):
            value = self._parsePropertyValue(value_string)
            setattr(track_object, name, value)

        return track_object

    def _saveTrackObjectRef(self, track_object, context):
        element = Element("track-object-ref")
        element.attrib["id"] = context.track_objects[track_object].attrib["id"]

        return element

    def _loadTrackObjectRef(self, element, context):
        return context.track_objects[element.attrib["id"]]

    def _saveTrackObjectRefs(self, track_objects, context):
        element = Element("track-object-refs")

        for track_object in track_objects:
            track_object_ref = self._saveTrackObjectRef(track_object, context)
            element.append(track_object_ref)

        return element

    def _loadTrackObjectRefs(self, element, context):
        track_objects = []
        for track_object_element in element:
            track_object = self._loadTrackObjectRef(track_object_element, context)
            track_objects.append(track_object)

        return track_objects

    def _saveTrack(self, track, context):
        element = Element("track")
        stream_element = self._saveStream(track.stream, context)
        element.append(stream_element)
        track_objects = SubElement(element, "track-objects")

        for track_object in track.track_objects:
            if track_object is track.default_track_object:
                continue

            track_object_element = self._saveTrackObject(track_object, context)
            track_objects.append(track_object_element)

        return element

    def _loadTrack(self, element, context):
        stream_element = element.find("stream")
        stream = self._loadStream(stream_element, context)

        track = Track(stream)

        track_objects_element  = element.find("track-objects")
        for track_object_element in track_objects_element:
            track_object = self._loadTrackObject(track_object_element, context)
            track.addTrackObject(track_object)

        return track

    def _saveTracks(self, tracks, context):
        element = Element("tracks")
        for track in tracks:
            track_element = self._saveTrack(track, context)
            element.append(track_element)

        return element

    def _loadTracks(self, element, context):
        tracks = []
        for track_element in element:
            track = self._loadTrack(track_element, context)
            tracks.append(track)

        return tracks

    def _saveTimelineObject(self, timeline_object, context):
        element = Element("timeline-object")
        factory_ref = self._saveFactoryRef(timeline_object.factory, context)
        element.append(factory_ref)
        track_object_refs = \
                self._saveTrackObjectRefs(timeline_object.track_objects,
                        context)
        element.append(track_object_refs)
        
        return element

    def _loadTimelineObject(self, element, context):
        factory_ref = element.find("factory-ref")
        factory = self._loadFactoryRef(factory_ref, context)

        timeline_object = TimelineObject(factory)
        track_object_refs_element = element.find("track-object-refs")
        track_objects = \
                self._loadTrackObjectRefs(track_object_refs_element, context)

        for track_object in track_objects:
            timeline_object.addTrackObject(track_object)

        return timeline_object

    def _saveTimelineObjects(self, timeline_objects, context):
        element = Element("timeline-objects")
        for timeline_object in timeline_objects:
            timeline_object_element = self._saveTimelineObject(timeline_object,
                    context)
            element.append(timeline_object_element)

        return element

    def _loadTimelineObjects(self, element, context):
        timeline_objects = []
        for timeline_object_element in element:
            timeline_object = \
                    self._loadTimelineObject(timeline_object_element, context)
            timeline_objects.append(timeline_object)

        return timeline_objects

    def _saveTimeline(self, timeline, context):
        element = Element("timeline")

        tracks = self._saveTracks(timeline.tracks, context)
        element.append(tracks)

        timeline_objects = \
                self._saveTimelineObjects(timeline.timeline_objects, context)
        element.append(timeline_objects)

        return element

    def _loadTimeline(self, element, context):
        tracks_element = element.find("tracks")
        tracks = self._loadTracks(tracks_element, context)

        timeline_objects_element = element.find("timeline-objects")
        timeline_objects = \
                self._loadTimelineObjects(timeline_objects_element, context)

        timeline = Timeline()
        for track in tracks:
            timeline.addTrack(track)

        for timeline_object in timeline_objects:
            timeline.addTimelineObject(timeline_object)

        return timeline

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

    def _loadProject(self, element, context):
        factories_element = element.find("factories")
        factories = self._loadFactories(factories_element, context)

        timeline_element = element.find("timeline")
        timeline = self._loadTimeline(timeline_element, context)

        project = Project()
        project.timeline = timeline

        # FIXME: add factories to the sources list

        for factory in factories:
            if isinstance(factory, SourceFactory):
                timeline.addSourceFactory(factory)
            else:
                raise NotImplementedError()

        return project
