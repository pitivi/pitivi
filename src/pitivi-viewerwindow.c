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
#include "pitivi-dragdrop.h"

static     PitiviProjectWindowsClass *parent_class;
static	   GdkPixmap *pixmap = NULL;


enum {
  PLAY,
  PAUSE,
  STOP
};

static GtkTargetEntry TargetEntries[] =
{
  { "pitivi/sourcefile", GTK_TARGET_SAME_APP, DND_TARGET_SOURCEFILEWIN }
};

static gint iNbTargetEntries = G_N_ELEMENTS (TargetEntries);

struct _PitiviViewerWindowPrivate
{
  gboolean	dispose_has_run;

  /* instance private members */

  gchar		*location;
  gboolean	play_status;
  
  GstElement	*pipe;
  GstElement	*bin_src;
  GstElement	*sink;
  GstElement	*spider;
  
  GtkWidget	*main_vbox;
  GtkWidget	*toolbar; 
  GtkWidget	*button_play;
  GtkWidget	*button_stop;
  GtkWidget	*button_backward;
  GtkWidget	*button_forward;
  GtkWidget	*video_area;
  GtkWidget	*timeline;

  gdouble	timeline_min;
  gdouble	timeline_max;
  gdouble	timeline_step;

};

/*
 * forward definitions
 */

GstElement	*get_file_source(GstElement *pipeline)
{
  GList		*pipelist;
  GstElement	*elem;
  

  pipelist = (GList *) gst_bin_get_list(GST_BIN(pipeline)); 
  elem = NULL;

 
  while (pipelist)
    {
      elem = (GstElement*)pipelist->data;
      if (strstr(gst_element_get_name(elem), "bin_"))
	break;
      pipelist = pipelist->next;
    }
  
  if (GST_IS_BIN(elem))
    {
      pipelist = (GList *) gst_bin_get_list(GST_BIN(elem));
      while (pipelist)
	{
	  elem = (GstElement*)pipelist->data;
	  if (strstr(gst_element_get_name(elem), "src_"))
	    break;
	  pipelist = pipelist->next;
	}
    }
  else
    return NULL;
  return elem;
}

gboolean	do_seek(GstElement *elem, gint64 value)
{
  GstEvent	*event;
  GstPad	*pad;
  gboolean	res;

  pad = gst_element_get_pad(elem, "src");
  event = gst_event_new_seek (
			      GST_FORMAT_BYTES |	    /* seek on bytes */
			      GST_SEEK_METHOD_SET | /* set the absolute position */
			      GST_SEEK_FLAG_FLUSH,  /* flush any pending data */
			      value);	    /* the seek offset in bytes */
  
  /* res = gst_element_send_event (GST_ELEMENT (elem), event); */
  if (!(res = gst_pad_send_event(pad, event)))
    {
      g_warning ("seek failed");
      return FALSE;
    }
  return TRUE;
}

gint64	do_query(GstElement *elem, GstQueryType type)
{
  GstFormat	format;
  gint64	value;

  format = GST_FORMAT_BYTES;
  if (!gst_element_query(elem, type, &format, &value))
    {
      g_printf("Couldn't perform requested query\n");
      return -1;
    }

  return value;
}

void	video_play(GtkWidget *widget, gpointer data)
{
  PitiviViewerWindow *self = (PitiviViewerWindow *) data;
  PitiviProject	*project = ((PitiviProjectWindows *) self)->project;
  GdkEventExpose ev;
  gboolean retval;

  if (self->private->play_status == PLAY) {
    gtk_signal_emit_by_name (GTK_OBJECT (self->private->video_area), "expose_event", &ev, &retval);
    g_print ("[CallBack]:video_pause\n");
    self->private->play_status = PAUSE;
    gst_element_set_state(project->pipeline, GST_STATE_PAUSED);
  } else if (self->private->play_status == PAUSE) {
    g_print ("[CallBack]:video_play\n");
    self->private->play_status = PLAY;
    gst_element_set_state(project->pipeline, GST_STATE_PLAYING);
  } else if (self->private->play_status == STOP) {
    g_print ("[CallBack]:video_play\n");
    self->private->play_status = PLAY;
    gst_element_set_state(project->pipeline, GST_STATE_PLAYING);
  }
  return ;
}

