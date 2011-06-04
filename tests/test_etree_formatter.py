# PiTiVi , Non-linear video editor
#
#       test_formatter.py
#
# Copyright (c) 2009, Alessandro Decina <alessandro.decina@collabora.co.uk>
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
# Free Software Foundation, Inc., 51 Franklin St, Fifth Floor,
# Boston, MA 02110-1301, USA.

from unittest import TestCase
import gst
from xml.etree.ElementTree import Element, SubElement

from pitivi.reflect import qual
from pitivi.formatters.etree import ElementTreeFormatter, version,\
                                    indent, tostring
from pitivi.stream import VideoStream, AudioStream
from pitivi.factories.file import FileSourceFactory
from pitivi.factories.test import VideoTestSourceFactory, \
    AudioTestSourceFactory
from pitivi.factories.operation import EffectFactory
from pitivi.timeline.track import Track, SourceTrackObject, Interpolator,\
                                  TrackEffect
from pitivi.timeline.timeline import Timeline, TimelineObject
from pitivi.project import Project
from pitivi.utils import get_controllable_properties
from pitivi.effects import EffectsHandler

class FakeElementTreeFormatter(ElementTreeFormatter):
    pass

def ts(time):
    return "(gint64)%s" % time

class TestSerialization(TestCase):
    def setUp(self):
        self.formatter = FakeElementTreeFormatter(EffectsHandler())

    def testSerializeAndDeserialize(self):
        element = Element('tag')
        values_dict = {
                'str_': 'four',
                'boolean_': True,
                'float_': 4.0,
                'guint64_': 4,
                'guint64_2': 4L}
        self.formatter._serializeDict(element, values_dict)
        # Make sure that all the keys end up in element.
        for key, unused_value in values_dict.iteritems():
            self.assertTrue(key in element.attrib)

        deserialized_values_dict = self.formatter._deserializeDict(element)
        # Make sure that all the keys in the original dict end up in the
        # deserialized dict.
        self.assertEqual(
                set(values_dict.keys()), set(deserialized_values_dict.keys()))
        for key, value in values_dict.iteritems():
            self.assertEqual(value, deserialized_values_dict[key])

