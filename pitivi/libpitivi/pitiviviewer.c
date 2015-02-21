/* Pitivi
 *
 * Copyright (C) 2015 Thibault Saunier <tsaunier@gnome.org>
 *
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Library General Public
 * License as published by the Free Software Foundation; either
 * version 2 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Library General Public License for more details.
 *
 * You should have received a copy of the GNU Library General Public
 * License along with this library; if not, write to the
 * Free Software Foundation, Inc., 51 Franklin St, Fifth Floor,
 * Boston, MA 02110-1301, USA.
 */

#ifdef HAVE_CONFIG_H
#include "config.h"
#endif

#include "pitiviviewer.h"

#include <gdk/gdk.h>
#if defined (GDK_WINDOWING_X11)
#include <gdk/gdkx.h>
#elif defined (GDK_WINDOWING_WIN32)
#include <gdk/gdkwin32.h>
#elif defined (GDK_WINDOWING_QUARTZ)
#include <gdk/gdkquartz.h>
#endif


static guintptr
get_window_handle (GtkWidget * widget)
{
  guintptr embed_xid;

  GdkWindow *window = gtk_widget_get_window (widget);

  g_return_val_if_fail (gdk_window_ensure_native (window), FALSE);

#if defined (GDK_WINDOWING_WIN32)
  embed_xid = (guintptr) GDK_WINDOW_HWND (window);
#elif defined (GDK_WINDOWING_QUARTZ)
  embed_xid = (guintptr) gdk_quartz_window_get_nsview (window);
#elif defined (GDK_WINDOWING_X11)
  embed_xid = GDK_WINDOW_XID (window);
#endif

  return embed_xid;
}

static void
realize_cb (GtkWidget * widget, GstElement * videosink)
{
  gst_video_overlay_set_window_handle (GST_VIDEO_OVERLAY (videosink),
      get_window_handle (widget));

  g_signal_handlers_disconnect_by_func (widget, realize_cb, videosink);
}

/**
 * pitivi_viewer_new:
 * @videosink: (transfer none) (allow-none): the sink
 *
 * Returns: (transfer full): The new GtkDrawing area ready to be used
 */
GtkWidget *
pitivi_viewer_new (GstElement * videosink)
{
  GtkWidget *res = gtk_drawing_area_new ();

  if (videosink)
    pitivi_viewer_set_sink (res, videosink);

  return res;
}

gboolean
pitivi_viewer_set_sink (GtkWidget * widget, GstElement * videosink)
{
  if (gtk_widget_get_realized (widget)) {
    gst_video_overlay_set_window_handle (GST_VIDEO_OVERLAY (videosink),
        get_window_handle (widget));
    return TRUE;
  }

  g_signal_connect (widget, "realize", G_CALLBACK (realize_cb), videosink);

  return FALSE;
}
