/* 
 * PiTiVi
 * Copyright (C) <2004> Delettrez Marc <delett_m@epita.fr>
 *                    	Pralat Raphael <pralat_r@epita.fr>  
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
#include <gtk/gtk.h>
#include <gst/gst.h>
#include <gdk/gdkx.h>
#include <gst/xoverlay/xoverlay.h>
#include <gst/play/play.h>

#include "pitivi.h"
#include "pitivi-viewerwindow.h"
#include "pitivi-timelinewindow.h"
#include "pitivi-dragdrop.h"
#include "pitivi-debug.h"

/* #include "../pixmaps/stop.xpm" */
/* #include "../pixmaps/play.xpm" */
/* #include "../pixmaps/pause.xpm" */
/* #include "../pixmaps/forward.xpm" */
/* #include "../pixmaps/backward.xpm" */

static		GdkPixbuf *window_icon = NULL;
static		PitiviProjectWindowsClass *parent_class;
static		GdkPixmap *pixmap = NULL;

gboolean	idle_func_video (gpointer data);
gboolean	updated_time (gpointer data);

enum {
  PLAY,
  PAUSE,
  STOP
};

/* static GtkTargetEntry TargetEntries[] = */
/* { */
/*   { "pitivi/sourcefile", GTK_TARGET_SAME_APP, DND_TARGET_SOURCEFILEWIN } */
/* }; */

/* static gint iNbTargetEntries = G_N_ELEMENTS (TargetEntries); */


struct _PitiviViewerWindowPrivate
{
  gboolean	dispose_has_run;

  /* instance private members */

  gint		play_status;
  
  GstElement	*sink;
  GstElement	*fulloutputbin;
  
  GtkWidget	*main_vbox;
  GtkWidget	*toolbar; 
  GtkWidget	*button_play;
  GtkWidget	*image_play;
  GtkWidget	*image_pause;

  GtkWidget	*button_stop;
  GtkWidget	*button_backward;
  GtkWidget	*button_forward;
  GtkWidget	*video_area;
  GtkWidget	*timeline;

  gdouble	timeline_min;
  gdouble	timeline_max;
  gdouble	timeline_step;

  gint64	new_time;
  GstProbe	*probe;
};

/*
 **********************************************************
 * Signals						  *
 *							  *
 **********************************************************
*/

enum {
  PLAY_SIGNAL,
  PAUSE_SIGNAL,
  STOP_SIGNAL,
  BACKWARD_SIGNAL,
  FORWARD_SIGNAL,
  LAST_SIGNAL
};

static  guint viewersignals[LAST_SIGNAL] = {0};


/*
 * forward definitions
 */

gboolean	do_seek(GstElement *elem, gint64 value)
{
  GstEvent	*event;
  GstElementState	prev;

  //  pad = gst_element_get_pad(elem, "src");
/*   g_printf ("do_seek %s -> %lld:%02lld:%03lld\n", */
/* 	    gst_element_get_name (elem), */
/* 	    GST_M_S_M (value)); */
/*   pitivi_printf_element (elem); */
  event = gst_event_new_seek (
			      GST_FORMAT_TIME |	    /* seek on nanoseconds */
			      GST_SEEK_METHOD_SET | /* set the absolute position */
			      GST_SEEK_FLAG_FLUSH,  /* flush any pending data */
			      value);	    /* the seek offset in bytes */

  
  prev = gst_element_get_state (elem);
  if (prev != GST_STATE_PAUSED)
    gst_element_set_state (elem, GST_STATE_PAUSED);
  /* res = gst_element_send_event (GST_ELEMENT (elem), event); */
  if (!(gst_element_send_event(elem, event)))
    {
      g_warning ("seek on element %s failed",
		 gst_element_get_name(elem));
      if (prev != GST_STATE_PAUSED)
	gst_element_set_state (elem, prev);
      return FALSE;
    }
  if (prev != GST_STATE_PAUSED)
    gst_element_set_state (elem, prev);
  return TRUE;
}

gint64	do_query(GstElement *elem, GstQueryType type)
{
  GstFormat	format;
  gint64	value;

  format = GST_FORMAT_TIME;
  if (!gst_element_query(elem, type, &format, &value))
    {
      g_printf("Couldn't perform requested query\n");
      return -1;
    }

  return value;
}

void
acitve_widget (GtkWidget *bin, GtkWidget *w1, GtkWidget *w2)
{
  gtk_container_remove (GTK_CONTAINER (bin), w2);
  gtk_container_add (GTK_CONTAINER (bin), w1);
  return ;
}