class TestFormatterSave(TestCase):
    def setUp(self):
        self.formatter = FakeElementTreeFormatter(EffectsHandler())

    def testSaveStream(self):
        stream = VideoStream(gst.Caps("video/x-raw-rgb, blah=meh"))
        element = self.formatter._saveStream(stream)
        self.failUnlessEqual(element.tag, "stream")
        self.failUnless("id" in element.attrib)
        self.failUnlessEqual(element.attrib["type"], qual(stream.__class__))
        self.failUnlessEqual(element.attrib["caps"], str(stream.caps))

    def testSaveStreamRef(self):
        # save a stream so that a mapping is created in the context
        stream = VideoStream(gst.Caps("video/x-raw-rgb, blah=meh"))
        element = self.formatter._saveStream(stream)
        element_ref = self.formatter._saveStreamRef(stream)
        self.failUnlessEqual(element_ref.tag, "stream-ref")
        self.failUnlessEqual(element_ref.attrib["id"], element.attrib["id"])

    def testSaveSource(self):
        video_stream = VideoStream(gst.Caps("video/x-raw-yuv"))
        audio_stream = AudioStream(gst.Caps("audio/x-raw-int"))
        source1 = FileSourceFactory("file1.ogg")
        source1.addOutputStream(video_stream)
        source1.addOutputStream(audio_stream)
        element = self.formatter._saveSource(source1)
        self.failUnlessEqual(element.tag, "source")
        self.failUnlessEqual(element.attrib["type"], qual(source1.__class__))
        self.failUnlessEqual(element.attrib["filename"], "file1.ogg")

        streams = element.find("output-streams")
        self.failUnlessEqual(len(streams), 2)

    def testSaveFactories(self):
        video_stream = VideoStream(gst.Caps("video/x-raw-yuv"))
        audio_stream = AudioStream(gst.Caps("audio/x-raw-int"))

        source1 = FileSourceFactory("file1.ogg")
        source1.addOutputStream(video_stream)
        source1.addOutputStream(audio_stream)

        source2 = FileSourceFactory("file2.ogg")
        source2.addOutputStream(video_stream)
        source2.addOutputStream(audio_stream)

        source_factories = [source1, source2]
        element = self.formatter._saveFactories(source_factories)
        self.failUnlessEqual(element.tag, "factories")

        sources = element.find("sources")
        self.failUnlessEqual(len(sources), 2)
        #source tags are tested in testSaveSource

    def testSaveFactoryRef(self):
        video_stream = VideoStream(gst.Caps("video/x-raw-yuv"))
        audio_stream = AudioStream(gst.Caps("audio/x-raw-int"))
        source1 = FileSourceFactory("file1.ogg")
        source1.addOutputStream(video_stream)
        source1.addOutputStream(audio_stream)
        element = self.formatter._saveSource(source1)

        element_ref = self.formatter._saveFactoryRef(source1)
        self.failUnlessEqual(element_ref.tag, "factory-ref")
        self.failUnlessEqual(element_ref.attrib["id"], element.attrib["id"])

    def testSaveTrackEffect(self):
        video_stream = VideoStream(gst.Caps("video/x-raw-yuv"))
        audio_stream = AudioStream(gst.Caps("audio/x-raw-int"))

        effect1 = EffectFactory('identity', 'identity')
        effect1.addOutputStream(video_stream)
        effect1.addInputStream(video_stream)

        #It is necessary to had the identity factory to the
        #effect_factories_dictionnary
        self.formatter.avalaible_effects._effect_factories_dict['identity'] =\
                                                                     effect1
        track_effect = TrackEffect(effect1, video_stream,
                start=10 * gst.SECOND, duration=20 * gst.SECOND,
                in_point=5 * gst.SECOND, media_duration=15 * gst.SECOND,
                priority=10)

        track = Track(video_stream)
        track.addTrackObject(track_effect)

        element = self.formatter._saveTrackObject(track_effect)
        self.failUnlessEqual(element.tag, "track-object")
        self.failUnlessEqual(element.attrib["type"],
                qual(track_effect.__class__))
        self.failUnlessEqual(element.attrib["start"], ts(10 * gst.SECOND))
        self.failUnlessEqual(element.attrib["duration"], ts(20 * gst.SECOND))
        self.failUnlessEqual(element.attrib["in_point"], ts(5 * gst.SECOND))
        self.failUnlessEqual(element.attrib["media_duration"],
                ts(15 * gst.SECOND))
        self.failUnlessEqual(element.attrib["priority"], "(int)10")

        effect_element = element.find('effect')
        self.failIfEqual(effect_element, None)
        self.failIfEqual(effect_element.find("factory"), None)
        self.failIfEqual(effect_element.find("gst-element-properties"), None)

    def testSaveTrackSource(self):
        video_stream = VideoStream(gst.Caps("video/x-raw-yuv"))
        audio_stream = AudioStream(gst.Caps("audio/x-raw-int"))
        source1 = FileSourceFactory("file1.ogg")
        source1.addOutputStream(video_stream)

        # these two calls are needed to populate the context for the -ref
        # elements
        self.formatter._saveSource(source1)
        self.formatter._saveStream(video_stream)


        track_source = SourceTrackObject(source1, video_stream,
                start=10 * gst.SECOND, duration=20 * gst.SECOND,
                in_point=5 * gst.SECOND, media_duration=15 * gst.SECOND,
                priority=10)

        track = Track(video_stream)
        track.addTrackObject(track_source)

        # create an interpolator and insert it into the track object
        fakevol = gst.element_factory_make("volume")
        prop = get_controllable_properties(fakevol)[1][1]
        volcurve = Interpolator(track_source, fakevol, prop)
        track_source.interpolators[prop.name] = (prop, volcurve)

        # add some points to the interpolator
        value = float(0)
        volcurve.start.setObjectTime(0)
        volcurve.start.value = 0
        for t in xrange(3, 15, 3):
            value = int(t % 2)
            volcurve.newKeyframe(t * gst.SECOND, value)
        volcurve.end.setObjectTime(15 * gst.SECOND)
        volcurve.end.value = 15 % 2

        element = self.formatter._saveTrackObject(track_source)
        self.failUnlessEqual(element.tag, "track-object")
        self.failUnlessEqual(element.attrib["type"],
                qual(track_source.__class__))
        self.failUnlessEqual(element.attrib["start"], ts(10 * gst.SECOND))
        self.failUnlessEqual(element.attrib["duration"], ts(20 * gst.SECOND))
        self.failUnlessEqual(element.attrib["in_point"], ts(5 * gst.SECOND))
        self.failUnlessEqual(element.attrib["media_duration"],
                ts(15 * gst.SECOND))
        self.failUnlessEqual(element.attrib["priority"], "(int)10")

        self.failIfEqual(element.find("factory-ref"), None)
        self.failIfEqual(element.find("stream-ref"), None)

        # find the interpolation keyframes
        curves = element.find("curves")
        self.failIfEqual(curves, None)
        curve = curves.find("curve")
        self.failIfEqual(curve, None)
        self.failUnlessEqual(curve.attrib["property"], "volume")

        # compute a dictionary of keyframes
        saved_points = dict(((obj.attrib["time"], (obj.attrib["value"],
            obj.attrib["mode"])) for obj in curve.getiterator("keyframe")))

        # compare this with the expected values
        expected = dict(((str(t * gst.SECOND), ("(gdouble)%s" % (t % 2), "2")) for t in
            xrange(3, 15, 3)))
        self.failUnlessEqual(expected, saved_points)

    def testSaveTrackObjectRef(self):
        video_stream = VideoStream(gst.Caps("video/x-raw-yuv"))
        audio_stream = AudioStream(gst.Caps("audio/x-raw-int"))
        source1 = FileSourceFactory("file1.ogg")
        source1.addOutputStream(video_stream)

        # these two calls are needed to populate the context for the -ref
        # elements
        self.formatter._saveSource(source1)
        self.formatter._saveStream(video_stream)

        track_object = SourceTrackObject(source1, video_stream,
                start=10 * gst.SECOND, duration=20 * gst.SECOND,
                in_point=5 * gst.SECOND, media_duration=15 * gst.SECOND,
                priority=10)
        track = Track(video_stream)
        track.addTrackObject(track_object)

        element = self.formatter._saveTrackObject(track_object)
        element_ref = self.formatter._saveTrackObjectRef(track_object)
        self.failUnlessEqual(element_ref.tag, "track-object-ref")
        self.failUnlessEqual(element.attrib["id"], element.attrib["id"])

    def testSaveTrack(self):
        video_stream = VideoStream(gst.Caps("video/x-raw-yuv"))
        audio_stream = AudioStream(gst.Caps("audio/x-raw-int"))
        source1 = VideoTestSourceFactory()

        # these two calls are needed to populate the context for the -ref
        # elements
        self.formatter._saveSource(source1)
        self.formatter._saveStream(video_stream)

        track_object = SourceTrackObject(source1, video_stream,
                start=10 * gst.SECOND, duration=20 * gst.SECOND,
                in_point=5 * gst.SECOND, media_duration=15 * gst.SECOND,
                priority=10)

        track = Track(video_stream)
        track.addTrackObject(track_object)

        element = self.formatter._saveTrack(track)
        self.failUnlessEqual(element.tag, "track")
        track_objects_element = element.find("track-objects")
        self.failUnlessEqual(len(track_objects_element), 1)

    def testSaveTimelineObject(self):
        video_stream = VideoStream(gst.Caps("video/x-raw-yuv"))
        audio_stream = AudioStream(gst.Caps("audio/x-raw-int"))
        source1 = FileSourceFactory("file1.ogg")
        source1.addOutputStream(video_stream)

        # these two calls are needed to populate the context for the -ref
        # elements
        self.formatter._saveSource(source1)
        self.formatter._saveStream(video_stream)

        track_object = SourceTrackObject(source1, video_stream,
                start=10 * gst.SECOND, duration=20 * gst.SECOND,
                in_point=5 * gst.SECOND, media_duration=15 * gst.SECOND,
                priority=10)
        track = Track(video_stream)
        track.addTrackObject(track_object)

        self.formatter._saveTrackObject(track_object)

        timeline_object = TimelineObject(source1)
        timeline_object.addTrackObject(track_object)

        element = self.formatter._saveTimelineObject(timeline_object)
        self.failUnlessEqual(element.tag, "timeline-object")
        self.failIfEqual(element.find("factory-ref"), None)
        track_object_refs = element.find("track-object-refs")
        self.failUnlessEqual(len(track_object_refs), 1)

    def testSavetimelineObjects(self):
        video_stream = VideoStream(gst.Caps("video/x-raw-yuv"))
        audio_stream = AudioStream(gst.Caps("audio/x-raw-int"))
        source1 = FileSourceFactory("file1.ogg")
        source1.addOutputStream(video_stream)

        # these two calls are needed to populate the context for the -ref
        # elements
        self.formatter._saveSource(source1)
        self.formatter._saveStream(video_stream)

        track_object = SourceTrackObject(source1, video_stream,
                start=10 * gst.SECOND, duration=20 * gst.SECOND,
                in_point=5 * gst.SECOND, media_duration=15 * gst.SECOND,
                priority=10)
        track = Track(video_stream)
        track.addTrackObject(track_object)
        self.formatter._saveTrackObject(track_object)

        timeline_object = TimelineObject(source1)
        timeline_object.addTrackObject(track_object)

        element = self.formatter._saveTimelineObjects([timeline_object])
        self.failUnlessEqual(len(element), 1)

    def testSaveTimeline(self):
        video_stream = VideoStream(gst.Caps("video/x-raw-yuv"))
        audio_stream = AudioStream(gst.Caps("audio/x-raw-int"))
        source1 = VideoTestSourceFactory()
        source1.addOutputStream(video_stream)

        self.formatter._saveSource(source1)
        self.formatter._saveStream(video_stream)

        track_object = SourceTrackObject(source1, video_stream,
                start=10 * gst.SECOND, duration=20 * gst.SECOND,
                in_point=5 * gst.SECOND, media_duration=15 * gst.SECOND,
                priority=10)

        track = Track(video_stream)
        track.addTrackObject(track_object)

        self.formatter._saveTrackObject(track_object)

        timeline_object = TimelineObject(source1)
        timeline_object.addTrackObject(track_object)

        self.formatter._saveTimelineObject(timeline_object)

        timeline = Timeline()
        timeline.addTrack(track)

        element = self.formatter._saveTimeline(timeline)
        self.failUnlessEqual(element.tag, "timeline")
        tracks = element.find("tracks")
        self.failUnlessEqual(len(tracks), 1)

    def testSaveMainTag(self):
        element = self.formatter._saveMainTag()
        self.failUnlessEqual(element.tag, "pitivi")
        self.failUnlessEqual(element.attrib["formatter"], "etree")
        self.failUnlessEqual(element.attrib["version"], version)

    def testSaveProject(self):
        video_stream = VideoStream(gst.Caps("video/x-raw-yuv"))
        audio_stream = AudioStream(gst.Caps("audio/x-raw-int"))
        source1 = VideoTestSourceFactory()

        self.formatter._saveSource(source1)
        self.formatter._saveStream(video_stream)

        track_object = SourceTrackObject(source1, video_stream,
                start=10 * gst.SECOND, duration=20 * gst.SECOND,
                in_point=5 * gst.SECOND, media_duration=15 * gst.SECOND,
                priority=10)

        track = Track(video_stream)
        track.addTrackObject(track_object)

        self.formatter._saveTrackObject(track_object)

        timeline_object = TimelineObject(source1)
        timeline_object.addTrackObject(track_object)

        self.formatter._saveTimelineObject(timeline_object)

        timeline = Timeline()
        timeline.addTrack(track)

        self.formatter._saveTimeline(timeline)

        project = Project()
        project.timeline = timeline
        project.sources.addFactory(source1)

        element = self.formatter._serializeProject(project)

        self.failUnlessEqual(element.tag, "pitivi")
        self.failIfEqual(element.find("factories"), None)
        self.failIfEqual(element.find("timeline"), None)


