/* 
 * PiTiVi               Guillaume Casanova <casano_g@epita.fr>
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

#include <glib/gprintf.h>
#include "pitivi.h"
#include "pitivi-debug.h"
#include "pitivi-controller.h"
#include "pitivi-windows.h"

enum {
  PITIVI_CONTROLLER_BUTTON_BACKWARD = 1,
  PITIVI_CONTROLLER_BUTTON_FORWARD,
};

enum {
  PITIVI_CONTROLLER_BUTTON_PLAY = 1,
  PITIVI_CONTROLLER_BUTTON_STOP,
  PITIVI_CONTROLLER_BUTTON_RECORD,
};

struct _PitiviControllerPrivate
{
  /* instance private members */
  
  gboolean	        dispose_has_run;
  GtkWidget	        *viewerwin;
  GtkWidget	        *toolbar;

  GtkToolItem           *b_ffrev[5];
  GtkToolItem           *b_playing[5];
  GSList                *group_playing;
  GSList                *group_ffrev;
};

/*
 * forward definitions
 */

enum {
  PROP_VIEWERWINDOW = 1,
  PROP_LAST
};


/*
 **********************************************************
 * Signals						  *
 *							  *
 **********************************************************
*/

enum {
  PAUSE_SIGNAL = 0,
  RECORD_SIGNAL,
  LAST_SIGNAL
};

static  guint controllersignals[LAST_SIGNAL] = {0};



/*
 * Insert "added-value" functions here
 */

PitiviController *
pitivi_controller_new (void)
{
  PitiviController	*controller;
  
  controller = (PitiviController *) g_object_new(PITIVI_CONTROLLER_TYPE, NULL);
  g_assert(controller != NULL);
  return controller;
}

static GObject *
pitivi_controller_constructor (GType type,
			     guint n_construct_properties,
			     GObjectConstructParam * construct_properties)
{
  GObject *obj;
  {
    /* Invoke parent constructor. */
    PitiviControllerClass *klass;
    GObjectClass *parent_class;
    klass = PITIVI_CONTROLLER_CLASS (g_type_class_peek (PITIVI_CONTROLLER_TYPE));
    parent_class = G_OBJECT_CLASS (g_type_class_peek_parent (klass));
    obj = parent_class->constructor (type, n_construct_properties,
				     construct_properties);
  }

  /* do stuff. */

  return obj;
}

gboolean
pitivi_controller_seek_started_handler (GtkWidget       *widget,
					GdkEventButton   *event,
					gpointer         user_data)
{

  return FALSE;
}


gboolean
pitivi_controller_seek_changed_handler (GtkWidget       *widget,
					GdkEventButton  *event,
					gpointer         user_data)
{
  
  return FALSE;
}

static void
pitivi_controller_callb_play (GtkWidget *widget, gpointer user_data)
{
  PitiviController *self = (PitiviController *) user_data;
  if ( self->private->viewerwin )
    {
      PITIVI_DEBUG ("play %p ... ", self->private->viewerwin);
      gtk_widget_show_all ( self->private->viewerwin );
      g_signal_emit_by_name ( self->private->viewerwin, "play" );
    }
}

static void
pitivi_controller_callb_pause (PitiviController *widget, gpointer user_data)
{
  PitiviController *self = (PitiviController *) user_data;
 if ( self->private->viewerwin )
   g_signal_emit_by_name (self->private->viewerwin, "pause");
}

static void
pitivi_controller_callb_forward (GtkWidget *widget, gpointer user_data)
{
  PitiviController *self = (PitiviController *) user_data;
 if ( self->private->viewerwin )
   g_signal_emit_by_name (self->private->viewerwin, "forward");
}

static void
pitivi_controller_callb_backward (GtkWidget *widget, gpointer user_data)
{
  PitiviController *self = (PitiviController *) user_data;
  if ( self->private->viewerwin )
    g_signal_emit_by_name (self->private->viewerwin, "backward");
}

static void
pitivi_controller_callb_record (GtkWidget *widget, PitiviController *self)
{
  g_signal_emit (G_OBJECT (self), controllersignals[RECORD_SIGNAL], 0);
} 

static void
pitivi_controller_callb_stop (GtkWidget *widget, gpointer user_data)
{
  PitiviController *self = (PitiviController *) user_data;

  if (!gtk_toggle_tool_button_get_active (GTK_TOGGLE_TOOL_BUTTON (self->private->b_ffrev[0])))
    gtk_toggle_tool_button_set_active (GTK_TOGGLE_TOOL_BUTTON (self->private->b_ffrev[0]), TRUE);
  if (!gtk_toggle_tool_button_get_active (GTK_TOGGLE_TOOL_BUTTON (self->private->b_playing[0])))
    gtk_toggle_tool_button_set_active (GTK_TOGGLE_TOOL_BUTTON (self->private->b_playing[0]), TRUE);
   if ( self->private->viewerwin )
     g_signal_emit_by_name (self->private->viewerwin, "stop");
}