void	video_play(GtkWidget *widget, gpointer data)
{
  PitiviViewerWindow *self = (PitiviViewerWindow *) data;
  PitiviProject	*project = ((PitiviProjectWindows *) self)->project;
  GdkEventExpose ev;
  gboolean retval;

  if (self->private->play_status == PLAY) {
    g_print ("[CallBack]:video_pause PLAY STATUS\n");
    self->private->play_status = PAUSE;
    gst_element_set_state(project->pipeline, GST_STATE_PAUSED);
  } else if (self->private->play_status == PAUSE) {
    g_print ("[CallBack]:video_play PAUSE STATUS\n");
    self->private->play_status = PLAY;
    if (!gst_element_set_state(project->pipeline, GST_STATE_PLAYING))
      g_warning("Couldn't set the project pipeline to PLAYING!");
    else {
      gst_x_overlay_set_xwindow_id
	( GST_X_OVERLAY ( self->private->sink ),
	  GDK_WINDOW_XWINDOW ( self->private->video_area->window ) );
      g_idle_add(idle_func_video, self);
    }
  } else if (self->private->play_status == STOP) {
    g_print ("[CallBack]:video_play STOP STATUS\n");
    self->private->play_status = PLAY;
    do_seek (GST_ELEMENT (project->timeline), 0);
    if (!gst_element_set_state(project->pipeline, GST_STATE_PLAYING))
      g_warning("Couldn't set the project pipeline to PLAYING");
    else {
      gst_x_overlay_set_xwindow_id
	( GST_X_OVERLAY ( self->private->sink ),
	  GDK_WINDOW_XWINDOW ( self->private->video_area->window ) );
      g_idle_add(idle_func_video, self);
    }
  }
  gtk_signal_emit_by_name (GTK_OBJECT (self->private->video_area), "expose_event", &ev, &retval);
  return ;
}

void	video_stop(GtkWidget *widget, gpointer data)
{
  PitiviViewerWindow *self = (PitiviViewerWindow *) data;
  PitiviProject	*project = ((PitiviProjectWindows *) self)->project;
/*   gint64	value; */

  g_print ("[CallBack]:video_stop\n");
  //gst_element_set_state(project->pipeline, GST_STATE_NULL);
  gst_element_set_state(project->pipeline, GST_STATE_READY);
  self->private->play_status = STOP;

  /* rewind the movie */
/*   do_seek(GST_ELEMENT (project->timeline), 0LL); */
  
  /* query total size */
  /* value  = do_query(GST_ELEMENT (project->timeline), GST_QUERY_TOTAL); */

  /* reset the viewer timeline */
  self->private->new_time = 0;
  updated_time (self);
  return ;
}

void	video_backward(GtkWidget *widget, gpointer data)
{
  PitiviViewerWindow *self = (PitiviViewerWindow *) data;

  gdouble	time;

  g_print ("[CallBack]:video_backward\n");

  time = gtk_range_get_value(GTK_RANGE (self->private->timeline));
  if (time >= (self->private->timeline_min + self->private->timeline_step))
    time -= self->private->timeline_step;
  else
    time = self->private->timeline_min;
  gtk_range_set_value(GTK_RANGE (self->private->timeline) , time);
  return ;
}

void	video_forward(GtkWidget *widget, gpointer data)
{
  PitiviViewerWindow *self = (PitiviViewerWindow *) data;

  gdouble	time;

  g_print ("[CallBack]:video_forward\n");

  time = gtk_range_get_value(GTK_RANGE (self->private->timeline));
  if (time <= (self->private->timeline_max - self->private->timeline_step))
    time += self->private->timeline_step;
  else
    time = self->private->timeline_max;
  gtk_range_set_value(GTK_RANGE (self->private->timeline) , time);
  return ;
}

gboolean	pause_stream(GtkWidget *widget,
			    GdkEventButton *event,
			    gpointer data)
{
  PitiviViewerWindow *self = (PitiviViewerWindow *) data;
  PitiviProject	*project = ((PitiviProjectWindows *) self)->project;

  gst_element_set_state(project->pipeline, GST_STATE_PAUSED);

  return FALSE;
}

/* void	move_timeline(GtkWidget *widget, gpointer data) */
/* { */
/* /\*   PitiviViewerWindow *self = (PitiviViewerWindow *) data; *\/ */

