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

struct _PitiviViewerWindowPrivate
{
  /* instance private members */
  gboolean			dispose_has_run;
  GtkWidget			*main_vbox;
  GtkWidget		        *playerview;
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

static void
pitivi_viewerwindow_instance_init (GTypeInstance * instance, gpointer g_class)
{
  PitiviViewerWindow *self = (PitiviViewerWindow *) instance;
  GtkWidget  *separator;
  int	     count;
  
  self->private = g_new0(PitiviViewerWindowPrivate, 1);
  
  /* initialize all public and private members to reasonable default values. */ 
  
  self->private->dispose_has_run = FALSE;
  gtk_window_set_resizable (GTK_WINDOW (self), FALSE);
  
  /* If you need specific consruction properties to complete initialization, 
   * delay initialization completion until the property is set. 
   */
  
  self->private->main_vbox = gtk_vbox_new (FALSE, 0);
  gtk_widget_set_usize (self->private->main_vbox, 400, 300);
  gtk_container_add(GTK_CONTAINER(self), GTK_WIDGET(self->private->main_vbox));

  self->private->playerview = pitivi_viewerplayer_new();
  g_return_if_fail (self->private->playerview != NULL);

  self->private->logo = gdk_pixbuf_new_from_file (PITIVI_APP_LOGO_PATH, NULL);
  pitivi_viewerplayer_set_minimum_size (PITIVI_VIEWERPLAYER (self->private->playerview), 300, 300);
  pitivi_viewerplayer_set_logo (PITIVI_VIEWERPLAYER (self->private->playerview), self->private->logo);
  pitivi_viewerplayer_choose_mode_start (PITIVI_VIEWERPLAYER (self->private->playerview));
  gtk_box_pack_start (GTK_BOX (self->private->main_vbox), GTK_WIDGET(self->private->playerview), TRUE, TRUE, 0);
  
  separator = gtk_hseparator_new ();
  gtk_box_pack_start (GTK_BOX (self->private->main_vbox), GTK_WIDGET(separator), FALSE, FALSE, 0);
  
  gtk_widget_show_all (GTK_WIDGET(self));
  
  PitiviViewerController *controller = pitivi_viewercontroller_new();
  self->private->media_controller = controller;
  gtk_box_pack_start (GTK_BOX (self->private->main_vbox), GTK_WIDGET(controller), FALSE, FALSE, 0);
  
  self->private->statusbar = gtk_statusbar_new ();
  gtk_box_pack_start (GTK_BOX (self->private->main_vbox), GTK_WIDGET(self->private->statusbar), FALSE, FALSE, 0);
  gtk_widget_show (self->private->statusbar);
  
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
