# ObjectFactory

**ObjectFactory are the descriptions of objects producing and/or
consuming data streams.**

-   They contain a list of the Stream(s) they can produce and/or
    consume.

This implies **ALL** The potential streams the factory can
provide/consume.

Ex: A **FileSourceFactory** of a raw DV File will list the following
streams:

-   `video/x-dv,systemstream=True`, The container stream,
-   `video/x-dv,systemstream=False`, The I-Frame only DV video stream,
-   `video/x-raw-yuv`, The decoded raw video stream
-   `audio/x-raw-int`, The audio stream

-   They produce GStreamer elements for all, or a selected number of,
    streams.

Some factories will be able to produce a different GStreamer element
every time, some will only be able to produce one at a time (Ex:
Video4Linux source, or audio sink with retarded backend that can have
multiple sockets opened).

## Properties

-   `Name`, unique for that given ObjectFactory instance type.
-   `InputStreams`, a list of Stream(s) the given factory can consume.
    Empty for SourceFactory.
-   `OutputStreams`, a list of Stream(s) the given factory can produce.
    Empty for SinkFactory.

## Class Properties

-   `Description` , a description of the ObjectFactory

## Methods

-   `makeBin(streams=[])`, returns a gst.Bin for the given Streams. If
    no Streams are specified, then a gst.Bin for all the available
    streams is returned. If only one Stream is specified, then the
    gst.Bin returned will not contain any `queue` in it.

# Examples

## FileSource

Describes the properties of a file specified by:

-   A URI
-   A list of streams the file can provide (This information can come
    from the Discoverer, or some other source)
-   Metadata regarding the file

This might be one of the most commonly used ObjectFactory. A single
instance of a FileSourceFactory can be used for:

-   Previewing the file
-   Using it many times in the timeline (which have different position,
    in/out points, streams used, etc...)

## SourceDeviceFactory

Describes a Hardware Device that can produce streams. This ObjectFactory
will most likely be provided by the HardwareBrowser.

-   A description of the hardware
-   A list of streams it can provide (An local SoundCard could provide
    several streams if it has several inputs).

This will be used most likely when recording or capturing.

## OperationFactory

Describes any kind of operation, which can be an A/V Effect, an Encoding
container, or even a Hardware processing effect (like OpenGL powered),
or even more complex effect.

-   A list of streams it can process
-   A list of resulting streams it can/will output

# Interfaces

## LinkedFactoryInterface

This allows aggregating streams from various factories at the same time,
with an eventual offset between each streams.

### Examples

-   Audio and Video captured on separate devices during a shoot. We
    could link all those separate A/V content into one source, allowing
    fixing of synchronization, and then be usable as one item in a
    timeline.

<!-- -->

-   LocalSourceDevicesFactory : SourceDeviceFactory aggregating all
    available LocalSourceDevice on the current system. We can then
    easily switch between the various devices, while keeping track of
    one consistent object.

<!-- -->

-   LocalSinkDevicesFactory : Same as above but for all available A/V
    sinks on the device.

<!-- -->

-   LinkedOperationFactory : Synchronized effect for use in the
    pipeline. Imagine a 'thunder' effect that has synchronized audio and
    video effect.

<!-- -->

-   MultipleQualitySourceFactory : SourceFactory that can provide a
    variety of different 'qualities' off the content. This could enable
    switching between a lower-quality (fast for editing) and a
    higher-quality (needed for final rendering).

## GroupedFactoryInterface

This allows creation groupings of different factories with:

-   time offsets for each factory,
-   different in-out points per factory,
-   priorities of placement of each factory

# Ideas

Maybe we should have a way to specify the properties/methods/... of some
of these use-case:

-   OnlineFactoryInterface : For sources (or sinks/destinations) which
    correspond to non-local content, which requires doing an action
    (Download/Upload) to get/use a local content. Ex : Youtube sources,
    which requires downloading a local copy to edit it. DV VCR, which
    requires doing a capture.

<!-- -->

-   LiveFactoryInterface : This applies to all factories that only
    consumes/processes/produces live. Ex: a Webcam source, or a
    StreamingSink. They too require a 'record' phase in order to produce
    a local, editable, copy.

![ObjectFactory
hierarchy](Objectfactory-hierarchy.png "ObjectFactory hierarchy")