/*   g_print ("[CallBack]:move_timeline:%g\n", gtk_range_get_value(GTK_RANGE (widget))); */
/*   /\* TODO actually seek in the timeline !!! *\/ */
/*   return ; */
/* } */

GtkWidget *
get_image (gpointer data, char **im_name)
{
  GtkWidget	* win;
  GdkColormap	*colormap;
  GdkBitmap	*mask;
  GdkPixmap	*pixmap;
  GtkWidget	*pixmapw;

  win = (GtkWidget *) data;
  colormap = gtk_widget_get_colormap (win);
  pixmap = gdk_pixmap_colormap_create_from_xpm_d (win->window, 
						  colormap, 
						  &mask, 
						  NULL,
						  im_name);
  pixmapw = gtk_image_new_from_pixmap (pixmap, mask);
  return pixmapw;
}  

static gint pitivi_viewerwindow_configure_event( GtkWidget         *widget,
						 GdkEventConfigure *event )
{
  if (pixmap)
    g_object_unref (pixmap);

  pixmap = gdk_pixmap_new (widget->window,
			   widget->allocation.width,
			   widget->allocation.height,
			   -1);
  gdk_draw_rectangle (pixmap,
		      widget->style->black_gc,
		      TRUE,
		      0, 0,
		      widget->allocation.width,
		      widget->allocation.height);
  return TRUE;
}

static gint pitivi_viewerwindow_expose_event( GtkWidget      *widget,
					      GdkEventExpose *event )
{
  //  g_printf("exposing\n");
  gdk_draw_drawable (widget->window,
		     widget->style->fg_gc[GTK_WIDGET_STATE (widget)],
		     pixmap,
		     event->area.x, event->area.y,
		     event->area.x, event->area.y,
		     event->area.width, event->area.height);
  return FALSE;
}

void
viewerwindow_start_stop_changed (GnlTimeline *timeline, GParamSpec *arg, gpointer udata)
{
  PitiviViewerWindow *self = (PitiviViewerWindow *) udata;

  self->private->timeline_min = GNL_OBJECT(timeline)->start;
  self->private->timeline_max = GNL_OBJECT(timeline)->stop;

  gtk_range_set_range (GTK_RANGE(self->private->timeline), 
		       self->private->timeline_min,
		       self->private->timeline_max);
}

gboolean
updated_time (gpointer data) {
  PitiviViewerWindow *self = (PitiviViewerWindow *) data;

  /*g_printf ("updated time %lld:%lld:%lld\n", GST_M_S_M(self->private->new_time));*/
  gtk_range_set_value(GTK_RANGE (self->private->timeline) , self->private->new_time);
  pitivi_timelinewindow_update_time (pitivi_mainapp_get_timelinewin (((PitiviWindows *) self)->mainapp),
				     self->private->new_time);
  return FALSE;
}

gboolean
output_probe (GstProbe *probe, GstData **data, gpointer udata)
{
  PitiviViewerWindow *self = (PitiviViewerWindow *) udata;
  PitiviProject	*project = ((PitiviProjectWindows *) self)->project;

  if (GST_IS_BUFFER(*data)) {
    self->private->new_time = GST_BUFFER_TIMESTAMP(*data);
    g_idle_add (updated_time, self);
  } else if (GST_IS_EVENT(*data) && (GST_EVENT_TYPE(*data) == GST_EVENT_EOS)) {
    /* 
       This is really a crude hack. We have to drop the EOS Event and stop iterating manually,
       otherwise the app segfaults on a gst_object_unref of that EOS event :(
    */
    gst_element_set_state (project->pipeline, GST_STATE_READY);
    self->private->play_status = STOP;
    self->private->new_time = 0;
    g_idle_add (updated_time, self);    
    return FALSE;
  }
  return TRUE;
}

