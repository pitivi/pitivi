/* 
 * PiTiVi
 * Copyright (C) <2004> Guillaume Casanova <casano_g@epita.fr>
 *                     
 *
 * This software has been written in EPITECH <http://www.epitech.net>
 * EPITECH is a computer science school in Paris - FRANCE -
 * under the direction of Flavien Astraud and Jerome Landrieu.
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public
 * License as published by the Free Software Foundation; either
 * version 2 of the License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * General Public License for more details.
 *
 * You should have received a copy of the GNU General Public
 * License along with this program; if not, write to the
 * Free Software Foundation, Inc., 59 Temple Place - Suite 330,
 * Boston, MA 02111-1307, USA.
 */

#include <gst/gst.h>
#include <gtk/gtk.h>

#define DIR_LENGTH 50
#define FRAME	10	/* which frame to snapshot */
#define TIMEOUT	5000	/* how long before we give up, msec */

gint64	   frame = FRAME;
gboolean   finished = FALSE;
gboolean   can_finish = FALSE;
GtkWidget  *myreceiver = NULL;
gchar      *myoutput = NULL;

typedef struct _infothumb
{
  GstElement *pipeline;
  gchar      *myoutput;
};

void end_of_snap (GstElement *sink, GstElement *pipeline)
{
  finished = TRUE;
  gst_element_set_state (pipeline, GST_STATE_NULL);
  g_signal_emit_by_name (myreceiver, "snapped", myoutput);
}

/* timeout after a given amount of time */
gboolean timeout (GstPipeline *gen)
{
  /* setting the state NULL will make iterate return false */
  gst_element_set_state (GST_ELEMENT (gen), GST_STATE_NULL);
  return FALSE;
}

gboolean iterator (GstPipeline *gen)
{
  /* setting the state NULL will make iterate return false */
  return gst_bin_iterate (GST_BIN (gen));
}


static int
gst_thumbnail_pngenc_get (const char *media, const char *thumbnail, GtkWidget *receiver)
{
  GstElement *pipeline;
  GstElement *gnomevfssrc;
  GstElement *snapshot;
  GstElement *sink;
  GstPad *pad;
  GstEvent *event;
  gboolean res;
  GError *error = NULL;
  int i;
  
  pipeline = gst_parse_launch ("gnomevfssrc name=gnomevfssrc ! spider ! " 
			       "videoscale ! ffcolorspace ! video/x-raw-rgb,width=48,height=48 !"
			       "pngenc name=snapshot",
			       &error);
  
  if (!GST_IS_PIPELINE (pipeline))
    {
      g_print ("Parse error: %s\n", error->message);
      return  -1;
    }
  gnomevfssrc = gst_bin_get_by_name (GST_BIN (pipeline), "gnomevfssrc");
  snapshot = gst_bin_get_by_name (GST_BIN (pipeline), "snapshot");
  g_assert (GST_IS_ELEMENT (snapshot));
  g_assert (GST_IS_ELEMENT (gnomevfssrc));
  g_object_set (G_OBJECT (gnomevfssrc), "location", media, NULL);

  gst_element_set_state (pipeline, GST_STATE_PLAYING);
    
  for (i = 0; i < frame; ++i)
    gst_bin_iterate (GST_BIN (pipeline));
	
  gst_element_set_state (pipeline, GST_STATE_PAUSED);
    
  sink = gst_element_factory_make ("filesink", "sink");
  g_assert (GST_IS_ELEMENT (sink));
  g_object_set (G_OBJECT (sink), "location", thumbnail, NULL);
  gst_bin_add (GST_BIN (pipeline), sink);
  gst_element_link (snapshot, sink);
  g_signal_connect (G_OBJECT (sink), "handoff",
		    G_CALLBACK (end_of_snap), pipeline);

  gst_element_set_state (pipeline, GST_STATE_PLAYING);
	
  g_timeout_add (TIMEOUT, (GSourceFunc) timeout, pipeline);
  g_idle_add ((GSourceFunc) iterator, pipeline);
  can_finish = TRUE;
  return 1;
}

gchar *
get_last_charoccur (gchar *s, char c)
{
  gchar *str;
  int len;

  len = strlen (s) - 1;
  if (len > 0)
    {
      str = s + len;
      if (str && *str)
	{
	  while (len)
	    {
	    if (*str == c)
	      return str + 1;
	    str--;
	    len--;
	    }
	}
    }
  return NULL;
}

gchar *
generate_thumb (char *filename, GtkWidget *widget, int i)
{
  GstElement *pngenc = NULL;
  gchar	     *tmp = NULL;

  pngenc = gst_element_factory_make ("pngenc", "pngenc");
  if (filename && pngenc != NULL)
    {
      tmp = get_last_charoccur (filename, '/');
      if ( tmp )
	{
	  myreceiver = widget;
	  myoutput = g_malloc (strlen (filename) + DIR_LENGTH);
	  g_sprintf (myoutput, "/tmp/%s%c%d", tmp, '\0', i);
	  if ( gst_thumbnail_pngenc_get (filename, myoutput, widget) > 0)
	      return myoutput;
	}
    }
  return NULL;
}

gchar *
generate_thumb_snap_on_frame (char *filename, GtkWidget *widget, gint pframe)
{
  GstElement *pngenc = NULL;
  gchar	     *tmp = NULL;

  pngenc = gst_element_factory_make ("pngenc", "pngenc");
  if (filename && pngenc != NULL)
    {
      tmp = get_last_charoccur (filename, '/');
      if ( tmp )
	{
	  frame = pframe;
	  myreceiver = widget;
	  myoutput = g_malloc (strlen (filename) + DIR_LENGTH);
	  g_sprintf (myoutput, "/tmp/%s%d", tmp, pframe);
	  if ( gst_thumbnail_pngenc_get (filename, myoutput, widget) > 0)
	      return myoutput;
	}
    }
  return NULL;
}