static void
pitivi_controller_instance_init (GTypeInstance * instance, gpointer g_class)
{
  PitiviController *self = (PitiviController *) instance;

  self->private = g_new0(PitiviControllerPrivate, 1);
  
  /* initialize all public and private members to reasonable default values. */ 
  
  self->private->dispose_has_run = FALSE;
    
  /* Gestion des bouttons de controle */
  
  self->private->toolbar = gtk_toolbar_new();   
  self->private->group_ffrev = g_new(GSList, 1);
  self->private->group_playing = g_new(GSList, 1);

  /* Creation Avance/Rembobinage Rapide Pause */
  
  self->private->b_ffrev[0] = \
    gtk_radio_tool_button_new (NULL);
  self->private->group_ffrev = \
    gtk_radio_tool_button_get_group (GTK_RADIO_TOOL_BUTTON (self->private->b_ffrev[0]));
  
  self->private->b_ffrev[PITIVI_CONTROLLER_BUTTON_FORWARD]  = gtk_tool_button_new_from_stock (PITIVI_STOCK_VIEWER_NEXT);
  self->private->b_ffrev[PITIVI_CONTROLLER_BUTTON_BACKWARD] = gtk_tool_button_new_from_stock (PITIVI_STOCK_VIEWER_PREVIOUS);
    
  /* Creation boutton Stop */

  self->private->b_playing[0] = \
    gtk_radio_tool_button_new (NULL);
  self->private->group_playing = \
    gtk_radio_tool_button_get_group GTK_RADIO_TOOL_BUTTON ((self->private->b_playing[0]));
  
  self->private->b_playing[PITIVI_CONTROLLER_BUTTON_PLAY] = gtk_tool_button_new_from_stock (PITIVI_STOCK_VIEWER_PLAY);
  self->private->b_playing[PITIVI_CONTROLLER_BUTTON_STOP] = gtk_tool_button_new_from_stock (PITIVI_STOCK_VIEWER_STOP);
  self->private->b_playing[PITIVI_CONTROLLER_BUTTON_RECORD] = gtk_tool_button_new_from_stock (PITIVI_STOCK_VIEWER_RECORD);
  
  /* Toolbar Insertion */
  
  gtk_toolbar_insert (GTK_TOOLBAR(self->private->toolbar)\
		      , GTK_TOOL_ITEM (self->private->b_ffrev[PITIVI_CONTROLLER_BUTTON_BACKWARD]), -1);
  gtk_toolbar_insert (GTK_TOOLBAR(self->private->toolbar)\
		      , GTK_TOOL_ITEM (self->private->b_playing[PITIVI_CONTROLLER_BUTTON_PLAY]), -1);
  gtk_toolbar_insert (GTK_TOOLBAR(self->private->toolbar)\
		      , GTK_TOOL_ITEM (self->private->b_ffrev[PITIVI_CONTROLLER_BUTTON_FORWARD]), -1);  
  gtk_toolbar_insert (GTK_TOOLBAR(self->private->toolbar)\
		      , GTK_TOOL_ITEM (self->private->b_playing[PITIVI_CONTROLLER_BUTTON_STOP]), -1);
  gtk_toolbar_insert (GTK_TOOLBAR(self->private->toolbar)\
		      , GTK_TOOL_ITEM (self->private->b_playing[PITIVI_CONTROLLER_BUTTON_RECORD]), -1);
  
  gtk_toolbar_set_orientation (GTK_TOOLBAR(self->private->toolbar), GTK_ORIENTATION_HORIZONTAL);
  gtk_toolbar_set_show_arrow (GTK_TOOLBAR(self->private->toolbar), FALSE);
  gtk_toolbar_set_style (GTK_TOOLBAR(self->private->toolbar), GTK_TOOLBAR_ICONS);
  gtk_toolbar_set_icon_size (GTK_TOOLBAR (self->private->toolbar), GTK_ICON_SIZE_MENU);

  gtk_box_pack_start (GTK_BOX (self), self->private->toolbar, TRUE, TRUE, 0);
  gtk_widget_show_all (GTK_WIDGET(self));

  /* Signals */
   
  g_signal_connect (self->private->b_playing[PITIVI_CONTROLLER_BUTTON_STOP]\
		    , "clicked", G_CALLBACK(pitivi_controller_callb_stop), self);
  
  g_signal_connect (self->private->b_playing[PITIVI_CONTROLLER_BUTTON_PLAY]\
		    , "clicked", G_CALLBACK(pitivi_controller_callb_play), self);

  g_signal_connect (self->private->b_playing[PITIVI_CONTROLLER_BUTTON_RECORD]\
		    , "clicked", G_CALLBACK(pitivi_controller_callb_record), self);

  g_signal_connect (self->private->b_ffrev[PITIVI_CONTROLLER_BUTTON_FORWARD]\
		    , "clicked", G_CALLBACK(pitivi_controller_callb_forward), self);
 
  g_signal_connect (self->private->b_ffrev[PITIVI_CONTROLLER_BUTTON_BACKWARD]\
		    , "clicked", G_CALLBACK(pitivi_controller_callb_backward), self);
}