void
create_gui (gpointer data)
{
  PitiviViewerWindow *self = (PitiviViewerWindow *) data;

  // main Vbox
  self->private->main_vbox = gtk_vbox_new (FALSE, FALSE);
  gtk_container_add (GTK_CONTAINER (self), self->private->main_vbox);
  gtk_widget_show (self->private->main_vbox);

  // Create Video Display (Drawing Area)
  self->private->video_area = gtk_drawing_area_new ();
  gtk_widget_show (self->private->video_area);

  /* Signals used to handle backing pixmap */

  g_signal_connect (G_OBJECT (self->private->video_area), "expose_event",
		    G_CALLBACK (pitivi_viewerwindow_expose_event), NULL);
  g_signal_connect (G_OBJECT (self->private->video_area), "configure_event",
		    G_CALLBACK (pitivi_viewerwindow_configure_event), NULL);
  
  gtk_widget_set_events (self->private->video_area, GDK_EXPOSURE_MASK);
  gtk_box_pack_start (GTK_BOX (self->private->main_vbox), self->private->video_area, TRUE, TRUE, 0);
  
  // Create hbox for toolbar
  self->private->toolbar = gtk_hbox_new (FALSE, FALSE);
  gtk_box_pack_start (GTK_BOX (self->private->main_vbox), self->private->toolbar, FALSE, TRUE, 0);
  gtk_widget_show (self->private->toolbar);

  // Buttons for Toolbar
  
  // Timeline
  self->private->timeline = gtk_hscale_new_with_range(self->private->timeline_min, 
						      self->private->timeline_max, 
						      self->private->timeline_step);
  gtk_scale_set_draw_value (GTK_SCALE (self->private->timeline), FALSE);
  gtk_widget_show (self->private->timeline);

  /*   gtk_signal_connect (GTK_OBJECT (self->private->timeline), "value-changed",  */
  /* 		      GTK_SIGNAL_FUNC (move_timeline), self); */
  gtk_box_pack_start (GTK_BOX (self->private->toolbar), 
		      self->private->timeline, TRUE, TRUE, 0);
  
  gtk_widget_show (GTK_WIDGET (self));

  return;
}

void
create_stream (gpointer data)
{
  PitiviViewerWindow *self = (PitiviViewerWindow *) data;
  PitiviProject	*project = ((PitiviProjectWindows *) self)->project;

/*   GstElement	*audiosink; */
  GstElement	*timeoverlay;

//  audiosink = gst_element_factory_make("alsasink", "audio-out");
  
//  pitivi_project_set_audio_output(project, audiosink);

  self->private->sink = gst_element_factory_make ("xvimagesink", "video_display");
  g_assert (self->private->sink != NULL);
  self->private->probe = gst_probe_new(FALSE, output_probe, self);
  gst_pad_add_probe (gnl_timeline_get_pad_for_group (project->timeline, project->videogroup),
		     self->private->probe);

  timeoverlay = gst_element_factory_make ("timeoverlay", "timeoverlay");
  self->private->fulloutputbin = gst_bin_new("videobin");

  if (timeoverlay) {
    gst_bin_add_many (GST_BIN (self->private->fulloutputbin),
		      timeoverlay,
		      self->private->sink,
		      NULL);
    gst_element_link (timeoverlay, self->private->sink);
    
    gst_element_add_ghost_pad (self->private->fulloutputbin,
			       gst_element_get_pad(timeoverlay, "sink"),
			       "sink");
  } else {
    gst_bin_add (GST_BIN (self->private->fulloutputbin),
		 self->private->sink);
    gst_element_add_ghost_pad (self->private->fulloutputbin,
			       gst_element_get_pad(self->private->sink, "sink"),
			       "sink");
  }
  /* Add a GstProbe to the output */
  pitivi_project_set_video_output(project, self->private->fulloutputbin);

  self->private->play_status = STOP;

  g_signal_connect (project->timeline, "notify::start",
		    G_CALLBACK(viewerwindow_start_stop_changed), self);
  g_signal_connect (project->timeline, "notify::stop",
		    G_CALLBACK(viewerwindow_start_stop_changed), self);

  return ;
}

gboolean	idle_func_video (gpointer data)
{
  PitiviViewerWindow *self = (PitiviViewerWindow *) data;
  PitiviProject	*project = ((PitiviProjectWindows *) self)->project;
  
  // remove the idle_func if we're not playing !
  if (self->private->play_status == STOP) {
    video_stop (GTK_WIDGET (self), self);
    return FALSE;
  }
  
  if ( gst_element_get_state (project->pipeline) == GST_STATE_PLAYING ) {
    gst_bin_iterate (GST_BIN (project->pipeline));
  }
  return TRUE;
}

/*
 * Insert "added-value" functions here
 */

PitiviViewerWindow *
pitivi_viewerwindow_new(PitiviMainApp *mainapp, PitiviProject *project)
{
  PitiviViewerWindow	*viewerwindow;

  //g_print ("coucou:new\n");
  viewerwindow = (PitiviViewerWindow *) g_object_new(PITIVI_VIEWERWINDOW_TYPE, 
						     "mainapp", mainapp,
						     "project", project, NULL);
  g_assert(viewerwindow != NULL);
  return viewerwindow;
}

