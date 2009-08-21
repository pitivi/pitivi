# PiTiVi , Non-linear video editor
#
#       etree.py
#
# Copyright (c) 2009, Alessandro Decina <alessandrod.@gmail.com>
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

from xml.etree.ElementTree import Element, SubElement, tostring, parse

from pitivi.reflect import qual, namedAny
from pitivi.factories.base import SourceFactory
from pitivi.factories.file import FileSourceFactory
from pitivi.timeline.track import Track
from pitivi.timeline.timeline import TimelineObject
from pitivi.formatters.base import Formatter, FormatterError
from pitivi.utils import get_filesystem_encoding
from pitivi.settings import ExportSettings
from pitivi.stream import match_stream_groups_map

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
        self.rootelement = None

class ElementTreeFormatterSaveContext(ElementTreeFormatterContext):
    pass

class ElementTreeFormatterLoadContext(ElementTreeFormatterContext):
    pass

class ElementTreeFormatter(Formatter):
    _element_id = 0
    _our_properties = ["id", "type"]

    def __init__(self, *args, **kwargs):
        Formatter.__init__(self, *args, **kwargs)
        self.factoriesnode = None
        self.timelinenode = None
        self._settingsnode = None
        self._context = ElementTreeFormatterContext()

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
        # edward: argh, I went past there, what shall I do now ?
        return gst.Caps("meh, name=%s" % value)[0]["name"]

    def _saveStream(self, stream):
        element = Element("stream")
        element.attrib["id"] = self._new_element_id()
        element.attrib["type"] = qual(stream.__class__)
        element.attrib["caps"] = str(stream.caps)
        element.attrib["name"] = str(stream.pad_name)

        self._context.streams[stream] = element

        return element

    def _loadStream(self, element):
        id_ = element.attrib["id"]
        klass = namedAny(element.attrib["type"])
        caps = gst.Caps(element.attrib["caps"])

        stream = klass(caps, element.attrib.get("name", None))

        self._context.streams[id_] = stream

        return stream

    def _saveStreamRef(self, stream):
        stream_element = self._context.streams[stream]
        element = Element("stream-ref")
        element.attrib["id"] = stream_element.attrib["id"]

        return element

    def _loadStreamRef(self, element):
        return self._context.streams[element.attrib["id"]]

    def _saveSource(self, source):
        element = self._saveObjectFactory(source)
        if isinstance(source, FileSourceFactory):
            return self._saveFileSourceFactory(element, source)

        return element

    def _loadFactory(self, element):
        klass = namedAny(element.attrib["type"])

        return self._loadObjectFactory(klass, element)

    def _saveObjectFactory(self, factory):
        element = Element("source")
        element.attrib["id"] = self._new_element_id()
        element.attrib["type"] = qual(factory.__class__)
        element.attrib["default_duration"] = str(factory.default_duration)
        element.attrib["duration"] = str(factory.duration)

        input_streams_element = SubElement(element, "input-streams")
        input_streams = factory.getInputStreams()
        for stream in input_streams:
            stream_element = self._saveStream(stream)
            input_streams_element.append(stream_element)

        output_streams_element = SubElement(element, "output-streams")
        output_streams = factory.getOutputStreams()
        for stream in output_streams:
            stream_element = self._saveStream(stream)
            output_streams_element.append(stream_element)

        self._context.factories[factory] = element

        return element

    def _loadObjectFactory(self, klass, element):
        self.debug("klass:%r, element:%r", klass, element)
        # FIXME : we should check if the given ObjectFactory
        # requires a filename !
        filename = element.attrib.get("filename", None)
        if filename is not None:
            if isinstance(filename, unicode):
                filename = filename.encode("utf-8")

            factory = klass(filename)
        else:
            factory = klass()

        factory.duration = long(element.attrib["duration"])
        factory.default_duration = long(element.attrib["default_duration"])

        input_streams = element.find("input-streams") or []
        for stream_element in input_streams:
            stream = self._loadStream(stream_element)
            factory.addInputStream(stream)

        output_streams = element.find("output-streams")
        for stream_element in output_streams:
            stream = self._loadStream(stream_element)
            factory.addOutputStream(stream)

        if filename is not None:
            filename1 = self.validateSourceURI(filename, factory)
            if filename != filename1:
                # the file was moved
                factory.uri = factory.filename = filename1

        self._context.factories[element.attrib["id"]] = factory
        return factory

    def _saveFileSourceFactory(self, element, source):
        # FIXME: we should probably have a rule that we only deal with unicode
        # strings in pitivi
        if not isinstance(source.filename, unicode):
            fs_encoding = get_filesystem_encoding()
            filename = source.filename.decode(fs_encoding)
        else:
            filename = source.filename
        element.attrib["filename"] = filename

        return element

    def _saveFactoryRef(self, factory):
        element = Element("factory-ref")
        element.attrib["id"] = self._context.factories[factory].attrib["id"]

        return element

    def _loadFactoryRef(self, element):
        return self._context.factories[element.attrib["id"]]

    def _saveFactories(self, factories):
        element = Element("factories")
        sources = SubElement(element, "sources")
        for factory in factories:
            if isinstance(factory, SourceFactory):
                source_element = self._saveSource(factory)
                sources.append(source_element)

        return element

    def _loadSources(self):
        try:
            return self._sources
        except AttributeError:
            pass

        sources = self.factoriesnode.find("sources")
        res = []
        for src in sources:
            res.append(self._loadFactory(src))

        self._sources = res
        return res

    def _serializeDict(self, element, dict):
        for a, b in dict.iteritems():
            print a, b, type(b)
            if isinstance(b, str):
                element.attrib[a] = b
            elif isinstance(b, bool):
                element.attrib[a] = "(boolean) %r" % b
            elif isinstance(b, float):
                element.attrib[a] = "(float) %r" % b
            else:
                element.attrib[a] = "(guint64) %r" % b


    def _deserializeDict(self, element):
        d = {}
        for a, b in element.attrib.iteritems():
            d[a] = self._parsePropertyValue(b)
        return d

    def _saveProjectSettings(self, settings):
        element = Element('export-settings')
        element.attrib["videowidth"] = str(int(settings.videowidth))
        element.attrib["videoheight"] = str(int(settings.videoheight))
        element.attrib["videorate-num"] = str(int(settings.videorate.num))
        element.attrib["videorate-denom"] = str(int(settings.videorate.denom))
        element.attrib["videopar-num"] = str(int(settings.videopar.num))
        element.attrib["videopar-denom"] = str(int(settings.videopar.denom))
        element.attrib["audiochannels"] = str(int(settings.audiochannels))
        element.attrib["audiorate"] = str(int(settings.audiorate))
        element.attrib["audiodepth"] = str(int(settings.audiodepth))
        element.attrib["vencoder"] = settings.vencoder or ""
        element.attrib["aencoder"] = settings.aencoder or ""
        element.attrib["muxer"] = settings.muxer

        # container/encoder settings
        if settings.containersettings != {}:
            ss = SubElement(element, "container-settings")
            self._serializeDict(ss, settings.containersettings)
        if settings.vcodecsettings != {}:
            ss = SubElement(element, "vcodec-settings")
            self._serializeDict(ss, settings.vcodecsettings)
        if settings.acodecsettings != {}:
            ss = SubElement(element, "acodec-settings")
            self._serializeDict(ss, settings.acodecsettings)
        return element

    def _loadProjectSettings(self, element):
        self.debug("element:%r", element)
        settings = ExportSettings()
        settings.videowidth = int(element.attrib["videowidth"])
        settings.videoheight = int(element.attrib["videoheight"])
        settings.videorate = gst.Fraction(int(element.attrib["videorate-num"]),
                                         int(element.attrib["videorate-denom"]))
        settings.videopar = gst.Fraction(int(element.attrib["videopar-num"]),
                                         int(element.attrib["videopar-denom"]))
        settings.audiochannels = int(element.attrib["audiochannels"])
        settings.audiorate = int(element.attrib["audiorate"])
        settings.audiodepth = int(element.attrib["audiodepth"])
        settings.aencoder = element.attrib["aencoder"] or None
        settings.vencoder = element.attrib["vencoder"] or None
        settings.muxer = element.attrib["muxer"]

        sett = element.find("container-settings")
        if sett != None:
            settings.containersettings = self._deserializeDict(sett)
        sett = element.find("vcodec-settings")
        if sett != None:
            settings.vcodecsettings = self._deserializeDict(sett)
        sett = element.find("acodec-settings")
        if sett != None:
            settings.acodecsettings = self._deserializeDict(sett)

        return settings

    def _saveTrackObject(self, track_object):
        element = Element("track-object")
        element.attrib["id"] = self._new_element_id()
        element.attrib["type"] = qual(track_object.__class__)
        for attribute in ("start", "duration",
                "in_point", "media_duration"):
            element.attrib[attribute] = \
                    str("(gint64)%s" % getattr(track_object, attribute))

        element.attrib["priority"] = "(int)%s" % track_object.priority

        factory_ref = \
                self._saveFactoryRef(track_object.factory)
        stream_ref = self._saveStreamRef(track_object.stream)

        element.append(factory_ref)
        element.append(stream_ref)
        interpolators = track_object.getInterpolators()
        curves = Element("curves")
        for property, interpolator in interpolators.itervalues():
            curves.append(self._saveInterpolator(interpolator, property))
        element.append(curves)

        self._context.track_objects[track_object] = element

        return element

    def _loadTrackObject(self, track, element):
        self.debug("%r", element)
        klass = namedAny(element.attrib["type"])

        factory_ref = element.find("factory-ref")
        factory = self._loadFactoryRef(factory_ref)

        stream_ref = element.find("stream-ref")
        stream = self._loadStreamRef(stream_ref)

        track_object = klass(factory, stream)
        for name, value_string in self._filterElementProperties(element):
            value = self._parsePropertyValue(value_string)
            setattr(track_object, name, value)
        track.addTrackObject(track_object)
        curves_element = element.find("curves")
        if curves_element:
            for curve in curves_element.getchildren():
                self._loadInterpolator(curve, track_object)

        self._context.track_objects[element.attrib["id"]] = track_object
        return track_object

    def _saveInterpolator(self, interpolator, prop):
        typename = prop.value_type.name
        element = Element("curve", property=prop.name, type=typename)

        start = self._saveKeyframe(interpolator.start, typename, False)
        start.tag = "start"
        element.append(start)

        for kf in interpolator.getInteriorKeyframes():
            kfel = self._saveKeyframe(kf, typename)
            element.append(kfel)

        end = self._saveKeyframe(interpolator.end, typename, False)
        end.tag = "end"
        element.append(end)
        return element

    def _saveKeyframe(self, keyframe, typename, time=True):
        element = Element("keyframe")
        element.attrib["value"] = "(%s)%r" % (typename, keyframe.value)
        element.attrib["mode"] = str(keyframe.mode)
        if not time:
            return element
        element.attrib["time"] = str(keyframe.time)
        return element

    def _loadInterpolator(self, element, trackobject):
        interpolator = trackobject.getInterpolator(element.attrib["property"])
        start = element.find("start")
        interpolator.start.value = self._parsePropertyValue(
            start.attrib["value"])
        interpolator.start.mode = int(start.attrib["mode"])

        for kf in element.getiterator("keyframe"):
            interpolator.newKeyframe(long(kf.attrib["time"]), 
                value=self._parsePropertyValue(kf.attrib["value"]),
                mode=int(kf.attrib["mode"]))
        end = element.find("end")
        interpolator.end.value = self._parsePropertyValue(end.attrib["value"])
        interpolator.end.mode = int(end.attrib["mode"])

    def _saveTrackObjectRef(self, track_object):
        element = Element("track-object-ref")
        element.attrib["id"] = self._context.track_objects[track_object].attrib["id"]

        return element

    def _loadTrackObjectRef(self, element):
        self.debug("%r", element)
        return self._context.track_objects[element.attrib["id"]]

    def _saveTrackObjectRefs(self, track_objects):
        element = Element("track-object-refs")

        for track_object in track_objects:
            track_object_ref = self._saveTrackObjectRef(track_object)
            element.append(track_object_ref)

        return element

    def _loadTrackObjectRefs(self, element):
        self.debug("%r", element)
        track_objects = []
        for track_object_element in element:
            track_object = self._loadTrackObjectRef(track_object_element)
            track_objects.append(track_object)

        return track_objects

    def _saveTrack(self, track):
        element = Element("track")
        stream_element = self._saveStream(track.stream)
        element.append(stream_element)
        track_objects = SubElement(element, "track-objects")

        for track_object in track.track_objects:
            if track_object is track.default_track_object:
                continue

            track_object_element = self._saveTrackObject(track_object)
            track_objects.append(track_object_element)

        return element

    def _loadTrack(self, element):
        self.debug("%r", element)
        stream_element = element.find("stream")
        stream = self._loadStream(stream_element)

        track = Track(stream)

        track_objects_element  = element.find("track-objects")
        for track_object_element in track_objects_element:
            self._loadTrackObject(track, track_object_element)

        return track

    def _saveTracks(self, tracks):
        element = Element("tracks")
        for track in tracks:
            track_element = self._saveTrack(track)
            element.append(track_element)

        return element

    def _loadTracks(self, element):
        self.debug("element:%r", element)
        tracks = []
        for track_element in element:
            track = self._loadTrack(track_element)
            tracks.append(track)

        return tracks

    ## TimelineObjects

    def _saveTimelineObject(self, timeline_object):
        element = Element("timeline-object")
        factory_ref = self._saveFactoryRef(timeline_object.factory)
        element.append(factory_ref)
        track_object_refs = \
                self._saveTrackObjectRefs(timeline_object.track_objects)
        element.append(track_object_refs)

        return element

    def _loadTimelineObject(self, element):
        factory_ref = element.find("factory-ref")
        factory = self._loadFactoryRef(factory_ref)

        timeline_object = TimelineObject(factory)
        track_object_refs_element = element.find("track-object-refs")
        track_objects = \
                self._loadTrackObjectRefs(track_object_refs_element)

        for track_object in track_objects:
            timeline_object.addTrackObject(track_object)

        return timeline_object

    def _saveTimelineObjects(self, timeline_objects):
        element = Element("timeline-objects")
        for timeline_object in timeline_objects:
            timeline_object_element = self._saveTimelineObject(timeline_object)
            element.append(timeline_object_element)

        return element

    def _loadTimelineObjects(self, element):
        timeline_objects = []
        for timeline_object_element in element:
            timeline_object = \
                    self._loadTimelineObject(timeline_object_element)
            timeline_objects.append(timeline_object)

        return timeline_objects

    ## Timeline

    def _saveTimeline(self, timeline):
        element = Element("timeline")

        tracks = self._saveTracks(timeline.tracks)
        element.append(tracks)

        timeline_objects = \
                self._saveTimelineObjects(timeline.timeline_objects)
        element.append(timeline_objects)

        return element

    def _loadTimeline(self, element):
        self.debug("element:%r", element)

        timeline = self.project.timeline

        # Tracks
        tracks_element = element.find("tracks")
        tracks = self._loadTracks(tracks_element)

        # Timeline Object
        timeline_objects_element = element.find("timeline-objects")
        timeline_objects = \
                self._loadTimelineObjects(timeline_objects_element)

        for track in tracks:
            timeline.addTrack(track)

        # add the timeline objects
        for timeline_object in timeline_objects:
            # NOTE: this is a low-level routine that simply appends the
            # timeline object to the timeline list. It doesn't ensure all the
            # child track objects have been added to their respective tracks.
            timeline.addTimelineObject(timeline_object)

        return timeline

    ## Main methods

    def _saveMainTag(self):
        element = Element("pitivi")
        element.attrib["formatter"] = "etree"
        element.attrib["version"] = version

        return element

    def _serializeProject(self, project):
        root = self._saveMainTag()

        # settings
        if project.settings:
            root.append(self._saveProjectSettings(project.settings))

        # sources
        root.append(self._saveFactories(project.sources.getSources()))

        # timeline
        root.append(self._saveTimeline(project.timeline))
        return root

    ## Formatter method implementations

    def _saveProject(self, project, location):
        root = self._serializeProject(project)
        f = file(location.split('file://')[1], "w")
        indent(root)
        f.write(tostring(root))
        f.close()

        return True

    def _loadProject(self, location, project):
        self.debug("location:%s, project:%r", location, project)
        # open the given location
        self._context.rootelement = parse(location.split('://', 1)[1])
        self.factoriesnode = self._context.rootelement.find("factories")
        self.timelinenode = self._context.rootelement.find("timeline")
        self._settingsnode = self._context.rootelement.find("export-settings")
        if project and self._settingsnode != None:
            project.setSettings(self._loadProjectSettings(self._settingsnode))

        # rediscover the factories
        closure = {"rediscovered": 0}
        try:
            sources = self._loadSources()
        except FormatterError, e:
            self.emit("new-project-failed", location, e)
            return

        uris = [source.uri for source in sources]
        discoverer = project.sources.discoverer
        discoverer.connect("discovery-done", self._discovererDiscoveryDoneCb,
                project, sources, uris, closure)
        discoverer.connect("discovery-error", self._discovererDiscoveryErrorCb,
                project, sources, uris, closure)

        if not sources:
            self._finishLoadingProject(project)
            return
        # start the rediscovering from the first source
        source = sources[0]
        discoverer.addUri(source.uri)

    def _findFactoryContextKey(self, old_factory):
        key = None
        for k, old_factory1 in self._context.factories.iteritems():
            if old_factory is old_factory1:
                key = k
                break

        return key

    def _matchFactoryStreams(self, factory, old_factory):
        old_streams = old_factory.getOutputStreams()
        streams = factory.getOutputStreams()
        self.debug("matching factory streams old (%s) %s new (%s) %s",
                len(old_streams), old_streams, len(streams), streams)
        if len(old_streams) != len(streams):
            raise FormatterError("cant find all streams")

        stream_map = match_stream_groups_map(old_streams, streams)
        self.debug("stream map (%s) %s", len(stream_map), stream_map)
        if len(stream_map) != len(old_streams):
            raise FormatterError("streams don't match")

        return stream_map

    def _replaceOldFactoryStreams(self, factory, old_factory):
        old_stream_to_new_stream = self._matchFactoryStreams(factory,
                old_factory)

        old_streams = old_factory.getOutputStreams()
        new_streams = {}
        for stream_id, old_stream in self._context.streams.iteritems():
            try:
                new_stream = old_stream_to_new_stream[old_stream]
            except KeyError:
                new_stream = old_stream
            new_streams[stream_id] = new_stream

        self._context.streams = new_streams

    def _replaceMatchingOldFactory(self, factory, old_factories):
        old_factory = None
        old_factory_index = None
        for index, old_factory1 in enumerate(old_factories):
            if old_factory1.uri == factory.uri:
                old_factory = old_factory1
                old_factory_index = index
                break

        # this should never happen
        assert old_factory is not None

        # replace the old factory with the new rediscovered one
        old_factories[old_factory_index] = factory

        # make self._context.factories[key] point to the new factory
        context_key = self._findFactoryContextKey(old_factory)
        self._context.factories[context_key] = factory

        self._replaceOldFactoryStreams(factory, old_factory)

    def _discovererDiscoveryDoneCb(self, discoverer, uri, factory,
            project, old_factories, uris, closure):
        if factory.uri not in uris:
            # someone else is using discoverer, this signal isn't for us
            return

        self._replaceMatchingOldFactory(factory, old_factories)
        project.sources.addFactory(factory)

        closure["rediscovered"] += 1
        if closure["rediscovered"] == len(old_factories):
            self._finishLoadingProject(project)
            return

        # schedule the next source
        next = old_factories[closure["rediscovered"]]
        discoverer.addUri(next.uri)

    def _discovererDiscoveryErrorCb(self, discoverer, uri, error, detail,
            project, sources, uris, closure):
        if uri not in uris:
            # someone else is using discoverer, this signal isn't for us
            return

        self.emit("new-project-failed", uri,
                FormatterError("%s: %s" % (error, detail)))

    def newProject(self):
        project = Formatter.newProject(self)
        # add the settings
        if self._settingsnode != None:
            project.setSettings(self._loadProjectSettings(self._settingsnode))
        return project

    def _getSources(self):
        self.debug("%r", self)
        return self._loadSources()

    def _fillTimeline(self):
        # fill up self.project
        self._loadTimeline(self.timelinenode)

    @classmethod
    def canHandle(cls, uri):
        return uri.endswith(".xptv")
