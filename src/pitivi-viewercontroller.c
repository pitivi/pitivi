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
#include "pitivi-viewercontroller.h"

enum {
  PITIVI_VIEWER_BUTTON_REWARD = 1,
  PITIVI_VIEWER_BUTTON_PAUSE,
  PITIVI_VIEWER_BUTTON_FORWARD,
};

enum {
  PITIVI_VIEWER_BUTTON_PLAY = 1,
  PITIVI_VIEWER_BUTTON_STOP,
};

struct _PitiviViewerControllerPrivate
{
  /* instance private members */
  gboolean	        dispose_has_run;
  
  GtkWidget	        *toolbar;
  
  GtkWidget	        *seeker_scale;
  GtkWidget	        *time;
  
  PitiviViewerVolume	*mixer;
  GtkWidget	        *volume;
  GtkWidget             **state_vol;
  GtkObject	        *seeker_adjust;

  GtkToolItem           *b_ffrev[5];
  GtkToolItem           *b_playing[5];
  GSList                *group_playing;
  GSList                *group_ffrev;
};

/*
 * forward definitions
 */

/*
 * Insert "added-value" functions here
 */

PitiviViewerController *
pitivi_viewercontroller_new(void)
{
  PitiviViewerController	*viewercontroller;

  viewercontroller = (PitiviViewerController *) g_object_new(PITIVI_VIEWERCONTROLLER_TYPE, NULL);
  g_assert(viewercontroller != NULL);
  return viewercontroller;
}

static GObject *
pitivi_viewercontroller_constructor (GType type,
			     guint n_construct_properties,
			     GObjectConstructParam * construct_properties)
{
  GObject *obj;
  {
    /* Invoke parent constructor. */
    PitiviViewerControllerClass *klass;
    GObjectClass *parent_class;
    klass = PITIVI_VIEWERCONTROLLER_CLASS (g_type_class_peek (PITIVI_VIEWERCONTROLLER_TYPE));
    parent_class = G_OBJECT_CLASS (g_type_class_peek_parent (klass));
    obj = parent_class->constructor (type, n_construct_properties,
				     construct_properties);
  }

  /* do stuff. */

  return obj;
}

gboolean
pitivi_viewercontroller_seek_started_handler (GtkWidget       *widget,
					     GdkEventButton   *event,
					     gpointer         user_data)
{

  return FALSE;
}


gboolean
pitivi_viewercontroller_seek_changed_handler (GtkWidget       *widget,
					      GdkEventButton  *event,
					      gpointer         user_data)
{
  
  return FALSE;
}

static void
pitivi_viewercontroller_callb_stop (GtkWidget *widget, gpointer user_data)
{
  PitiviViewerController *self = (PitiviViewerController *) user_data;

  if (!gtk_toggle_tool_button_get_active (GTK_TOGGLE_TOOL_BUTTON (self->private->b_ffrev[0])))
    gtk_toggle_tool_button_set_active (GTK_TOGGLE_TOOL_BUTTON (self->private->b_ffrev[0]), TRUE);
  if (!gtk_toggle_tool_button_get_active (GTK_TOGGLE_TOOL_BUTTON (self->private->b_playing[0])))
    gtk_toggle_tool_button_set_active (GTK_TOGGLE_TOOL_BUTTON (self->private->b_playing[0]), TRUE);
}