static GObject *
pitivi_viewerwindow_constructor (GType type,
				 guint n_construct_properties,
				 GObjectConstructParam * construct_properties)
{
  //g_print ("coucou:constructor\n");

  GObject *obj;
  {
    obj = G_OBJECT_CLASS (parent_class)->constructor (type, n_construct_properties,
						      construct_properties);
  }

  create_gui (obj);
  create_stream (obj);
  // only add idle function when playing
  //  g_idle_add (idle_func_video, obj);

  return obj;
}

static void
pitivi_viewerwindow_instance_init (GTypeInstance * instance, gpointer g_class)
{
  PitiviViewerWindow *self = (PitiviViewerWindow *) instance;

  self->private = g_new0(PitiviViewerWindowPrivate, 1);
  
  /* initialize all public and private members to reasonable default values. */ 
  
  self->private->dispose_has_run = FALSE;

  gtk_window_set_default_size(GTK_WINDOW(self), PITIVI_VIEWER_DF_WIN_WIDTH, PITIVI_VIEWER_DF_WIN_HEIGHT);
  gtk_window_set_title (GTK_WINDOW (self), PITIVI_VIEWER_DF_TITLE); 
  if (window_icon == NULL) 
    {
      char *filename;
      
      filename = g_strdup(pitivi_file (PITIVI_VIEWER_LOGO));
      window_icon = gdk_pixbuf_new_from_file (filename, NULL);
      g_free (filename);
    }
  gtk_window_set_icon (GTK_WINDOW (self), window_icon);

  /* initialize all public and private members to reasonable default values. */ 
  
  self->private->play_status = STOP;

  self->private->sink = NULL;
  self->private->fulloutputbin = NULL;

  self->private->main_vbox = NULL;
  self->private->toolbar = NULL;
  self->private->button_play = NULL;
  self->private->button_stop = NULL;
  self->private->button_backward = NULL;
  self->private->button_forward = NULL;
  self->private->video_area = NULL;
  self->private->timeline = NULL;

  self->private->timeline_min = 0;
  self->private->timeline_max = 500;
  self->private->timeline_step = 1;
}

static void
pitivi_viewerwindow_dispose (GObject *object)
{
  PitiviViewerWindow	*self = PITIVI_VIEWERWINDOW(object);

  /* If dispose did already run, return. */
  if (self->private->dispose_has_run)
    return;
  
  /* Make sure dispose does not run twice. */
  self->private->dispose_has_run = TRUE;

	
  g_idle_remove_by_data (self);


  /* 
   * In dispose, you are supposed to free all types referenced from this 
   * object which might themselves hold a reference to self. Generally, 
   * the most simple solution is to unref all members on which you own a 
   * reference. 
   */

  G_OBJECT_CLASS (parent_class)->dispose (object);
}

static void
pitivi_viewerwindow_finalize (GObject *object)
{
  PitiviViewerWindow	*self = PITIVI_VIEWERWINDOW(object);
  PitiviProject	*project = ((PitiviProjectWindows *) self)->project;

  /* 
   * Here, complete object destruction. 
   * You might not need to do much... 
   */

  gst_element_set_state(project->pipeline, GST_STATE_NULL);

  g_free (self->private);
  G_OBJECT_CLASS (parent_class)->finalize (object);
}

static void
pitivi_viewver_callb_play (PitiviViewerWindow *self)
{
  gtk_widget_show (GTK_WIDGET (self));
  video_play (GTK_WIDGET (self), self);
}

static void
pitivi_viewver_callb_backward (PitiviViewerWindow *self)
{
  video_backward (GTK_WIDGET (self), self);
}

static void
pitivi_viewver_callb_forward (PitiviViewerWindow *self)
{
  video_forward (GTK_WIDGET (self), self);
}

static void
pitivi_viewver_callb_pause (PitiviViewerWindow *self)
{
  PitiviProject	*project = ((PitiviProjectWindows *) self)->project;
  gst_element_set_state (project->pipeline, GST_STATE_PAUSED);
}

static void
pitivi_viewer_callb_stop (PitiviViewerWindow *self)
{
  video_stop (GTK_WIDGET(self), self);
/*   pitivi_timelinewindow_stop (pitivi_mainapp_get_timelinewin (((PitiviWindows *) self)->mainapp)); */
}

