/* 
 * PiTiVi
 * Copyright (C) <2004> DELETTREZ Marc <delett_m@epita.fr>
 *			PRALAT Raphael <pralat_r@epita.fr>
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

#include <glib.h>
#include <glib/gprintf.h>
#include <gtk/gtk.h>
#include <gst/gst.h>
#include <gdk/gdkx.h>
#include <gst/xoverlay/xoverlay.h>

#include "pitivi.h"
#include "pitivi-viewerwindow.h"
#include "pitivi-lplayerwindow.h"
#include "pitivi-controller.h"

static     GObjectClass *parent_class;

enum {
  PROP_0,
  PROP_FILENAME
};

struct _PitiviLPlayerWindowPrivate
{
  gboolean	dispose_has_run;
  
  /* instance private members */
  // Main Gui elements
  GtkWidget	*main_vbox;
  GtkWidget	*hbox;
  // stream
  GstElement	*sink;
  GstElement	*spider;
  GstElement	*pipe;
  GstElement	*filesrc;
  GstElement	*colorspace;
  GstElement	*video_sink;
  GstElement	*audio_sink;
  // video_area
  GtkWidget	*video_area;
  // toolbar
  GtkWidget	*toolbar;
  GtkWidget	*toolbarTEMP;
  GtkWidget	*backward;
  GtkWidget	*playpause;
  GtkWidget	*forward;
  GtkWidget	*stop;
  // timeline
  GtkWidget	*timeline;
  gint64	timeline_min;
  gint64	timeline_max;
  gdouble	timeline_step;
};

/*
 * ####################################################################################
 * ####################### forward definitions ########################################
 * ####################################################################################
 */

// TODO
// continuer sur la timeline


gboolean	pitivi_lplayer_idle_func (gpointer data)
{
  PitiviLPlayerWindow *self = (PitiviLPlayerWindow *) data;
  GstElement *elem;
  gint64	value1;

  elem = GST_ELEMENT (self->private->pipe);
  if (elem) // we have a true source
    {
      value1 = do_query(elem, GST_QUERY_POSITION);

      g_printf("**idle** : pos:%lld\n", value1);

    }
/* } */

  g_print("MA QUESTION: %d\n",sizeof(gdouble) );
  g_print("IDLE FUNCTION END %lld, %lld\n", self->private->timeline_min, self->private->timeline_max);

  return TRUE;
}

gboolean	do_lplayer_seek(GstElement *elem, gint64 value)
{
  GstEvent	*event;
  gboolean	res;

  //  pad = gst_element_get_pad(elem, "src");
  event = gst_event_new_seek (
			      GST_FORMAT_TIME |	    /* seek on nanoseconds */
			      GST_SEEK_METHOD_SET | /* set the absolute position */
			      GST_SEEK_FLAG_FLUSH,  /* flush any pending data */
			      value);	    /* the seek offset in bytes */
  
  /* res = gst_element_send_event (GST_ELEMENT (elem), event); */
  if (!(res = gst_element_send_event(elem, event)))
    {
      g_warning ("seek on element %s failed",
		 gst_element_get_name(elem));
      return FALSE;
    }
  return TRUE;
}


void pitivi_lplayer_play_stream (GtkWidget *widget, PitiviLPlayerWindow *self)
{
  if (GTK_TOGGLE_BUTTON (self->private->playpause)->active)
    {
      g_print("FCT__________pitivi_lplayer_play_video:_PLAY\n");
      gst_element_set_state (self->private->pipe, GST_STATE_PLAYING);
      g_idle_add(pitivi_lplayer_idle_func, self);
    }
  else
    {
      g_print("FCT__________pitivi_lplayer_play_video:_STOP\n");
       gst_element_set_state (self->private->pipe, GST_STATE_PAUSED);
    }
}

void pitivi_lplayer_pause_stream (GtkWidget *widget, PitiviLPlayerWindow *self)
{
  gst_element_set_state (self->private->pipe, GST_STATE_PAUSED);
}


