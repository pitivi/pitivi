/* 
 * PiTiVi
 * Copyright (C) <2004> Delettrez Marc <delett_m@epita.fr>
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
#include "pitivi-splashscreenwindow.h"

static     GtkWindowClass *parent_class;


struct _PitiviSplashScreenWindowPrivate
{
  /* instance private members */
  gboolean	dispose_has_run;
  gboolean	time_out;

  GtkWidget	*main_vbox;
  GtkWidget	*img;
  GtkWidget	*label;
  GtkWidget	*bar;
};

/*
 * forward definitions
 */

static gboolean progress_timeout( gpointer data )
{
  PitiviSplashScreenWindow *self = (PitiviSplashScreenWindow *) data;
  gdouble	new_val;

  new_val = gtk_progress_bar_get_fraction (GTK_PROGRESS_BAR (self->private->bar));
  self->private->time_out = TRUE;
  if (new_val == 1.0) {
    //g_print ("coucou_3\n");
    gtk_widget_destroy (GTK_WIDGET (self));
  }
  return FALSE;
} 

/*
 * methodes definitions
 */

void
pitivi_splashscreenwindow_set_both (PitiviSplashScreenWindow *self, gdouble per, gchar *label)
{
  pitivi_splashscreenwindow_set_fraction (self, per);
  pitivi_splashscreenwindow_set_label (self, label);
  return ;
}

void
pitivi_splashscreenwindow_set_fraction (PitiviSplashScreenWindow *self, gdouble per)
{
  gchar		*text;

  if ((per  != 1.0)  || (!self->private->time_out)) {
    //g_print ("coucou_1\n");
    text = g_strdup_printf("%g %%", per*100);
    gtk_progress_bar_set_text (GTK_PROGRESS_BAR (self->private->bar), text);
    //gtk_progress_set_percentage (GTK_PROGRESS (self->private->bar), per);
    gtk_progress_bar_set_fraction (GTK_PROGRESS_BAR (self->private->bar), per);
    g_free (text);
  } else {
    //g_print ("coucou_2\n");
    gtk_widget_destroy (GTK_WIDGET (self));
  }
  return ;
}

void
pitivi_splashscreenwindow_set_label (PitiviSplashScreenWindow *self, gchar *label)
{
  gtk_label_set_text (GTK_LABEL (self->private->label), label);
  return ;
}

/*
 * Insert "added-value" functions here
 */

PitiviSplashScreenWindow *
pitivi_splashscreenwindow_new(void)
{
  PitiviSplashScreenWindow	*splashscreenwindow;

  splashscreenwindow = (PitiviSplashScreenWindow *) g_object_new(PITIVI_SPLASHSCREENWINDOW_TYPE, NULL);
  g_assert(splashscreenwindow != NULL);
  return splashscreenwindow;
}

static GObject *
pitivi_splashscreenwindow_constructor (GType type,
			     guint n_construct_properties,
			     GObjectConstructParam * construct_properties)
{
  PitiviSplashScreenWindow *self;
  GObject *obj;
  gint x;
  gint y;

  /* Invoke parent constructor. */
  obj = G_OBJECT_CLASS (parent_class)->constructor (type, n_construct_properties,
				   construct_properties);

  /* do stuff. */
  self = (PitiviSplashScreenWindow *) obj;

  gtk_window_set_decorated (GTK_WINDOW (self), FALSE);
  //gtk_window_set_default_size (GTK_WINDOW(self), 200, 200);
  x = (gdk_screen_width () / 2);
  y = (gdk_screen_height () / 3);
  gtk_window_move (GTK_WINDOW (self), x,  y);
  //gtk_window_set_resizable (GTK_WINDOW (self), FALSE);
  //gtk_window_set_keep_above (GTK_WINDOW (self), FALSE);

  // main container box
  self->private->main_vbox = gtk_vbox_new (FALSE, 3);
  gtk_container_add (GTK_CONTAINER (self), self->private->main_vbox);
  gtk_widget_show (self->private->main_vbox);

  // Img
  self->private->img = gtk_image_new_from_file ("../pixmaps/logo-pitivi.png");
  gtk_container_add (GTK_CONTAINER (self->private->main_vbox), self->private->img);
  gtk_widget_show (self->private->img);

  // Label
  self->private->label = gtk_label_new ("Pitivi Loading ......");
  gtk_container_add (GTK_CONTAINER (self->private->main_vbox), self->private->label);
  gtk_widget_show (self->private->label);

  // Bar loading
  self->private->bar = gtk_progress_bar_new ();
  gtk_progress_bar_set_orientation (GTK_PROGRESS_BAR (self->private->bar), GTK_PROGRESS_LEFT_TO_RIGHT);
  pitivi_splashscreenwindow_set_fraction (self, 0.0);
  //gtk_progress_bar_set_fraction (GTK_PROGRESS_BAR (self->private->bar), 0.0);
  //gtk_progress_bar_set_text (GTK_PROGRESS_BAR (self->private->bar), "0 %");
  gtk_container_add (GTK_CONTAINER (self->private->main_vbox), self->private->bar);
  gtk_widget_show (self->private->bar);

  gtk_widget_show (GTK_WIDGET (self));
  g_timeout_add (2000, progress_timeout, self);
  return obj;
}