void	video_stop(GtkWidget *widget, gpointer data)
{
  PitiviViewerWindow *self = (PitiviViewerWindow *) data;
  PitiviProject	*project = ((PitiviProjectWindows *) self)->project;
  gboolean res;
  GstElement *elem;
  gint64	value;

  g_print ("[CallBack]:video_stop\n");
  //gst_element_set_state(project->pipeline, GST_STATE_NULL);
  gst_element_set_state(project->pipeline, GST_STATE_PAUSED);
  self->private->play_status = STOP;

  elem = get_file_source(project->pipeline);

  /* rewind the movie */
  do_seek(elem, 0);
  
  /* query total size */
  value  = do_query(elem, GST_QUERY_TOTAL);

  /* reset the viewer timeline */
  gtk_range_set_value(GTK_RANGE (self->private->timeline) , 0);
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

gboolean	seek_stream(GtkWidget *widget,
			    GdkEventButton *event,
			    gpointer data)
{
  PitiviViewerWindow *self = (PitiviViewerWindow *) data;
  PitiviProject	*project = ((PitiviProjectWindows *) self)->project;
  gboolean	res;
  GstElement	*elem;
  gint64	value1;
  gint64	value2;
  gdouble	pourcent;

  g_printf("you release me\n");
  elem = get_file_source(project->pipeline);

  
  /* query total size */
  value1  = do_query(elem, GST_QUERY_TOTAL);
  
  pourcent = gtk_range_get_value(GTK_RANGE (widget));

  value2 = (gint64)((pourcent * value1) / 500);
  /* rewind the movie */
  if (do_seek(elem, value2))
    g_printf("performing  seek\n");
  
  return FALSE;
}
void	move_timeline(GtkWidget *widget, gpointer data)
{
  PitiviViewerWindow *self = (PitiviViewerWindow *) data;

  g_print ("[CallBack]:move_timeline:%g\n", gtk_range_get_value(GTK_RANGE (widget)));

  return ;
}

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
  g_printf("exposing\n");
  gdk_draw_drawable (widget->window,
		     widget->style->fg_gc[GTK_WIDGET_STATE (widget)],
		     pixmap,
		     event->area.x, event->area.y,
		     event->area.x, event->area.y,
		     event->area.width, event->area.height);
  return FALSE;
}

static void
pitivi_viewerwindow_drag_data_received (GtkWidget *widget, GdkDragContext *drag_context,
					gint x, gint y, GtkSelectionData *data,
					guint info, guint time, gpointer user_data)
{
  PitiviSourceFile	*sf;
  PitiviViewerWindow *self = (PitiviViewerWindow *) user_data;
  PitiviProject	*project = ((PitiviProjectWindows *) self)->project;
  guint		*id;

  g_printf("drag-data-received viewer\n");
  sf = (void *) data->data;
  g_printf("Received file [%s] in viewer\n",
	   sf->filename);
  g_printf("pipeline ==> %p\n", sf->pipeline);

  self->private->play_status = STOP;
  pitivi_project_set_source_element(project, sf->pipeline);
}

static gboolean
pitivi_viewerwindow_drag_drop (GtkWidget *widget, GdkDragContext *dc,
			       gint x, gint y, guint time, gpointer user_data)
{

  g_printf("drag-drop viewer\n");
  gtk_drag_finish (dc, TRUE, FALSE, time);


  return TRUE;
}

