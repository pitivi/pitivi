# Preamble

Although video editors are complex by nature, the information they need
to create a timeline is rather lightweight compared to the data they
process. There is therefore no need to create a memory-efficient and/or
binary file format. It is more important to have an format which is
**easy to parse and extensible**, an **XML-based** format is therefore
chosen.

# Requirements

The various information we need to store can be summarized in 3
categories:

-   **Global project information**
    -   metadata: title, comment, revision history, authors, ...
    -   sources, ...
    -   export settings, ...
    -   ...
-   **Timeline specific information**
    -   tracks, layers
    -   layout of sources/effects/transitions,
    -   ...
-   **Extensions information**
    -   Parsing/Serializing done by extension plugins.

# Specification

# Implementation sample

**This page was a draft from 2007**. It badly needs to be updated. Help
welcome!

``` xml
<?xml version="1.0"?>
<project xmlns='http://www.pitivi.org/projectxml'>
    <formatversion>1</formatversion>
    <title>Insane video</title>
    <comment>
        This is my very first video done with PiTiVi.
    </comment>
    <authors>
        <author id="0" name="Edward Hervey" />
        <author id="1" name="George Lucas" />
    </authors>
    <history>
        <revision id="0" date="Mon 25 Sep 2006 12:00" who="0" >Initial version</revision>
        <revision id="1" date="Mon 25 Sep 2006 12:25" who="1" />
    </history>
    <sources>
    </sources>
    <timeline>
        <composition type="video">
            <transitions>
                <transition type="fade" start="2000000000" duration="2000000000" />
            </transitions>
            <sources>{startFrom="0"}</sources>
        </composition>
        <composition type="audio">
            <transitions>
                <transition start="2000000000" duration="200000000" />
            </transitions>
        </composition>
    </timeline>
</project>
```