void
connect2viewer (PitiviController *controller, GtkWidget *viewer)
{
  controller->private->viewerwin = viewer;
}

static void
pitivi_controller_dispose (GObject *object)
{
  PitiviController	*self = PITIVI_CONTROLLER(object);

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

}

static void
pitivi_controller_finalize (GObject *object)
{
  PitiviController	*self = PITIVI_CONTROLLER(object);

  /* 
   * Here, complete object destruction. 
   * You might not need to do much... 
   */
  
  g_slist_free (self->private->group_playing);
  g_slist_free (self->private->group_ffrev);
  g_free (self->private);
}

static void
pitivi_controller_set_property (GObject * object,
			      guint property_id,
			      const GValue * value, GParamSpec * pspec)
{
  PitiviController *self = (PitiviController *) object;

  switch (property_id)
    {
    case PROP_VIEWERWINDOW:
      self->private->viewerwin = g_value_get_pointer (value);
      break;
    default:
      g_assert (FALSE);
      break;
    }
}

static void
pitivi_controller_get_property (GObject * object,
			      guint property_id,
			      GValue * value, GParamSpec * pspec)
{
  PitiviController *self = (PitiviController *) object;
  
   switch (property_id)
     {
     case PROP_VIEWERWINDOW:
       g_value_set_pointer (value, self->private->viewerwin);
      break;
    default:
      g_assert (FALSE);
      break;
    }
}

static void
pitivi_controller_class_init (gpointer g_class, gpointer g_class_data)
{
  GObjectClass *gobject_class = G_OBJECT_CLASS (g_class);
  PitiviControllerClass *klass = PITIVI_CONTROLLER_CLASS (g_class);

  gobject_class->constructor = pitivi_controller_constructor;
  gobject_class->dispose = pitivi_controller_dispose;
  gobject_class->finalize = pitivi_controller_finalize;

  gobject_class->set_property = pitivi_controller_set_property;
  gobject_class->get_property = pitivi_controller_get_property;
  
  controllersignals[PAUSE_SIGNAL] = g_signal_new ("pause",
						  G_TYPE_FROM_CLASS (g_class),
						  G_SIGNAL_RUN_FIRST | G_SIGNAL_ACTION,
						  G_STRUCT_OFFSET (PitiviControllerClass, pause),
						  NULL,
						  NULL,       
						  g_cclosure_marshal_VOID__POINTER,
						  G_TYPE_NONE, 1, G_TYPE_POINTER);

  controllersignals[RECORD_SIGNAL] =
    g_signal_new("record",
		 G_TYPE_FROM_CLASS (g_class),
		 G_SIGNAL_RUN_FIRST,
		 G_STRUCT_OFFSET (PitiviControllerClass, record),
		 NULL,
		 NULL,
		 g_cclosure_marshal_VOID__VOID,
		 G_TYPE_NONE, 0);
  
  klass->pause = pitivi_controller_callb_pause;

  g_object_class_install_property (G_OBJECT_CLASS (g_class), PROP_VIEWERWINDOW,
				   g_param_spec_pointer ("viewerwin","viewerwin","viewerwin",
							 G_PARAM_WRITABLE | G_PARAM_CONSTRUCT_ONLY));
}

GType
pitivi_controller_get_type (void)
{
  static GType type = 0;
 
  if (type == 0)
    {
      static const GTypeInfo info = {
	sizeof (PitiviControllerClass),
	NULL,			/* base_init */
	NULL,			/* base_finalize */
	pitivi_controller_class_init,	/* class_init */
	NULL,			/* class_finalize */
	NULL,			/* class_data */
	sizeof (PitiviController),
	0,			/* n_preallocs */
	pitivi_controller_instance_init	/* instance_init */
      };
      type = g_type_register_static (GTK_TYPE_HBOX,
				     "PitiviControllerType", &info, 0);
    }

  return type;
}