void pitivi_lplayer_stop_stream (GtkWidget *widget, PitiviLPlayerWindow *self)
{
  //  PitiviProject	*project = ((PitiviProjectWindows *) self)->project;
  gint64	value;
  
  if (GTK_TOGGLE_BUTTON (self->private->playpause)->active)
    {
      g_print("PLAY_VIDEO_________from_stop\n");   
      gtk_toggle_button_set_active(GTK_TOGGLE_BUTTON(self->private->playpause), FALSE);
    }
  else
    g_print("STOP_VIDEO_________from_stop\n");

  gst_element_set_state(self->private->pipe, GST_STATE_PAUSED);

  /* rewind the movie */
  do_lplayer_seek(GST_ELEMENT (self->private->pipe), 0LL);
  
  /* query total size */
  value  = do_query(GST_ELEMENT (self->private->timeline), GST_QUERY_TOTAL);

  /* reset the viewer timeline */
  gtk_range_set_value(GTK_RANGE (self->private->timeline) , 0);

  // 2 lignes porc pour mettre du noir quand on stop
  gst_element_set_state (self->private->pipe, GST_STATE_PLAYING);
  gst_element_set_state (self->private->pipe, GST_STATE_PAUSED);
  return ;

}

void pitivi_lplayer_backward_stream (GtkWidget *widget, PitiviLPlayerWindow *self)
{

}

void pitivi_lplayer_forward_stream (GtkWidget *widget, PitiviLPlayerWindow *self)
{

}

void
pitivi_lplayerwindow_create_gui (PitiviLPlayerWindow *self)
{
 
  GtkWidget	*button_image;

  g_print ("FILE NAME:%s\n", self->filename);

  // main Vbox
  self->private->main_vbox = gtk_vbox_new (FALSE, FALSE);
  gtk_container_add (GTK_CONTAINER (self), self->private->main_vbox);
  
  // Create Video Display (Drawing Area)
  
  self->private->video_area = gtk_drawing_area_new ();
  gtk_drawing_area_size (GTK_DRAWING_AREA (self->private->video_area), PITIVI_DEFAULT_VIEWER_AREA_WIDTH, 
			 PITIVI_DEFAULT_VIEWER_AREA_HEIGHT);
  gtk_box_pack_start (GTK_BOX (self->private->main_vbox), 
		      self->private->video_area, TRUE, TRUE, 0);
  gtk_widget_set_size_request (self->private->video_area, 355, 190);

  // set Background for video_area
  gtk_widget_realize (self->private->video_area);
  gdk_window_set_background (self->private->video_area->window, &self->private->video_area->style->black);


  // HbOx
  self->private->hbox = gtk_hbox_new (FALSE, FALSE);
  gtk_box_pack_start (GTK_BOX (self->private->main_vbox), 
		      self->private->hbox, TRUE, TRUE, 0);

  // ToolbAr
  self->private->toolbar = gtk_toolbar_new ();
  gtk_box_pack_start (GTK_BOX (self->private->hbox), self->private->toolbar, FALSE, TRUE, 0);
  gtk_widget_show (self->private->toolbar);
  
  gtk_toolbar_set_orientation (GTK_TOOLBAR (self->private->toolbar), GTK_ORIENTATION_HORIZONTAL);
  gtk_toolbar_set_style (GTK_TOOLBAR (self->private->toolbar), GTK_TOOLBAR_BOTH);
  gtk_container_set_border_width (GTK_CONTAINER (self->private->toolbar), 0);

  button_image = gtk_image_new_from_file ("../pixmaps/backward.xpm");
  self->private->backward = gtk_toolbar_append_item( GTK_TOOLBAR (self->private->toolbar),
						     NULL,
						     "My item tooltip",
						     "private item text",
						     button_image,
						     GTK_SIGNAL_FUNC (pitivi_lplayer_play_stream),
						     self);
  
  button_image = gtk_image_new_from_file ("../pixmaps/play.xpm");
  self->private->playpause = gtk_toolbar_append_element (GTK_TOOLBAR (self->private->toolbar),
							 GTK_TOOLBAR_CHILD_TOGGLEBUTTON,
							 NULL,
							 NULL,
							 "Play",
							 "Private",
							 button_image,
							 GTK_SIGNAL_FUNC (pitivi_lplayer_play_stream),
							 self);
  
  button_image = gtk_image_new_from_file ("../pixmaps/forward.xpm");
  self->private->forward  = gtk_toolbar_append_item( GTK_TOOLBAR (self->private->toolbar),
						     NULL,
						     "My item tooltip",
						     "private item text",
						     button_image,
						     GTK_SIGNAL_FUNC (pitivi_lplayer_play_stream),
						     self);
  
  button_image = gtk_image_new_from_file ("../pixmaps/stop.xpm");
  self->private->stop  = gtk_toolbar_append_item( GTK_TOOLBAR (self->private->toolbar),
						  NULL,
						  "My item tooltip",
						  "private item test",
						  button_image,
						  GTK_SIGNAL_FUNC (pitivi_lplayer_stop_stream),
						  self);


  gtk_toggle_button_set_active(GTK_TOGGLE_BUTTON(self->private->playpause), FALSE);

  // TiMelinE



  self->private->timeline = gtk_hscale_new_with_range(self->private->timeline_min, 
						      self->private->timeline_max, 
						      self->private->timeline_step);
  gtk_scale_set_draw_value (GTK_SCALE (self->private->timeline), FALSE);
  gtk_box_pack_start (GTK_BOX (self->private->hbox), 
		      self->private->timeline, TRUE, TRUE, 0);
  
  gtk_widget_show (self->private->timeline);
  
  
  /*   gtk_signal_connect (GTK_OBJECT (self->private->timeline), "button-press-event",  */
  /* 		      GTK_SIGNAL_FUNC (pitivi_lplayer_pause_stream), self); */
  /*   gtk_signal_connect (GTK_OBJECT (self->private->timeline), "button-release-event",  */
  /* 		      GTK_SIGNAL_FUNC (seek_stream), self); */
  /*   gtk_signal_connect (GTK_OBJECT (self->private->timeline), "value-changed",  */
  /* 		      GTK_SIGNAL_FUNC (move_timeline), self); */

  gtk_widget_show_all (GTK_WIDGET (self));

  return ;
}