void
create_gui (gpointer data)
{
  PitiviViewerWindow *self = (PitiviViewerWindow *) data;
  GtkWidget	*image;

  // main Vbox
  self->private->main_vbox = gtk_vbox_new (FALSE, FALSE);
  gtk_container_add (GTK_CONTAINER (self), self->private->main_vbox);

  // Create Video Display (Drawing Area)
  self->private->video_area = gtk_drawing_area_new ();
  /* Signals used to handle backing pixmap */

  g_signal_connect (G_OBJECT (self->private->video_area), "expose_event",
		    G_CALLBACK (pitivi_viewerwindow_expose_event), NULL);
  g_signal_connect (G_OBJECT (self->private->video_area), "configure_event",
		    G_CALLBACK (pitivi_viewerwindow_configure_event), NULL);

  gtk_widget_set_events (self->private->video_area, GDK_EXPOSURE_MASK
			 | GDK_LEAVE_NOTIFY_MASK
			 | GDK_BUTTON_PRESS_MASK
			 | GDK_POINTER_MOTION_MASK
			 | GDK_POINTER_MOTION_HINT_MASK);

  gtk_drag_dest_set(GTK_WIDGET(self->private->video_area), 
		    GTK_DEST_DEFAULT_ALL,
		    TargetEntries, iNbTargetEntries,
		    GDK_ACTION_COPY);

  g_signal_connect (G_OBJECT(self->private->video_area), "drag_data_received",
		    G_CALLBACK (pitivi_viewerwindow_drag_data_received), self);
  g_signal_connect (G_OBJECT(self->private->video_area), "drag_drop",
		    G_CALLBACK (pitivi_viewerwindow_drag_drop), self);

  gtk_box_pack_start (GTK_BOX (self->private->main_vbox), self->private->video_area, TRUE, TRUE, 0);
  
  // Create hbox for toolbar
  self->private->toolbar = gtk_hbox_new (FALSE, FALSE);
  gtk_box_pack_start (GTK_BOX (self->private->main_vbox), self->private->toolbar, FALSE, TRUE, 0);
  
  // Buttons for Toolbar

  // Button Backward
  image = get_image (self, backward_xpm);
  self->private->button_backward = gtk_button_new ();
  gtk_container_add (GTK_CONTAINER (self->private->button_backward), image);
  //gtk_widget_set_size_request (GTK_WIDGET (self->private->button_backward), 30, 17);
  gtk_signal_connect (GTK_OBJECT (self->private->button_backward), "pressed", 
                      GTK_SIGNAL_FUNC (video_backward), self);
  gtk_box_pack_start (GTK_BOX (self->private->toolbar), 
		      self->private->button_backward, FALSE, FALSE, 0);

  // Button Play
  image = get_image (self, play_xpm);
  self->private->button_play = gtk_button_new ();
  gtk_container_add (GTK_CONTAINER (self->private->button_play), image);
  gtk_signal_connect (GTK_OBJECT (self->private->button_play), "clicked", 
                      GTK_SIGNAL_FUNC (video_play), self);
  gtk_box_pack_start (GTK_BOX (self->private->toolbar), self->private->button_play, FALSE, FALSE, 0);
  //gtk_widget_set_size_request (self->private->button_play, 60, 17);
 
  // Button Forward
  image = get_image (self, forward_xpm);
  self->private->button_forward = gtk_button_new ();
  gtk_container_add (GTK_CONTAINER (self->private->button_forward), image);
  gtk_widget_set_size_request (GTK_WIDGET (self->private->button_forward), 30, 17);
  gtk_signal_connect (GTK_OBJECT (self->private->button_forward), "pressed", 
                      GTK_SIGNAL_FUNC (video_forward), self);
  gtk_box_pack_start (GTK_BOX (self->private->toolbar),
		      self->private->button_forward, FALSE, TRUE, 0);

  // Button Stop
  image = get_image (self, stop_xpm);
  self->private->button_stop = gtk_button_new ();
  gtk_container_add (GTK_CONTAINER (self->private->button_stop), image);
  //gtk_widget_set_size_request (GTK_WIDGET (self->private->button_stop), 30, 17);
  gtk_signal_connect (GTK_OBJECT (self->private->button_stop), "clicked", 
                      GTK_SIGNAL_FUNC (video_stop), self);
  gtk_box_pack_start (GTK_BOX (self->private->toolbar),
		      self->private->button_stop, FALSE, TRUE, 0);

  // Timeline
  self->private->timeline = gtk_hscale_new_with_range(self->private->timeline_min, 
						      self->private->timeline_max, 
						      self->private->timeline_step);
  gtk_scale_set_draw_value (GTK_SCALE (self->private->timeline), FALSE);


  gtk_signal_connect (GTK_OBJECT (self->private->timeline), "button-release-event", 
		      GTK_SIGNAL_FUNC (seek_stream), self);
  gtk_signal_connect (GTK_OBJECT (self->private->timeline), "value-changed", 
		      GTK_SIGNAL_FUNC (move_timeline), self);
  gtk_box_pack_start (GTK_BOX (self->private->toolbar), 
		      self->private->timeline, TRUE, TRUE, 0);
 
 
  return;
}

