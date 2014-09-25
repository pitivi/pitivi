# Pitivi video editor
#
#       pitivi/titleeditor.py
#
# Copyright (c) 2012, Matas Brazdeikis <matas@brazdeikis.lt>
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

import os

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import Pango
from gi.repository import GES
from gi.repository import Gst
from gi.repository import GLib

from gettext import gettext as _

from pitivi.configure import get_ui_dir
from pitivi.utils.loggable import Loggable
from pitivi.utils.pipeline import Seeker
from pitivi.utils.timeline import SELECT
from pitivi.utils.ui import argb_to_gdk_rgba, gdk_rgba_to_argb


FOREGROUND_DEFAULT_COLOR = 0xFFFFFFFF  # White
BACKGROUND_DEFAULT_COLOR = 0x00000000  # Transparent


class TitleEditor(Loggable):

    """
    Widget for configuring the selected title.

    @type app: L{Pitivi}
    """

    def __init__(self, app):
        Loggable.__init__(self)
        self.app = app
        self.settings = {}
        self.source = None
        self.seeker = Seeker()

        # Drag attributes
        self._drag_events = []
        self._signals_connected = False

        self._createUI()

    def _createUI(self):
        builder = Gtk.Builder()
        builder.add_from_file(os.path.join(get_ui_dir(), "titleeditor.ui"))
        builder.connect_signals(self)
        self.widget = builder.get_object("box1")  # To be used by tabsmanager
        self.infobar = builder.get_object("infobar")
        self.editing_box = builder.get_object("editing_box")
        self.textarea = builder.get_object("textview")
        toolbar = builder.get_object("toolbar")
        toolbar.get_style_context().add_class(Gtk.STYLE_CLASS_INLINE_TOOLBAR)

        self.textbuffer = Gtk.TextBuffer()
        self.textarea.set_buffer(self.textbuffer)
        self.textbuffer.connect("changed", self._updateSourceText)

        self.font_button = builder.get_object("fontbutton1")
        self.foreground_color_button = builder.get_object("fore_text_color")
        self.background_color_button = builder.get_object("back_color")

        settings = ["valignment", "halignment", "xpos", "ypos"]
        for setting in settings:
            self.settings[setting] = builder.get_object(setting)

        for n, en in list({_("Custom"): "position",
                           _("Top"): "top",
                           _("Center"): "center",
                           _("Bottom"): "bottom",
                           _("Baseline"): "baseline"}.items()):
            self.settings["valignment"].append(en, n)

        for n, en in list({_("Custom"): "position",
                           _("Left"): "left",
                           _("Center"): "center",
                           _("Right"): "right"}.items()):
            self.settings["halignment"].append(en, n)
        self._deactivate()

    def _backgroundColorButtonCb(self, widget):
        color = gdk_rgba_to_argb(widget.get_rgba())
        self.debug("Setting title background color to %x", color)
        self.source.set_background(color)
        self.seeker.flush()

    def _frontTextColorButtonCb(self, widget):
        color = gdk_rgba_to_argb(widget.get_rgba())
        self.debug("Setting title foreground color to %x", color)
        # TODO: Use set_text_color when we work with TitleSources instead of
        # TitleClips
        self.source.set_color(color)
        self.seeker.flush()

    def _fontButtonCb(self, widget):
        font_desc = widget.get_font_desc().to_string()
        self.debug("Setting font desc to %s", font_desc)
        self.source.set_font_desc(font_desc)
        self.seeker.flush()

    def _activate(self):
        """
        Show the title editing UI widgets and hide the infobar
        """
        self.infobar.hide()
        self.textarea.show()
        self.editing_box.show()
        self._connect_signals()

    def _deactivate(self):
        """
        Reset the title editor interface to its default look
        """
        self.infobar.show()
        self.textarea.hide()
        self.editing_box.hide()
        self._disconnect_signals()

    def _updateFromSource(self):
        if not self.source:
            # Nothing to update from.
            return

        source_text = self.source.get_text()
        if source_text is None:
            # FIXME: sometimes we get a TextOverlay/TitleSource
            # without a valid text property. This should not happen.
            source_text = ""
            self.warning(
                'Source did not have a text property, setting it to "" to avoid pango choking up on None')
        self.log("Title text set to %s", source_text)
        self.textbuffer.set_text(source_text)

        self.settings['xpos'].set_value(self.source.get_xpos())
        self.settings['ypos'].set_value(self.source.get_ypos())
        self.settings['valignment'].set_active_id(
            self.source.get_valignment().value_name)
        self.settings['halignment'].set_active_id(
            self.source.get_halignment().value_name)

        font_desc = Pango.FontDescription.from_string(
            self.source.get_font_desc())
        self.font_button.set_font_desc(font_desc)

        color = argb_to_gdk_rgba(self.source.get_text_color())
        self.foreground_color_button.set_rgba(color)

        color = argb_to_gdk_rgba(self.source.get_background_color())
        self.background_color_button.set_rgba(color)

    def _updateSourceText(self, unused_updated_obj):
        if not self.source:
            # Nothing to update.
            return

        text = self.textbuffer.get_text(self.textbuffer.get_start_iter(),
                                        self.textbuffer.get_end_iter(),
                                        True)
        self.log("Source text updated to %s", text)
        self.source.set_text(text)
        self.seeker.flush()

    def _updateSource(self, updated_obj):
        """
        Handle changes in one of the advanced property widgets at the bottom
        """
        if not self.source:
            # Nothing to update.
            return

        for name, obj in list(self.settings.items()):
            if obj == updated_obj:
                if name == "valignment":
                    self.source.set_valignment(
                        getattr(GES.TextVAlign, obj.get_active_id().upper()))
                    self.settings["ypos"].set_visible(
                        obj.get_active_id() == "position")
                elif name == "halignment":
                    self.source.set_halignment(
                        getattr(GES.TextHAlign, obj.get_active_id().upper()))
                    self.settings["xpos"].set_visible(
                        obj.get_active_id() == "position")
                elif name == "xpos":
                    self.settings["halignment"].set_active_id("position")
                    self.source.set_xpos(obj.get_value())
                elif name == "ypos":
                    self.settings["valignment"].set_active_id("position")
                    self.source.set_ypos(obj.get_value())
                self.seeker.flush()
                return

    def set_source(self, source):
        """
        Set the clip to be edited with this editor.

        @type source: L{GES.TitleSource}
        """
        self.debug("Source set to %s", source)
        self._deactivate()
        assert isinstance(source, GES.TextOverlay) or \
            isinstance(source, GES.TitleSource)
        # TODO: Remove ".get_parent()" when bug 727880 is fixed.
        self.source = source.get_parent()
        self._updateFromSource()
        self._activate()

    def unset_source(self):
        self.source = None
        self._deactivate()

    def _createCb(self, unused_button):
        """
        The user clicked the "Create and insert" button, initialize the UI
        """
        clip = GES.TitleClip()
        clip.set_text("")
        clip.set_duration(int(Gst.SECOND * 5))
        clip.set_color(FOREGROUND_DEFAULT_COLOR)
        clip.set_background(BACKGROUND_DEFAULT_COLOR)
        # TODO: insert on the current layer at the playhead position.
        # If no space is available, create a new layer to insert to on top.
        self.app.gui.timeline_ui.insertEnd([clip])
        self.app.gui.timeline_ui.timeline.selection.setToObj(clip, SELECT)

    def _connect_signals(self):
        if not self._signals_connected:
            self.app.gui.viewer.target.connect(
                "motion-notify-event", self.drag_notify_event)
            self.app.gui.viewer.target.connect(
                "button-press-event", self.drag_press_event)
            self.app.gui.viewer.target.connect(
                "button-release-event", self.drag_release_event)
            self._signals_connected = True

    def _disconnect_signals(self):
        if not self._signals_connected:
            return
        self.app.gui.viewer.target.disconnect_by_func(self.drag_notify_event)
        self.app.gui.viewer.target.disconnect_by_func(self.drag_press_event)
        self.app.gui.viewer.target.disconnect_by_func(self.drag_release_event)
        self._signals_connected = False

    def drag_press_event(self, unused_widget, event):
        if event.button == 1:
            self._drag_events = [(event.x, event.y)]
            # Update drag by drag event change, but not too often
            self.timeout = GLib.timeout_add(100, self.drag_update_event)
            # If drag goes out for 0.3 second, and do not come back, consider
            # drag end
            self._drag_updated = True
            self.timeout = GLib.timeout_add(1000, self.drag_possible_end_event)

    def drag_possible_end_event(self):
        if self._drag_updated:
            # Updated during last timeout, wait more
            self._drag_updated = False
            return True
        else:
            # Not updated - posibly out of bounds, stop drag
            self.log("Drag timeout")
            self._drag_events = []
            return False

    def drag_update_event(self):
        if len(self._drag_events) > 0:
            st = self._drag_events[0]
            self._drag_events = [self._drag_events[-1]]
            e = self._drag_events[0]
            xdiff = e[0] - st[0]
            ydiff = e[1] - st[1]
            xdiff /= self.app.gui.viewer.target.get_allocated_width()
            ydiff /= self.app.gui.viewer.target.get_allocated_height()
            newxpos = self.settings["xpos"].get_value() + xdiff
            newypos = self.settings["ypos"].get_value() + ydiff
            self.settings["xpos"].set_value(newxpos)
            self.settings["ypos"].set_value(newypos)
            self.seeker.flush()
            return True
        else:
            return False

    def drag_notify_event(self, unused_widget, event):
        if len(self._drag_events) > 0 and event.get_state() & Gdk.ModifierType.BUTTON1_MASK:
            self._drag_updated = True
            self._drag_events.append((event.x, event.y))
            st = self._drag_events[0]
            e = self._drag_events[-1]

    def drag_release_event(self, unused_widget, unused_event):
        self._drag_events = []

    def tabSwitchedCb(self, unused_notebook, page_widget, unused_page_index):
        if self.widget == page_widget:
            self._connect_signals()
        else:
            self._disconnect_signals()

    def selectionChangedCb(self, selection):
        selected_clip = selection.getSingleClip(GES.TitleClip)
        source = selected_clip and selected_clip.get_children(False)[0]
        if source:
            self.set_source(source)
        else:
            self.unset_source()