void
pitivi_lplayerwindow_create_stream (PitiviLPlayerWindow *self)
{
  self->private->pipe = gst_element_factory_make("playbin", "spider");
  g_assert (self->private->pipe != NULL);
  
  self->private->video_sink = gst_element_factory_make("ximagesink", "video_sink");
  g_assert (self->private->video_sink != NULL);
  
  // Sound desactivated 1/2
  // self->private->audio_sink = gst_element_factory_make("alsasink", "audio_sink");
  // g_assert (self->private->audio_sink != NULL);



  g_object_set (G_OBJECT (self->private->pipe), "uri", gst_uri_construct("file", self->filename), NULL);	   
  
  g_object_set (G_OBJECT (self->private->pipe), "video-sink", self->private->video_sink, NULL);	
  // Sound desactivated 2/2
  //  g_object_set (G_OBJECT (self->private->pipe), "audio-sink", self->private->audio_sink, NULL);	

  gst_x_overlay_set_xwindow_id
    ( GST_X_OVERLAY ( self->private->video_sink ),
      GDK_WINDOW_XWINDOW ( self->private->video_area->window ) );

  if (!gst_element_set_state(self->private->pipe, GST_STATE_PLAYING)) {
    g_print ("############################# BAD STATE ########################33\n");
    exit (-1);
  }


  gtk_toggle_button_set_active(GTK_TOGGLE_BUTTON(self->private->playpause), TRUE);

  return ;

}




/*
 * ####################################################################################
 * ####################### Insert "added-value" functions here ########################
 * ####################################################################################
 */

PitiviLPlayerWindow *
pitivi_lplayerwindow_new (gchar *filename)
{
  PitiviLPlayerWindow	*lplayerwindow;

  lplayerwindow = (PitiviLPlayerWindow *) g_object_new(PITIVI_LPLAYERWINDOW_TYPE,
						       "filename", filename,
						       NULL);

  g_assert(lplayerwindow != NULL);
  return lplayerwindow;
}

static GObject *
pitivi_lplayerwindow_constructor (GType type,
			     guint n_construct_properties,
			     GObjectConstructParam * construct_properties)
{
  GstElement *elem;
  GObject *obj;
  /* Invoke parent constructor. */
  obj = parent_class->constructor (type, n_construct_properties,
				   construct_properties);

  /* do stuff. */
  g_printf("lplayer creation !\n");
  PitiviLPlayerWindow *self = (PitiviLPlayerWindow *) obj;

  pitivi_lplayerwindow_create_gui (self);

  pitivi_lplayerwindow_create_stream (self);


  // Set min max range
  elem = GST_ELEMENT (self->private->pipe);
  if (elem) // we have a true source
    {
      self->private->timeline_min  = do_query(elem, GST_QUERY_START);
      self->private->timeline_max  = do_query(elem, GST_QUERY_SEGMENT_END);
    }

  gtk_range_set_range (GTK_RANGE(self->private->timeline), 
		       self->private->timeline_min,
		       self->private->timeline_max);

  return obj;
}