static void
pitivi_viewercontroller_instance_init (GTypeInstance * instance, gpointer g_class)
{
  PitiviViewerController *self = (PitiviViewerController *) instance;
  GtkWidget  *separators[3];
  int	     count;

  self->private = g_new0(PitiviViewerControllerPrivate, 1);
  
  /* initialize all public and private members to reasonable default values. */ 
  
  self->private->dispose_has_run = FALSE;
  
  /* If you need specific consruction properties to complete initialization, 
   * delay initialization completion until the property is set. 
   */
  
  /* Gestion des bouttons de controle */
  
  self->private->toolbar = gtk_toolbar_new();   
  self->private->group_ffrev = g_new(GSList, 1);
  self->private->group_playing = g_new(GSList, 1);

  /* Creation Avance/Rembobinage Rapide Pause */
  
  self->private->b_ffrev[0] = gtk_radio_tool_button_new (NULL);
  self->private->group_ffrev = gtk_radio_tool_button_get_group (GTK_RADIO_TOOL_BUTTON (self->private->b_ffrev[0]));
    
  self->private->b_ffrev[PITIVI_VIEWER_BUTTON_FORWARD] = \
    gtk_radio_tool_button_new_from_stock (self->private->group_ffrev, PITIVI_STOCK_VIEWER_NEXT);
  self->private->group_ffrev = \
    gtk_radio_tool_button_get_group (GTK_RADIO_TOOL_BUTTON (self->private->b_ffrev[PITIVI_VIEWER_BUTTON_FORWARD]));
    
  self->private->b_ffrev[PITIVI_VIEWER_BUTTON_PAUSE] = \
    gtk_radio_tool_button_new_from_stock (self->private->group_ffrev, PITIVI_STOCK_VIEWER_PAUSE);
  self->private->group_ffrev = gtk_radio_tool_button_get_group (GTK_RADIO_TOOL_BUTTON (self->private->b_ffrev[PITIVI_VIEWER_BUTTON_PAUSE]));
  
  self->private->b_ffrev[PITIVI_VIEWER_BUTTON_REWARD] = \
    gtk_radio_tool_button_new_from_stock (self->private->group_ffrev, PITIVI_STOCK_VIEWER_PREVIOUS);
  self->private->group_ffrev = \
    gtk_radio_tool_button_get_group (GTK_RADIO_TOOL_BUTTON (self->private->b_ffrev[PITIVI_VIEWER_BUTTON_REWARD]));
    
  /* Creation boutton Stop */

  self->private->b_playing[0] = \
    gtk_radio_tool_button_new (NULL);
  self->private->group_playing = \
    gtk_radio_tool_button_get_group GTK_RADIO_TOOL_BUTTON ((self->private->b_playing[0]));
  
  self->private->b_playing[PITIVI_VIEWER_BUTTON_PLAY] \
    = gtk_radio_tool_button_new_from_stock (self->private->group_playing, PITIVI_STOCK_VIEWER_PLAY);
  self->private->group_playing = \
    gtk_radio_tool_button_get_group (GTK_RADIO_TOOL_BUTTON (self->private->b_playing[PITIVI_VIEWER_BUTTON_PLAY]));
  
  self->private->b_playing[PITIVI_VIEWER_BUTTON_STOP] = gtk_tool_button_new_from_stock (PITIVI_STOCK_VIEWER_STOP);
  g_signal_connect (self->private->b_playing[PITIVI_VIEWER_BUTTON_STOP]\
		    , "clicked", G_CALLBACK(pitivi_viewercontroller_callb_stop), self);
  
  gtk_toolbar_insert (GTK_TOOLBAR(self->private->toolbar)\
		      , GTK_TOOL_ITEM (self->private->b_ffrev[PITIVI_VIEWER_BUTTON_REWARD]), -1);
  gtk_toolbar_insert (GTK_TOOLBAR(self->private->toolbar)\
		      , GTK_TOOL_ITEM (self->private->b_playing[PITIVI_VIEWER_BUTTON_PLAY]), -1);
  gtk_toolbar_insert (GTK_TOOLBAR(self->private->toolbar)\
		      , GTK_TOOL_ITEM (self->private->b_ffrev[PITIVI_VIEWER_BUTTON_PAUSE]), -1);
  gtk_toolbar_insert (GTK_TOOLBAR(self->private->toolbar)\
		      , GTK_TOOL_ITEM (self->private->b_ffrev[PITIVI_VIEWER_BUTTON_FORWARD]), -1);  
  gtk_toolbar_insert (GTK_TOOLBAR(self->private->toolbar)\
		      , GTK_TOOL_ITEM (self->private->b_playing[PITIVI_VIEWER_BUTTON_STOP]), -1);
  
  gtk_toolbar_set_orientation (GTK_TOOLBAR(self->private->toolbar), GTK_ORIENTATION_HORIZONTAL);
  gtk_toolbar_set_show_arrow (GTK_TOOLBAR(self->private->toolbar), FALSE);
  gtk_toolbar_set_style (GTK_TOOLBAR(self->private->toolbar), GTK_TOOLBAR_ICONS);
  gtk_toolbar_set_icon_size (GTK_TOOLBAR (self->private->toolbar), GTK_ICON_SIZE_SMALL_TOOLBAR);

  gtk_box_pack_start (GTK_BOX (self), self->private->toolbar, TRUE, TRUE, 0);
  
  /* Creation du seeker */
  
  self->private->seeker_adjust = gtk_adjustment_new (0, 0, 0, 0, 0, 0);
  self->private->seeker_scale =  gtk_hscale_new (GTK_ADJUSTMENT(self->private->seeker_adjust));
  gtk_widget_set_size_request (self->private->seeker_scale, 150, -1);
  gtk_widget_set_sensitive ( self->private->seeker_scale, FALSE);
  gtk_scale_set_draw_value (GTK_SCALE ( self->private->seeker_scale ), FALSE);
  gtk_scale_set_digits (GTK_SCALE ( self->private->seeker_scale ), 0);
  
  self->private->time = gtk_label_new ("00:00");
  gtk_label_set_use_markup (GTK_LABEL (self->private->time), TRUE);
  gtk_label_set_justify (GTK_LABEL (self->private->time), GTK_JUSTIFY_LEFT);
  gtk_misc_set_alignment (GTK_MISC (self->private->time), 1, 0.5);  
    
  separators[0] = gtk_vseparator_new ();
  gtk_box_pack_start (GTK_BOX (self), separators[0], TRUE, TRUE, 5);
        
  gtk_box_pack_start (GTK_BOX (self), self->private->time, TRUE, TRUE, 0);
  gtk_box_pack_start (GTK_BOX (self), GTK_WIDGET(self->private->seeker_scale), TRUE, TRUE, 5);
  
  separators[1] = gtk_vseparator_new ();
  gtk_box_pack_start (GTK_BOX (self), separators[1], TRUE, TRUE, 5);
  
  self->private->volume = gtk_toggle_button_new ();
  gtk_box_pack_start (GTK_BOX (self), self->private->volume, TRUE, TRUE, 5);
  
  GtkWidget *hbox_volume = gtk_hbox_new (FALSE, 0);
  
  gtk_widget_show_all (GTK_WIDGET(self));
  
  /* Creation du volume */

  self->private->mixer = pitivi_viewervolume_new ();
  self->private->state_vol = self->private->mixer->public->state_vol;
  for (count = 0; count < PITIVI_STATE_VOLIMG_ALL; count++)
    {
      gtk_box_pack_start (GTK_BOX (hbox_volume), self->private->state_vol[count], TRUE, TRUE, 0);
      if (count != PITIVI_STATE_VOLIMG_ALL - 1)
	gtk_widget_hide (self->private->state_vol[count]);
      else
	{
	  gtk_widget_show (hbox_volume);
	  gtk_widget_show (self->private->state_vol[count]);
	}
    }
  
  gtk_container_add (GTK_CONTAINER (self->private->volume), hbox_volume);    
  
  g_signal_connect ((gpointer) self->private->volume, "button-release-event",
		    G_CALLBACK (pitivi_viewervolume_cb_button_released),
		    self->private->mixer);
  
  g_signal_connect ((gpointer) self->private->volume, "toggled",
		    G_CALLBACK (pitivi_viewervolume_cb_button_clicked),
		    self->private->mixer);
}