void
create_stream (gpointer data)
{
  PitiviViewerWindow *self = (PitiviViewerWindow *) data;
  PitiviProject	*project = ((PitiviProjectWindows *) self)->project;

  GstElement	*audiosink;

/*   self->private->pipe = gst_thread_new ("pipeline"); */
/*   g_assert (self->private->pipe != NULL); */

/*   self->private->bin_src = gst_element_factory_make ("videotestsrc", "video_source"); */
/*   g_assert (self->private->bin_src != NULL); */

  audiosink = gst_element_factory_make("alsasink", "audio-out");
  
  pitivi_project_set_audio_output(project, audiosink);

  self->private->sink = gst_element_factory_make ("xvimagesink", "video_display");
  g_assert (self->private->sink != NULL);
  pitivi_project_set_video_output(project, self->private->sink);

				  

/*   gst_bin_add_many (GST_BIN (self->private->pipe), */
/* 		    self->private->bin_src, */
/* 		    self->private->sink, */
/* 		    NULL); */

/* <<<<<<< pitivi-viewerwindow.c */
/*   if (!gst_element_link (self->private->bin_src, self->private->sink)) */
/*     printf ("could not link elem\n"); */
  
/*   gst_element_set_state (self->private->pipe, GST_STATE_PLAYING); */
/* ======= */
  if (!gst_element_link (self->private->bin_src, self->private->sink))
    printf ("could not link elem\n");

  pitivi_project_blank_source(project);
  gst_element_set_state (project->pipeline, GST_STATE_PLAYING);
/* >>>>>>> 1.24 */
  self->private->play_status = PLAY;
  return ;
}

void
print_element_schedulers(GstElement *element) {
  GList *sched;
  GstScheduler  *son;
  GstScheduler  *msch;

  msch = gst_element_get_scheduler(element);
  g_printf("Schedulers in Element[%s](ElementState:%d)(SchedulerState:%d):\n",
           gst_element_get_name(element), gst_element_get_state(element),
	   msch->state);
  for (sched = gst_element_get_scheduler(element)->schedulers; sched;
       sched = sched->next) {
    son = (GstScheduler *) sched->data;
    
    g_printf("\tScheduler[%s]:%p State=%d\n",
             gst_element_get_name(son->parent), son, son->state);
    g_printf("/-------\\\n");
    print_element_schedulers(son->parent);
    g_printf("\\-------/\n");
  }
}

