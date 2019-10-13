# PyGST Tutorial/States, and the Bus

The material in this section may not seem all that exciting, but serves
as the foundation for more interesting topics. Hopefully now that I've
captured your attention with a few sexy examples, we can get through
this rather dreary subject. In this tutorial, we explore *element
state*and the *element life-cycle*. We will also examine the *message
bus* in further detail, and how this relates to tracking state changes.
Finally, will use this information to polish up our demonstration
framework.

# States

There are four element states: `gst.STATE_NULL`, `gst.STATE_READY`,
`gst.STATE_PAUSED`, and `gst.STATE_PLAYING`. The distinction between
`NULL` and `READY` states deserve some explanation.

`gst.STATE_NULL`

:   when state is null resources needed for a gst.Element have not been
    loaded, these can be libraries, devices etc. This is the first state
    of any gst.Element.

`gst.STATE_READY`

:   when state is ready resources have been allocated, and the
    gst.Element is ready to be used.

`gst.STATE_PAUSED`

:

`gst.STATE_PLAYING`

:

## The element life-cycle

![](element_lifecycle.png "element_lifecycle.png")

The above illustration summarizes the element life-cycle.

## Dataflow and Blocking

So far, we've only talked about *element state*. However, *pads* also
have state. Pads can be either *blocked* or *unblocked*. In order for a
pipeline to transition into the playing state, all the pads of all the
elements in the pipeline must be in the *unblocked* state.

## Adding a Pause Button

[source for this example](enhanced_demo.py.md)

Let's use what we've learned to modify demo.py to add a *pause* button.

First, add the pause button to the UI layout:

        def createWindow(self):

        ...

            # declare buttons and their associated handlers
            controls = (
                ("play_button", gtk.ToolButton(gtk.STOCK_MEDIA_PLAY), self.onPlay),
                ("pause_button", gtk.ToolButton(gtk.STOCK_MEDIA_PAUSE), self.onPause),
                ("stop_button", gtk.ToolButton(gtk.STOCK_MEDIA_STOP), self.onStop),
                ("quit_button", gtk.ToolButton(gtk.STOCK_QUIT), gtk.main_quit)
            )

        ...

Next, define the `onPause()` handler. This handler simply sets the
pipeline state to the `gst.PAUSED` state.

        def onPause(self, unused_button):
            self.pipeline.set_state(gst.STATE_PAUSED)

[source for this example](enhanced_demo.py.md)

## Running this Example

This example serves as a drop-in replacement for our original `demo.py`.
You can run this file stand-alone, but it will be more interesting to
save it as `demo.py` and re-run the previous examples.

# The Bus

We have seen the Bus before. Remember this code from the first example?

            # this code receives the messages from the pipeline. if we
            # need to set X11 id, then we call set_xid
            def bus_handler(unused_bus, message):
                if message.type == gst.MESSAGE_ELEMENT:
                    if message.structure.get_name() == 'prepare-xwindow-id':
                        set_xid(w)
                return gst.BUS_PASS

            # create our pipeline, and connect our bus_handler
            self.pipeline = gst.Pipeline()
            bus = self.pipeline.get_bus()
            bus.set_sync_handler(bus_handler)

The bus is one mechanism that GStreamer pipelines use to communicate
with the application. Elements can post messages onto the Bus from any
thread, and the messages will be received by the application's main
thread. Handling bus messages is central to many aspects of GStreamer
application development, including tracking state changes.

## Connecting to the Bus

There are three ways to connect to the bus: with a *watch*, a *signal
watch*, and a *sync handler*.

-   A watch is a simple call back, which you register by calling
    `Bus.add_watch()`.
-   If you need more flexibility, add a signal watch by calling
    `Bus.add_signal_watch()`. This causes the bus to emit the `message`
    signal, which you can connect to. The `message` signal is not
    emitted unless you call `add_signal_watch()`
-   If you want to receive bus messages in the same thread from which
    they are posted, call `Bus.set_sync_handler`. You should probably
    avoid this method unless you understand how to to write
    multi-threaded code.

## Messages

There are many message types, including the `gst.MESSAGE_ELEMENT` shown
above. Here's a list of some common ones, and what they mean:

  Message Type                  Meaning
  ----------------------------- -----------------------------------------------
  `gst.MESSAGE_ELEMENT`         message type for element-specific information
  `gst.MESSAGE_EOS`             the end of the pipeline has been reached
  `gst.MESSAGE_ERROR`           a pipeline error has occurred
  `gst.MESSAGE_SEGMENT_DONE`    the pipeline has completed a *segment seek*
  `gst.MESSAGE_STATE_CHANGED`   an element's state has changed
  `gst.MESSAGE_TAG`             meta-data has been decoded from the stream

We'll talk more about that last message, `gst.MESSAGE_SEGMENT_DONE`, in
the next article.

The `gst.Message` object is generic, and information is extracted using
the `parse_*()` set of functions depending on the message type. For
example, to parse the `gst.MESSAGE_STATE_CHANGED` message, use the
`parse_state_changed()` method. You may also need to access the
message's `structure` attribute directly (as we must to do set the
`ximagesink` element's `xwindow_id`).

## Providing State-Change Feedback

Let's use what we've learned to provide feedback to the user about state
changes. We want the sensitivity of the playback controls to reflect the
current state of the pipeline.

[source for this example](enhanced_demo.py.md)

The following table summarizes the sensitivity that Play, Pause, and
Stop buttons should have in each of the GStreamer states.

  State                 Play Button   Pause Button   Stop Button
  --------------------- ------------- -------------- -------------
  `gst.STATE_NULL`      Sensitive     Insensitive    Insensitive
  `gst.STATE_READY`     Sensitive     Insensitive    Insensitive
  `gst.STATE_PAUSED`    Sensitive     Insensitive    Sensitive
  `gst.STATE_PLAYING`   Insensitive   Sensitive      Sensitive

This is easily translated into an else-if chain. What we will do is
update the sensitivity of all the buttons according to this chart when
we get a state-changed message.

        def updateButtons(self, state):
            if state == gst.STATE_NULL:
                self.play_button.set_sensitive(True)
                self.pause_button.set_sensitive(False)
                self.stop_button.set_sensitive(False)
            elif state == gst.STATE_READY:
                self.play_button.set_sensitive(True)
                self.pause_button.set_sensitive(False)
                self.stop_button.set_sensitive(False)
            elif state == gst.STATE_PAUSED:
                self.play_button.set_sensitive(True)
                self.pause_button.set_sensitive(False)
                self.stop_button.set_sensitive(True)
            elif state == gst.STATE_PLAYING:
                self.play_button.set_sensitive(False)
                self.pause_button.set_sensitive(True)
                self.stop_button.set_sensitive(True)

Now, we just need to look for the `gst.MESSAGE_STATE_CHANGED` message on
the bus, and call `updateButtons` with the new state. First let's define
our message handler:

         def messageCb(self, bus, message):
            if message.type == gst.MESSAGE_STATE_CHANGED:
                old, new, pending = message.parse_state_changed()
                self.updateButtons(new)
            return gst.BUS_PASS

We want to receive these element messages in the main thread, since we
are using the information to update the UI. Therefore, we modify
`createPipeline()` to connect to our message handler as a bus watch.

One last detail: update the state of the buttons with the null state in
`createWindow()`

[source for this example](enhanced_demo.py.md)

## Running this Example

This example serves as a drop-in replacement for our original `demo.py`.
You can run this file stand-alone, but it will be more interesting to
save it as `demo.py` and re-run the previous examples.

## Handling Pipeline Errors

Our demonstration framework has not done any error handling to speak of.
Let's fix that.
