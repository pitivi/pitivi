/* 
 * PiTiVi
 * Copyright (C) <2004> Edward G. Hervey <hervey_e@epita.fr>
 *                      Guillaume Casanova <casano_g@epita.fr>
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

#include "pitivi.h"
#include "pitivi-viewerwindow.h"

static GtkWindowClass *parent_class = NULL;

enum PITIVI_GST_ELEMENT
  {
    PIPELINE_ELEMENT = 0,
    SRC_ELEMENT,
    SINK_ELEMENT,
    ALL_ELEMENT
  };

struct _PitiviViewerWindowPrivate
{
  /* instance private members */
  gboolean			dispose_has_run;
  GtkWidget			*main_vbox;
  PitiviViewerPlayer		*playerview;
  GstElement			*elm[ALL_ELEMENT];
  GtkWidget			*video_area;
  PitiviViewerController	*media_controller;
  GdkPixbuf			*logo;
  GtkWidget			*mixer;
  GtkWidget			*statusbar;
};


/*
 * forward definitions
 */

/*
 * Insert "added-value" functions here
 */

PitiviViewerWindow *
pitivi_viewerwindow_new(void)
{
  PitiviViewerWindow *viewerwindow;

  viewerwindow = (PitiviViewerWindow *) g_object_new(PITIVI_VIEWERWINDOW_TYPE, NULL);
  g_assert(viewerwindow != NULL);
  return viewerwindow;
}


gboolean	idle_func (gpointer data)
{
  
  PitiviViewerWindowPrivate *x = (PitiviViewerWindowPrivate *) data;

  if ( x->elm[PIPELINE_ELEMENT] )
    if ( gst_element_get_state (x->elm[0]) == GST_STATE_PLAYING )
      {
	gst_x_overlay_set_xwindow_id ( GST_X_OVERLAY ( x->elm[SINK_ELEMENT] ), 
				       GDK_WINDOW_XWINDOW ( x->video_area->window ) );
	gst_bin_iterate (GST_BIN (x->elm[PIPELINE_ELEMENT]));
      }
  
  return TRUE;
}


void		meof (GstElement *elm)
{
  gst_element_set_state ( GST_ELEMENT (elm), GST_STATE_NULL );
  g_print ("have eof, quitting\n");
  g_object_unref (G_OBJECT (elm));
  elm = 0;
}


gboolean  launching_gst_video (PitiviViewerWindow *self )
{

  self->private->elm[PIPELINE_ELEMENT]=gst_pipeline_new("pipeline");
  g_return_val_if_fail ( self->private->elm[PIPELINE_ELEMENT] != NULL, -1);
  
  self->private->elm[SRC_ELEMENT]=gst_element_factory_make("videotestsrc", "src");
  g_return_val_if_fail ( self->private->elm[SRC_ELEMENT] != NULL, -1);

  self->private->elm[SINK_ELEMENT]=gst_element_factory_make("xvimagesink", "sink");
  g_return_val_if_fail ( self->private->elm[SINK_ELEMENT] != NULL, -1);
  
  gst_bin_add_many (GST_BIN (self->private->elm[PIPELINE_ELEMENT])\
		    , self->private->elm[1], self->private->elm[SINK_ELEMENT]\
		    , NULL);
  g_signal_connect (G_OBJECT (self->private->elm[SRC_ELEMENT]), "eos",
		    G_CALLBACK (meof), self->private->elm[PIPELINE_ELEMENT]);
  gst_element_link (self->private->elm[SRC_ELEMENT], self->private->elm[2]);
  gst_element_set_state ( GST_ELEMENT (self->private->elm[PIPELINE_ELEMENT])\
			  , GST_STATE_PLAYING );
  g_idle_add ( idle_func, self->private );
  
  return (TRUE);
}


static void
pitivi_viewerwindow_instance_init (GTypeInstance * instance, gpointer g_class)
{
  PitiviViewerWindow *self = (PitiviViewerWindow *) instance;
  GtkWidget  *separator;
  int	     count;
    
  self->private = g_new0(PitiviViewerWindowPrivate, 1);
  gtk_window_set_resizable (GTK_WINDOW (self), FALSE);
  self->private->dispose_has_run = FALSE;
  gtk_widget_show (GTK_WIDGET (self));
 
  // Create Video Display (Drawing Area)
  
  self->private->video_area = gtk_drawing_area_new ();
  gtk_widget_set_events (self->private->video_area, GDK_BUTTON_PRESS_MASK);
  gtk_widget_set_size_request (self->private->video_area, 400, 300);
  gtk_widget_show (GTK_WIDGET (self->private->video_area));
  gtk_container_add (GTK_CONTAINER(self), GTK_WIDGET (self->private->video_area));
  
  PitiviViewerController *controller = pitivi_viewercontroller_new();
  self->private->media_controller = controller;
  gtk_window_move (GTK_WINDOW (self->private->media_controller), 250, 350);
  launching_gst_video ( self );
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

  /* 
   * Here, complete object destruction. 
   * You might not need to do much... 
   */

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
      type = g_type_register_static (GTK_TYPE_WINDOW,
				     "PitiviViewerWindowType", &info, 0);
    }

  return type;
}