gboolean	idle_func_video (gpointer data)
{
  PitiviViewerWindow *self = (PitiviViewerWindow *) data;
  PitiviProject	*project = ((PitiviProjectWindows *) self)->project;
  
  GstElement *elem;
  gint64	value1, value2;
  gdouble	pourcent;

  if ( gst_element_get_state (project->pipeline) == GST_STATE_PLAYING ) {
/*     print_element_schedulers(project->pipeline); */
    gst_x_overlay_set_xwindow_id
      ( GST_X_OVERLAY ( self->private->sink ),
	GDK_WINDOW_XWINDOW ( self->private->video_area->window ) );
    gst_bin_iterate (GST_BIN (project->pipeline));
    elem = get_file_source(project->pipeline);
    
    if (elem) /* we have a true source */
      {
	value1 = do_query(elem, GST_QUERY_POSITION);
	value2 = do_query(elem, GST_QUERY_TOTAL);
	pourcent = (value1 * 100) / value2;
	
	pourcent *= 5;

	gtk_range_set_value(GTK_RANGE (self->private->timeline) , pourcent);
      }
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
  g_idle_add (idle_func_video, obj);

  return obj;
}

static void
pitivi_viewerwindow_instance_init (GTypeInstance * instance, gpointer g_class)
{
  PitiviViewerWindow *self = (PitiviViewerWindow *) instance;

  self->private = g_new0(PitiviViewerWindowPrivate, 1);
  
  /* initialize all public and private members to reasonable default values. */ 
  
  self->private->dispose_has_run = FALSE;

  gtk_window_set_default_size(GTK_WINDOW(self), 300, 200);
  
  /* initialize all public and private members to reasonable default values. */ 
  
  self->private->location = "";
  self->private->play_status = STOP;

  self->private->pipe = NULL;
  self->private->bin_src = NULL;
  self->private->sink = NULL;
  self->private->spider = NULL;

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
pitivi_viewerwindow_set_property (GObject * object,
			      guint property_id,
			      const GValue * value, GParamSpec * pspec)
{
  PitiviViewerWindow *self = (PitiviViewerWindow *) object;

  switch (property_id)
    {
      /*   case PITIVI_VIEWERWINDOW_PROPERTY: { */
      /*     g_free (self->private->name); */
      /*     self->private->name = g_value_dup_string (value); */
      /*     g_print ("maman: %s\n",self->private->name); */
      /*   } */
      /*     break; */
    default:
      /* We don't have any other property... */
      g_assert (FALSE);
      break;
    }
}

static void
pitivi_viewerwindow_get_property (GObject * object,
			      guint property_id,
			      GValue * value, GParamSpec * pspec)
{
  PitiviViewerWindow *self = (PitiviViewerWindow *) object;

  switch (property_id)
    {
      /*  case PITIVI_VIEWERWINDOW_PROPERTY: { */
      /*     g_value_set_string (value, self->private->name); */
      /*   } */
      /*     break; */
    default:
      /* We don't have any other property... */
      g_assert (FALSE);
      break;
    }
}

static void
pitivi_viewerwindow_class_init (gpointer g_class, gpointer g_class_data)
{
  GObjectClass *gobject_class = G_OBJECT_CLASS (g_class);
  PitiviViewerWindowClass *klass = PITIVI_VIEWERWINDOW_CLASS (g_class);

  parent_class = g_type_class_peek_parent (g_class);

  gobject_class->constructor = pitivi_viewerwindow_constructor;
  gobject_class->dispose = pitivi_viewerwindow_dispose;
  gobject_class->finalize = pitivi_viewerwindow_finalize;

  gobject_class->set_property = pitivi_viewerwindow_set_property;
  gobject_class->get_property = pitivi_viewerwindow_get_property;

  /* Install the properties in the class here ! */
  /*   pspec = g_param_spec_string ("maman-name", */
  /*                                "Maman construct prop", */
  /*                                "Set maman's name", */
  /*                                "no-name-set" /\* default value *\/, */
  /*                                G_PARAM_CONSTRUCT_ONLY | G_PARAM_READWRITE); */
  /*   g_object_class_install_property (gobject_class, */
  /*                                    MAMAN_BAR_CONSTRUCT_NAME, */
  /*                                    pspec); */


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