static void
pitivi_splashscreenwindow_instance_init (GTypeInstance * instance, gpointer g_class)
{
  PitiviSplashScreenWindow *self = (PitiviSplashScreenWindow *) instance;

  self->private = g_new0(PitiviSplashScreenWindowPrivate, 1);
  
  /* initialize all public and private members to reasonable default values. */ 
  
  self->private->dispose_has_run = FALSE;

  self->private->time_out = FALSE;

  /* Do only initialisation here */
  /* The construction of the object should be done in the Constructor
     So that properties set at instanciation can be set */
}

static void
pitivi_splashscreenwindow_dispose (GObject *object)
{
  PitiviSplashScreenWindow	*self = PITIVI_SPLASHSCREENWINDOW(object);

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
pitivi_splashscreenwindow_finalize (GObject *object)
{
  PitiviSplashScreenWindow	*self = PITIVI_SPLASHSCREENWINDOW(object);

  /* 
   * Here, complete object destruction. 
   * You might not need to do much... 
   */

  g_free (self->private);
  G_OBJECT_CLASS (parent_class)->finalize (object);
}

static void
pitivi_splashscreenwindow_set_property (GObject * object,
			      guint property_id,
			      const GValue * value, GParamSpec * pspec)
{
/*   PitiviSplashScreenWindow *self = (PitiviSplashScreenWindow *) object; */

  switch (property_id)
    {
      /*   case PITIVI_SPLASHSCREENWINDOW_PROPERTY: { */
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
pitivi_splashscreenwindow_get_property (GObject * object,
			      guint property_id,
			      GValue * value, GParamSpec * pspec)
{
/*   PitiviSplashScreenWindow *self = (PitiviSplashScreenWindow *) object; */

  switch (property_id)
    {
      /*  case PITIVI_SPLASHSCREENWINDOW_PROPERTY: { */
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
pitivi_splashscreenwindow_class_init (gpointer g_class, gpointer g_class_data)
{
  GObjectClass *gobject_class = G_OBJECT_CLASS (g_class);
/*   PitiviSplashScreenWindowClass *klass = PITIVI_SPLASHSCREENWINDOW_CLASS (g_class); */

  parent_class = g_type_class_peek_parent (g_class);

  gobject_class->constructor = pitivi_splashscreenwindow_constructor;
  gobject_class->dispose = pitivi_splashscreenwindow_dispose;
  gobject_class->finalize = pitivi_splashscreenwindow_finalize;

  gobject_class->set_property = pitivi_splashscreenwindow_set_property;
  gobject_class->get_property = pitivi_splashscreenwindow_get_property;

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
pitivi_splashscreenwindow_get_type (void)
{
  static GType type = 0;
 
  if (type == 0)
    {
      static const GTypeInfo info = {
	sizeof (PitiviSplashScreenWindowClass),
	NULL,			/* base_init */
	NULL,			/* base_finalize */
	pitivi_splashscreenwindow_class_init,	/* class_init */
	NULL,			/* class_finalize */
	NULL,			/* class_data */
	sizeof (PitiviSplashScreenWindow),
	0,			/* n_preallocs */
	pitivi_splashscreenwindow_instance_init	/* instance_init */
      };
      type = g_type_register_static (GTK_TYPE_WINDOW,
				     "PitiviSplashScreenWindowType", &info, 0);
    }

  return type;
}