static void
pitivi_lplayerwindow_instance_init (GTypeInstance * instance, gpointer g_class)
{
  PitiviLPlayerWindow *self = (PitiviLPlayerWindow *) instance;

  self->private = g_new0(PitiviLPlayerWindowPrivate, 1);
  
  /* initialize all public and private members to reasonable default values. */ 
  
  self->private->dispose_has_run = FALSE;

  self->private->pipe = NULL;
  self->private->filesrc = NULL;
  self->private->spider = NULL;
  self->private->video_sink = NULL;

  // settings for timeline
  self->private->timeline_min = 0;
  self->private->timeline_max = 500;
  self->private->timeline_step = 1;
  /* Do only initialisation here */
  /* The construction of the object should be done in the Constructor
     So that properties set at instanciation can be set */
}

static void
pitivi_lplayerwindow_dispose (GObject *object)
{
  PitiviLPlayerWindow	*self = PITIVI_LPLAYERWINDOW(object);

  /* If dispose did already run, return. */
  if (self->private->dispose_has_run)
    return;
  
  /* Make sure dispose does not run twice. */
  self->private->dispose_has_run = TRUE;	

  /* 
   * In dispose, you are supposed to free all types referenced from this 
   * object which might themselves hold a reference to self. Generally, 
   * the most simple solution is to unref all members on which you own a 
   * reference. 
   */

  G_OBJECT_CLASS (parent_class)->dispose (object);
}

static void
pitivi_lplayerwindow_finalize (GObject *object)
{
  PitiviLPlayerWindow	*self = PITIVI_LPLAYERWINDOW(object);

  /* 
   * Here, complete object destruction. 
   * You might not need to do much... 
   */

  g_idle_remove_by_data (self);

  gst_element_set_state(self->private->pipe, GST_STATE_PAUSED);
  gst_object_unref (GST_OBJECT(self->private->pipe));

  g_free (self->private);
  G_OBJECT_CLASS (parent_class)->finalize (object);
}

static void
pitivi_lplayerwindow_set_property (GObject * object,
			      guint property_id,
			      const GValue * value, GParamSpec * pspec)
{
  PitiviLPlayerWindow *self = (PitiviLPlayerWindow *) object;

  switch (property_id)
    {
    case PROP_FILENAME:
      self->filename = g_value_dup_string (value);
      //g_value_set_string (value, self->filename); 
      break;
    default:
      g_assert (FALSE);
      break;
    }
}

static void
pitivi_lplayerwindow_get_property (GObject * object,
			      guint property_id,
			      GValue * value, GParamSpec * pspec)
{
  PitiviLPlayerWindow *self = (PitiviLPlayerWindow *) object;

  switch (property_id)
    {
    case PROP_FILENAME:
      //self->filename = g_value_dup_string (value);
      g_value_set_string (value, self->filename); 
      break; 
    default:
      g_assert (FALSE);
      break;
    }
}

static void
pitivi_lplayerwindow_class_init (gpointer g_class, gpointer g_class_data)
{
  GObjectClass *gobject_class = G_OBJECT_CLASS (g_class);
/*   PitiviLPlayerWindowClass *klass = PITIVI_LPLAYERWINDOW_CLASS (g_class); */

  parent_class = G_OBJECT_CLASS (g_type_class_peek_parent (g_class));

  gobject_class->constructor = pitivi_lplayerwindow_constructor;
  gobject_class->dispose = pitivi_lplayerwindow_dispose;
  gobject_class->finalize = pitivi_lplayerwindow_finalize;

  gobject_class->set_property = pitivi_lplayerwindow_set_property;
  gobject_class->get_property = pitivi_lplayerwindow_get_property;

  g_object_class_install_property (gobject_class,  
				   PROP_FILENAME,   
				   g_param_spec_string ("filename", 
							"filename", 
							"media name",	
							NULL, 	
							G_PARAM_CONSTRUCT_ONLY | G_PARAM_WRITABLE)  
				   );

}

GType
pitivi_lplayerwindow_get_type (void)
{
  static GType type = 0;
 
  if (type == 0)
    {
      static const GTypeInfo info = {
	sizeof (PitiviLPlayerWindowClass),
	NULL,			/* base_init */
	NULL,			/* base_finalize */
	pitivi_lplayerwindow_class_init,	/* class_init */
	NULL,			/* class_finalize */
	NULL,			/* class_data */
	sizeof (PitiviLPlayerWindow),
	0,			/* n_preallocs */
	pitivi_lplayerwindow_instance_init	/* instance_init */
      };
      type = g_type_register_static (GTK_TYPE_WINDOW,
				     "PitiviLPlayerWindowType", &info, 0);
    }

  return type;
}