static void
pitivi_viewercontroller_dispose (GObject *object)
{
  PitiviViewerController	*self = PITIVI_VIEWERCONTROLLER(object);

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
pitivi_viewercontroller_finalize (GObject *object)
{
  PitiviViewerController	*self = PITIVI_VIEWERCONTROLLER(object);

  /* 
   * Here, complete object destruction. 
   * You might not need to do much... 
   */

  g_free (self->private);
}

static void
pitivi_viewercontroller_set_property (GObject * object,
			      guint property_id,
			      const GValue * value, GParamSpec * pspec)
{
  PitiviViewerController *self = (PitiviViewerController *) object;

  switch (property_id)
    {
      /*   case PITIVI_VIEWERCONTROLLER_PROPERTY: { */
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
pitivi_viewercontroller_get_property (GObject * object,
			      guint property_id,
			      GValue * value, GParamSpec * pspec)
{
  PitiviViewerController *self = (PitiviViewerController *) object;

  switch (property_id)
    {
      /*  case PITIVI_VIEWERCONTROLLER_PROPERTY: { */
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
pitivi_viewercontroller_class_init (gpointer g_class, gpointer g_class_data)
{
  GObjectClass *gobject_class = G_OBJECT_CLASS (g_class);
  PitiviViewerControllerClass *klass = PITIVI_VIEWERCONTROLLER_CLASS (g_class);

  gobject_class->constructor = pitivi_viewercontroller_constructor;
  gobject_class->dispose = pitivi_viewercontroller_dispose;
  gobject_class->finalize = pitivi_viewercontroller_finalize;

  gobject_class->set_property = pitivi_viewercontroller_set_property;
  gobject_class->get_property = pitivi_viewercontroller_get_property;

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
pitivi_viewercontroller_get_type (void)
{
  static GType type = 0;
 
  if (type == 0)
    {
      static const GTypeInfo info = {
	sizeof (PitiviViewerControllerClass),
	NULL,			/* base_init */
	NULL,			/* base_finalize */
	pitivi_viewercontroller_class_init,	/* class_init */
	NULL,			/* class_finalize */
	NULL,			/* class_data */
	sizeof (PitiviViewerController),
	0,			/* n_preallocs */
	pitivi_viewercontroller_instance_init	/* instance_init */
      };
      type = g_type_register_static (GTK_TYPE_HBOX,
				     "PitiviViewerControllerType", &info, 0);
    }

  return type;
}
