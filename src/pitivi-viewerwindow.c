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
#include "pitivi-debug.h"

static     PitiviProjectWindowsClass *parent_class;

static	   GdkPixmap *pixmap = NULL;

static GtkTargetEntry TargetEntries[] =
{
  { "pitivi/sourcefile", GTK_TARGET_SAME_APP, DND_TARGET_SOURCEFILEWIN }
};

static gint iNbTargetEntries = G_N_ELEMENTS (TargetEntries);

enum {
  PLAY,
  PAUSE,
  STOP
};

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
  GtkWidget	*video_area;

};

/*
 * forward definitions
 */


// #####################################################################
// ############################### TODO ################################
// #####################################################################

// functions PLAY(POS) PAUSE AVANCE(STEP) RECULE(STEP)
// geometry 4:3 16:9 ....
// double click = mazimize / unmaximize
// mettre a jour le graph
// relier aux controls de la timeline
// FREE ALL VAR AT THE END


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
create_gui (gpointer data)
{
  PitiviViewerWindow	*self = (PitiviViewerWindow *) data;

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

  //gtk_box_pack_start (GTK_BOX (self->private->main_vbox), 
  //	      self->private->video_area, TRUE, TRUE, 0);
  gtk_container_add (GTK_CONTAINER (self->private->main_vbox), 
		     self->private->video_area);
  
  gtk_widget_show_all (GTK_WIDGET (self));

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

//  audiosink = gst_element_factory_make("alsasink", "audio-out");
  
//  pitivi_project_set_audio_output(project, audiosink);

  self->private->sink = gst_element_factory_make ("ximagesink", "video_display");
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
/*   if (!gst_element_link (self->private->bin_src, self->private->sink)) */
/*     printf ("could not link elem\n"); */

  //  pitivi_project_blank_source(project);
  // gst_element_set_state (project->pipeline, GST_STATE_PLAYING);
/* >>>>>>> 1.24 */
  self->private->play_status = STOP;
  return ;
}

gboolean	idle_func_video (gpointer data)
{
  PitiviViewerWindow *self = (PitiviViewerWindow *) data;
  PitiviProject	*project = ((PitiviProjectWindows *) self)->project;
  
  GstElement *elem;
  gint64	value1, value2;
  gdouble	pourcent;

  if ( gst_element_get_state (project->pipeline) == GST_STATE_PLAYING ) {
/*     g_printf("\n"); */
/*     pitivi_printf_element(project->pipeline); */
/*     g_printf("\n"); */
    gst_x_overlay_set_xwindow_id
      ( GST_X_OVERLAY ( self->private->sink ),
	GDK_WINDOW_XWINDOW ( self->private->video_area->window ) );
    gst_bin_iterate (GST_BIN (project->pipeline));
    
    /*
      elem = get_file_source(project->pipeline);
      if (elem) 
      {
      value1 = do_query(elem, GST_QUERY_POSITION);
      value2 = do_query(elem, GST_QUERY_TOTAL);
      pourcent = (value1 * 100) / value2;
      
      pourcent *= 5;
      
      gtk_range_set_value(GTK_RANGE (self->private->timeline) , pourcent);
      }
    */
  }
  return TRUE;
}

/*
 * ################################################################################## 
 * ################### Insert "added-value" functions here ##########################
 * ################################################################################## 
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
  self->private->video_area = NULL;
  
  gtk_window_set_title (GTK_WINDOW (self), PITIVI_VIEWER_DF_TITLE);
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
