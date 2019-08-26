# Browsers

`Browser`s are meant to assist in three things:

-   Media Asset Management, here called **Content Browsers**,
-   Operation Management, here called **Operation Browsers**,
-   Device Management, here called **Device Browsers**

All `Browser`s produce/consume ObjectFactory in output/input . They are
the main providers/consumers (along with
[Formatter](design/2008_design/2008_Architectural_Redesign/Formatter.md
)) for ObjectFactory
anywhere else in the Application.

New types of `Browsers` can be created through the plugin interface to:

-   Offer access to a new type of MAM (for storing/retrieving/searching
    content)
-   Offer discoverability of devices through a new system (HAL doesn't
    exist on windows !)
-   ...

# Browser types

## Content Browsers

These Browsers can be listed individually for access to specific
services.

They only return content of type `SourceFactory`

-   Local content
    -   `file://` (standard system)
    -   F-Spot catalog browsing
    -   Tracker
    -   ...
-   Remote content
    -   Tape catalog, or any other kind of professional MAM system
    -   Flickr
    -   Youtube
    -   ...

These browsers MUST offer at least the following functionality:

-   `getFactory(`*`uri`*`)` , returns the `ObjectFactory` for the given
    uri.

The browsers CAN also offer these functionality:

-   `storeFactory(`*`factory`*`, `*`uri`*`)`, stores the given
    `ObjectFactory` with the given uri. It returns an `ObjectFactory`
    which might be the same as the input, or a new one, or a a temporary
    new one.
-   Searching/Browsing functionalities

Browsers should use the **UI Bundle** system to provide adequate UI
interfaces if needed.

## Operation Browser

They only return content of type `OperationFactory`.

The default implementation will just look for all available GstElement
of a given type and return simple OperationFactory objects wrapping
them.

Another implementation will be in charge of handling all the pitivi
plugins providing different OperationFactory.

## Device Browser

Only returns content of type `DeviceFactoryInterface`.

It MUST provide the following functionality:

-   `getDefaultSinks()` , which should return the default usable
    SinkDeviceFactory.
-   `getDefaultSources()`, which should return the default usable
    SourceDeviceFactory.