static gboolean
pitivi_viewerwindow_delete_event ( GtkWidget  *widget,
				   GdkEventAny *event )
{
  g_return_val_if_fail (GTK_IS_WIDGET (widget), FALSE);
  gtk_widget_hide (widget);
  pitivi_timelinewindow_windows_set_action (pitivi_mainapp_get_timelinewin (((PitiviWindows *) widget)->mainapp), 
					    "ViewerWindows", FALSE);
  return TRUE;
}

static void
pitivi_viewerwindow_class_init (gpointer g_class, gpointer g_class_data )
{
  GtkWidgetClass *widget_class = GTK_WIDGET_CLASS (g_class);
  GObjectClass *gobject_class = G_OBJECT_CLASS (g_class);
  PitiviViewerWindowClass *klass = PITIVI_VIEWERWINDOW_CLASS (g_class);

  parent_class = g_type_class_peek_parent (g_class);

  widget_class->delete_event = pitivi_viewerwindow_delete_event;
  
  gobject_class->constructor = pitivi_viewerwindow_constructor;
  gobject_class->dispose = pitivi_viewerwindow_dispose;
  gobject_class->finalize = pitivi_viewerwindow_finalize;
  
  viewersignals[PLAY_SIGNAL] = g_signal_new ("play",
					     G_TYPE_FROM_CLASS (g_class),
					     G_SIGNAL_RUN_FIRST | G_SIGNAL_ACTION,
					     G_STRUCT_OFFSET (PitiviViewerWindowClass, play),
					     NULL, 
					     NULL,                
					     g_cclosure_marshal_VOID__VOID,
					     G_TYPE_NONE, 0);
  
  viewersignals[PAUSE_SIGNAL] = g_signal_new ("pause",
					      G_TYPE_FROM_CLASS (g_class),
					      G_SIGNAL_RUN_FIRST | G_SIGNAL_ACTION,
					      G_STRUCT_OFFSET (PitiviViewerWindowClass, pause),
					      NULL, 
					      NULL,                
					      g_cclosure_marshal_VOID__VOID,
					      G_TYPE_NONE, 0);
  
  viewersignals[BACKWARD_SIGNAL] = g_signal_new ("backward",
						 G_TYPE_FROM_CLASS (g_class),
						 G_SIGNAL_RUN_FIRST | G_SIGNAL_ACTION,
						 G_STRUCT_OFFSET (PitiviViewerWindowClass, backward),
						 NULL, 
						 NULL,                
						 g_cclosure_marshal_VOID__VOID,
						 G_TYPE_NONE, 0);
   
  viewersignals[FORWARD_SIGNAL] = g_signal_new ("forward",
						G_TYPE_FROM_CLASS (g_class),
						G_SIGNAL_RUN_FIRST | G_SIGNAL_ACTION,
						G_STRUCT_OFFSET (PitiviViewerWindowClass, forward),
						NULL, 
						NULL,                
						g_cclosure_marshal_VOID__VOID,
						G_TYPE_NONE, 0);
  
  viewersignals[STOP_SIGNAL] = g_signal_new ("stop",
						G_TYPE_FROM_CLASS (g_class),
						G_SIGNAL_RUN_FIRST | G_SIGNAL_ACTION,
						G_STRUCT_OFFSET (PitiviViewerWindowClass, stop),
						NULL, 
						NULL,                
						g_cclosure_marshal_VOID__VOID,
						G_TYPE_NONE, 0);
  
  
  klass->play  =  pitivi_viewver_callb_play;
  klass->backward =  pitivi_viewver_callb_backward; 
  klass->forward  =  pitivi_viewver_callb_forward;
  klass->pause  =  pitivi_viewver_callb_pause;
  klass->stop = pitivi_viewer_callb_stop;
}

GType
pitivi_viewerwindow_get_type (void)
{
  static GType type = 0;
 
  if (type == 0)
    {
      static const GTypeInfo info = {
	sizeof (PitiviViewerWindowClass),
	NULL,			/* base_init */
	NULL,			/* base_finalize */
	pitivi_viewerwindow_class_init,	/* class_init */
	NULL,			/* class_finalize */
	NULL,			/* class_data */
	sizeof (PitiviViewerWindow),
	0,			/* n_preallocs */
	pitivi_viewerwindow_instance_init	/* instance_init */
      };
      type = g_type_register_static (PITIVI_PROJECTWINDOWS_TYPE,
				     "PitiviViewerWindowType", &info, 0);
    }

  return type;
}