class TestFormatterLoad(TestCase):
    def setUp(self):
        self.formatter = FakeElementTreeFormatter(EffectsHandler())

    def testLoadStream(self):
        caps = gst.Caps("video/x-raw-yuv")
        element = Element("stream")
        element.attrib["id"] = "1"
        element.attrib["type"] = "pitivi.stream.VideoStream"
        element.attrib["caps"] = str(caps)

        stream = self.formatter._loadStream(element)
        self.failUnlessEqual(qual(stream.__class__), element.attrib["type"])
        self.failUnlessEqual(str(stream.caps), str(caps))
        self.failUnlessEqual(stream, self.formatter._context.streams["1"])

    def testLoadTrackEffect(self):
        # create fake document tree
        element = Element("track-object",\
                type="pitivi.timeline.track.TrackEffect",
                start=ts(1 * gst.SECOND), duration=ts(10 * gst.SECOND),
                in_point=ts(5 * gst.SECOND),
                media_duration=ts(15 * gst.SECOND), priority=ts(5), id="1")
        effect_elem = SubElement(element, "effect")
        factory_elem = SubElement(effect_elem, "factory", name="identity")
        properties_elem = SubElement(effect_elem, "gst-element-properties", sync="(bool)True")

        # insert our fake factory into the context
        stream = AudioStream(gst.Caps("audio/x-raw-int"))
        factory = EffectFactory('identity')
        factory.addInputStream(stream)
        factory.addOutputStream(stream)
        self.formatter.avalaible_effects._effect_factories_dict['identity'] = factory

        track = Track(stream)
        track_object = self.formatter._loadTrackObject(track, element)
        self.failUnless(isinstance(track_object, TrackEffect))
        self.failUnlessEqual(track_object.factory, factory)
        self.failUnlessEqual(track_object.stream, stream)

        self.failUnlessEqual(track_object.start, 1 * gst.SECOND)
        self.failUnlessEqual(track_object.duration, 10 * gst.SECOND)
        self.failUnlessEqual(track_object.in_point, 5 * gst.SECOND)
        self.failUnlessEqual(track_object.media_duration, 15 * gst.SECOND)
        self.failUnlessEqual(track_object.priority, 5)

    def testLoadStreamRef(self):
        stream = VideoStream(gst.Caps("meh"))
        self.formatter._context.streams["1"] = stream
        element = Element("stream-ref")
        element.attrib["id"] = "1"
        stream1 = self.formatter._loadStreamRef(element)
        self.failUnlessEqual(stream, stream1)

    def testLoadFactory(self):
        element = Element("source")
        element.attrib["id"] = "1"
        element.attrib["type"] = "pitivi.factories.test.VideoTestSourceFactory"
        element.attrib["duration"] = 5 * gst.SECOND
        element.attrib["default_duration"] = 5 * gst.SECOND
        output_streams = SubElement(element, "output-streams")
        output_stream = SubElement(output_streams, "stream")
        caps = gst.Caps("video/x-raw-yuv")
        output_stream.attrib["id"] = "1"
        output_stream.attrib["type"] = "pitivi.stream.VideoStream"
        output_stream.attrib["caps"] = str(caps)

        factory = self.formatter._loadFactory(element)
        self.failUnless(isinstance(factory, VideoTestSourceFactory))
        self.failUnlessEqual(len(factory.output_streams), 2)

        self.failUnlessEqual(self.formatter._context.factories["1"], factory)
        self.failUnlessEqual(factory.duration, 5 * gst.SECOND)
        self.failUnlessEqual(factory.default_duration, 5 * gst.SECOND)

    def testLoadFactoryRef(self):
        class Tag(object): pass
        tag = Tag()
        self.formatter._context.factories["1"] = tag
        element = Element("factory-ref", id="1")
        ret = self.formatter._loadFactoryRef(element)
        self.failUnless(ret is tag)

    def testLoadTrackSource(self):
        # create fake document tree
        element = Element("track-object",
                type="pitivi.timeline.track.SourceTrackObject",
                start=ts(1 * gst.SECOND), duration=ts(10 * gst.SECOND),
                in_point=ts(5 * gst.SECOND),
                media_duration=ts(15 * gst.SECOND), priority=ts(5), id="1")
        factory_ref = SubElement(element, "factory-ref", id="1")
        stream_ref = SubElement(element, "stream-ref", id="1")

        # insert our fake factory into the context
        factory = AudioTestSourceFactory()
        factory.duration = 10 * gst.SECOND
        self.formatter._context.factories["1"] = factory

        # insert fake stream into the context
        stream = AudioStream(gst.Caps("audio/x-raw-int"))
        self.formatter._context.streams["1"] = stream

        # add a volume curve
        curves = SubElement(element, "curves")
        curve = SubElement(curves, "curve", property="volume",
            version="1")
        expected = dict((long(t * gst.SECOND), (float(t % 2), gst.INTERPOLATE_LINEAR))
            for t in xrange(1, 10))
        start = SubElement(curve, "start", value="0.0", mode="2")
        for time, (value, mode) in expected.iteritems():
            SubElement(curve, "keyframe", time=str(time), value=str(value),
                mode=str(mode))
        end = SubElement(curve, "end", value=str(10 % 2), mode="2")

        track = Track(stream)
        # point gun at foot; pull trigger
        track_object = self.formatter._loadTrackObject(track, element)
        self.failUnless(isinstance(track_object, SourceTrackObject))
        self.failUnlessEqual(track_object.factory, factory)
        self.failUnlessEqual(track_object.stream, stream)

        self.failUnlessEqual(track_object.start, 1 * gst.SECOND)
        self.failUnlessEqual(track_object.duration, 10 * gst.SECOND)
        self.failUnlessEqual(track_object.in_point, 5 * gst.SECOND)
        self.failUnlessEqual(track_object.media_duration, 15 * gst.SECOND)
        self.failUnlessEqual(track_object.priority, 5)

        self.failIfEqual(track_object.interpolators, None)
        interpolator = track_object.getInterpolator("volume")
        self.failIfEqual(interpolator, None)
        curve = dict(((kf.time, (kf.value, kf.mode)) for kf in
            interpolator.getInteriorKeyframes()))
        self.failUnlessEqual(curve, expected)

        self.failUnlessEqual(interpolator.start.value, 0.0)
        self.failUnlessEqual(interpolator.start.time, 5 * gst.SECOND)
        self.failUnlessEqual(interpolator.end.value, 0.0)
        self.failUnlessEqual(interpolator.end.time, 15 * gst.SECOND)

    def testLoadInterpolatorV0(self):
        # create fake document tree
        element = Element("track-object",
                type="pitivi.timeline.track.SourceTrackObject",
                start=ts(1 * gst.SECOND), duration=ts(15 * gst.SECOND),
                in_point=ts(5 * gst.SECOND),
                media_duration=ts(15 * gst.SECOND), priority=ts(5), id="1")
        factory_ref = SubElement(element, "factory-ref", id="1")
        stream_ref = SubElement(element, "stream-ref", id="1")

        # insert our fake factory into the context
        factory = AudioTestSourceFactory()
        factory.duration = 20 * gst.SECOND
        self.formatter._context.factories["1"] = factory

        # insert fake stream into the context
        stream = AudioStream(gst.Caps("audio/x-raw-int"))
        self.formatter._context.streams["1"] = stream

        # add a volume curve
        curves = SubElement(element, "curves")
        curve = SubElement(curves, "curve", property="volume")
        expected = dict((long(t * gst.SECOND), (float(t % 2), gst.INTERPOLATE_LINEAR))
            for t in xrange(6, 15))
        start = SubElement(curve, "start", value="1.0", mode="2")
        for time, (value, mode) in expected.iteritems():
            SubElement(curve, "keyframe", time=str(time), value=str(value),
                mode=str(mode))
        end = SubElement(curve, "end", value="1.0", mode="2")

        track = Track(stream)
        # point gun at foot; pull trigger
        track_object = self.formatter._loadTrackObject(track, element)
        self.failIfEqual(track_object.interpolators, None)
        interpolator = track_object.getInterpolator("volume")
        self.failIfEqual(interpolator, None)
        curve = dict(((kf.time, (kf.value, kf.mode)) for kf in
            interpolator.getInteriorKeyframes()))
        self.failUnlessEqual(curve, expected)

        # check that start keyframe value has been properly adjusted so as not
        # to change the shape of the curve. rounding is applied here because
        # the controller seems to round to a different precision
        # than python. we just want to check that the value is "in the
        # ballpark", indicating the keyframes have been updated. If you do the
        # math you'll see that both start and end keyframe values should be
        # about 1/6
        self.failUnlessEqual(
            round(interpolator.start.value, 6),
            round((-5.0 / 6) + 1, 6))
        self.failUnlessEqual(interpolator.start.time, 5 * gst.SECOND)

        # check that end keyrame value has been properly adjusted so as not to
        # change the shape of the curve
        self.failUnlessEqual(interpolator.end.time, 15 * gst.SECOND)
        self.failUnlessEqual(
            round(interpolator.end.value, 6),
            round((15.0 / 6) - (7.0/3), 6))


    def testLoadTrackObjectRef(self):
        class Tag(object):
            pass
        tag = Tag()
        self.formatter._context.track_objects["1"] = tag
        element = Element("track-object-ref", id="1")
        ret = self.formatter._loadTrackObjectRef(element)
        self.failUnless(ret is tag)

    def testLoadTrack(self):
        # create fake document tree
        element = Element("track")
        stream_element = SubElement(element, "stream", id="1",
                type="pitivi.stream.VideoStream", caps="video/x-raw-rgb")

        track_objects_element = SubElement(element, "track-objects")
        track_object = SubElement(track_objects_element, "track-object",
                type="pitivi.timeline.track.SourceTrackObject",
                start=ts(1 * gst.SECOND), duration=ts(10 * gst.SECOND),
                in_point=ts(5 * gst.SECOND),
                media_duration=ts(15 * gst.SECOND), priority=ts(5), id="1")
        factory_ref = SubElement(track_object, "factory-ref", id="1")
        stream_ref = SubElement(track_object, "stream-ref", id="1")

        # insert fake factories and streams into current context
        factory = VideoTestSourceFactory()
        self.formatter._context.factories["1"] = factory
        stream = VideoStream(gst.Caps("video/x-raw-rgb"))
        self.formatter._context.streams["1"] = stream

        # point gun at foot; pull trigger
        track = self.formatter._loadTrack(element)

        self.failUnlessEqual(len(track.track_objects), 1)
        # FIXME: this is an hack
        self.failUnlessEqual(str(track.stream), str(stream))

    def testLoadTimelineObject(self):
        video_stream = VideoStream(gst.Caps("video/x-raw-yuv"))
        source1 = VideoTestSourceFactory()
        self.formatter._context.factories["1"] = source1
        self.formatter._context.track_objects["1"] = SourceTrackObject(source1, video_stream)

        element = Element("timeline-object")
        factory_ref = SubElement(element, "factory-ref", id="1")
        stream_ref = SubElement(element, "stream-ref", id="1")
        track_object_refs = SubElement(element, "track-object-refs")
        track_object_ref = SubElement(track_object_refs,
                "track-object-ref", id="1")

        timeline_object = \
                self.formatter._loadTimelineObject(element)

        self.failUnlessEqual(timeline_object.factory, source1)
        self.failUnlessEqual(len(timeline_object.track_objects), 1)

    def testLoadTimeline(self):
        # we need a project for this to work
        self.formatter.project = Project()

        # create fake document tree
        timeline_element = Element("timeline")

        tracks_element = SubElement(timeline_element, "tracks")
        track_element = SubElement(tracks_element, "track")
        stream_element = SubElement(track_element, "stream", id="1",
                type="pitivi.stream.VideoStream", caps="video/x-raw-rgb")
        track_objects_element = SubElement(track_element, "track-objects")
        track_object = SubElement(track_objects_element, "track-object",
                type="pitivi.timeline.track.SourceTrackObject",
                start=ts(1 * gst.SECOND), duration=ts(10 * gst.SECOND),
                in_point=ts(5 * gst.SECOND),
                media_duration=ts(15 * gst.SECOND), priority=ts(5), id="1")
        factory_ref = SubElement(track_object, "factory-ref", id="1")
        stream_ref = SubElement(track_object, "stream-ref", id="1")
        timeline_objects_element = SubElement(timeline_element,
                "timeline-objects")
        timeline_object_element = \
                SubElement(timeline_objects_element, "timeline-object")
        factory_ref = SubElement(timeline_object_element, "factory-ref", id="1")
        stream_ref = SubElement(timeline_object_element, "stream-ref", id="1")
        track_object_refs = SubElement(timeline_object_element, "track-object-refs")
        track_object_ref = SubElement(track_object_refs,
                "track-object-ref", id="1")

        # insert fake streams and factories into context
        factory = VideoTestSourceFactory()
        self.formatter._context.factories["1"] = factory
        stream = VideoStream(gst.Caps("video/x-raw-rgb"))
        self.formatter._context.streams["1"] = stream
        video_stream = VideoStream(gst.Caps("video/x-raw-yuv"))
        source1 = VideoTestSourceFactory()
        self.formatter._context.factories["2"] = source1
        self.formatter._context.track_objects["1"] = SourceTrackObject(source1, video_stream)


        # point gun at foot; pull trigger
        self.formatter._loadTimeline(timeline_element)
        self.failUnlessEqual(len(self.formatter.project.timeline.tracks), 1)

    def testLoadProject(self):
        video_stream = VideoStream(gst.Caps("video/x-raw-yuv"))
        audio_stream = AudioStream(gst.Caps("audio/x-raw-int"))
        source1 = VideoTestSourceFactory()

        self.formatter._saveSource(source1)
        self.formatter._saveStream(video_stream)

        track_object = SourceTrackObject(source1, video_stream,
                start=10 * gst.SECOND, duration=20 * gst.SECOND,
                in_point=5 * gst.SECOND, media_duration=15 * gst.SECOND,
                priority=10)

        track = Track(video_stream)
        track.addTrackObject(track_object)

        self.formatter._saveTrackObject(track_object)

        timeline_object = TimelineObject(source1)
        timeline_object.addTrackObject(track_object)

        self.formatter._saveTimelineObject(timeline_object)

        timeline = Timeline()
        timeline.addTrack(track)

        self.formatter._saveTimeline(timeline)

        project = Project()
        project.timeline = timeline
        project.sources.addFactory(source1)

        element = self.formatter._serializeProject(project)

        self.failUnlessEqual(element.tag, "pitivi")
        self.failIfEqual(element.find("factories"), None)
        self.failIfEqual(element.find("timeline"), None)

        indent(element)
        f = file("/tmp/untitled.pptv", "w")
        f.write(tostring(element))
        f.close()

    ## following test is disabled until I figure out a better way of
    ## testing the mapping system.
#     def testDirectoryMapping(self):
#         pa = "file:///if/you/have/this/file/you/are/on/crack.avi"
#         pb = "file:///I/really/mean/it/you/crack.avi"

#         self.formatter.addMapping(pa,pb)
#         self.assertEquals(self.formatter.validateSourceURI(pa),
#                           pb)
