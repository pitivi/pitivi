/* 
 * PiTiVi
 * Copyright (C) <2004> Edward Hervey <hervey_e@epita.fr>
 *                      Bloch Stephan <bloch_s@epita.fr>
 *                      Carbon Julien <carbon_j@epita.fr>
 *                      Dubart Loic <dubart_l@epita.fr>
 *			Guillaume Casanova <casano_g@epita.fr>
 *			Delettrez Marc <delett_m@epita.fr>
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

/* Recuperation des caps */
/*   pad_sink = gst_element_get_pad(element, "sink"); */
/*   media_setting->caps = gst_pad_get_caps(pad_sink); */
/*   g_print("Caps Sink:\n%s.\n", gst_caps_to_string (media_setting->caps)); */
/*   pad_src = gst_element_get_pad(element, "src"); */
/*   media_setting->caps = gst_pad_get_caps(pad_src); */
/*   g_print("Caps Src:\n%s.\n", gst_caps_to_string (media_setting->caps)); */
/*   media_setting->caps = gst_caps_new_simple ("my_caps", "audio/wav",  */
/* 					     NULL); */

#include <gst/gst.h>
#include "pitivi.h"
#include "pitivi-mainapp.h"
#include "pitivi-toolboxwindow.h"
#include "pitivi-newprojectwindow.h"
#include "pitivi-sourcelistwindow.h"
#include "pitivi-timelinewindow.h"
#include "pitivi-viewerwindow.h"
#include "pitivi-effectswindow.h"
#include "pitivi-projectsettings.h"
#include "pitivi-settings.h"
#include "pitivi-splashscreenwindow.h"

#define BORDER 10
#define BOTTOM2 42
#define BOTTOM 45

struct _PitiviMainAppPrivate
{
  /* instance private members */
  gboolean			dispose_has_run;
  PitiviToolboxWindow		*tbxwin;
  PitiviNewProjectWindow	*win_new_project;
  PitiviSettings		*global_settings;

  PitiviSourceListWindow	*srclistwin;
  PitiviTimelineWindow		*timelinewin;
  PitiviViewerWindow		*viewerwin;
  PitiviEffectsWindow		*effectswin;  
  PitiviSplashScreenWindow	*splash_screen;
};


/*
 * forward definitions
 */
void			pitivi_mainapp_destroy			( GtkWidget *pWidget, gpointer pData );
void			pitivi_mainapp_add_newcategory		( PitiviMainApp *self, const gchar *cat_name);
void			pitivi_mainapp_add_settings		( PitiviMainApp *self, PitiviProjectSettings *new_setting, gint *position );
void			pitivi_mainapp_del_settings		( PitiviMainApp *self, gint *position );

/*
 * Insert "added-value" functions here
 */

/* PitiviSettings * */
/* pitivi_mainapp_get_win_new_project(PitiviMainApp *self) { */
/*   return self->private->win_new_project; */
/* } */

PitiviSettings *
pitivi_mainapp_settings(PitiviMainApp *self) {
  return self->private->global_settings;
}

PitiviToolboxWindow *
pitivi_mainapp_get_toolboxwindow(PitiviMainApp *self) {
  return self->private->tbxwin;
}

PitiviTimelineWindow *
pitivi_mainapp_get_timelinewin(PitiviMainApp *self) {
  return self->private->timelinewin;
}

PitiviViewerWindow *
pitivi_mainapp_get_viewerwin(PitiviMainApp *self) {
  return self->private->viewerwin;
}

void
pitivi_mainapp_destroy(GtkWidget *pWidget, gpointer pData)
{
  PitiviMainApp *mainapp = PITIVI_WINDOWS(pWidget)->mainapp;
  gchar	*conf;

  conf = g_strdup_printf("%s/.pitivi", g_get_home_dir());
  /* Save settings before exiting */
  if (pitivi_settings_save_to_file(mainapp->private->global_settings, conf) == FALSE)
    g_printf("Error saving configuration file");
  g_free(conf);
  gtk_main_quit();
}

void
pitivi_mainapp_callb_sourcelist (GtkWindow *win, gpointer data)
{
  PitiviMainApp *self = data;
  self->private->srclistwin = NULL;
}

void
pitivi_mainapp_callb_effects (GtkWindow *win, gpointer data)
{
  PitiviMainApp *self = data;
  self->private->effectswin = NULL;
}

void
pitivi_mainapp_callb_viewer (GtkWindow *win, gpointer data)
{
  PitiviMainApp *self = data;
  self->private->viewerwin = NULL;
}

void
pitivi_mainapp_callb_timelinewin (GtkWindow *win, gpointer data)
{
  PitiviMainApp *self = data;
  self->private->timelinewin = NULL;
}

void
pitivi_mainapp_activate_effectswindow (PitiviMainApp *self, gboolean activate)
{
  if (activate && (self->private->effectswin == NULL)) {
      self->private->effectswin = pitivi_effectswindow_new(self);
      gtk_widget_show_all (GTK_WIDGET (self->private->effectswin) );
      gtk_window_move (GTK_WINDOW (self->private->effectswin), 720, 450);
      gtk_signal_connect (GTK_OBJECT (self->private->effectswin), "destroy"\
			  , GTK_SIGNAL_FUNC (pitivi_mainapp_callb_effects), self);
  } else if (self->private->effectswin){
    gtk_widget_destroy(GTK_WIDGET (self->private->effectswin));
  }
}

void
pitivi_mainapp_create_wintools (PitiviMainApp *self, PitiviProject *project)
{
  gint width;
  gint height;
  gint tmp_w;
  gint tmp_h;
  gint tmp1_w;
  gint tmp1_h;

  width = gdk_screen_width ();
  height = gdk_screen_height ();
  
  /* Source List Window */
  
  if (self->private->srclistwin == NULL)
    {
      self->private->srclistwin = pitivi_sourcelistwindow_new(self, project);
      gtk_widget_show_all (GTK_WIDGET (self->private->srclistwin) );
      gtk_window_move (GTK_WINDOW (self->private->srclistwin), 0, 0);
      gtk_window_get_size (GTK_WINDOW (self->private->srclistwin), &tmp_w, &tmp_h);
      gtk_signal_connect (GTK_OBJECT (self->private->srclistwin), "destroy"\
			  , GTK_SIGNAL_FUNC (pitivi_mainapp_callb_sourcelist), self);
    }
  
  /* Viewer Window */

  if (self->private->viewerwin == NULL)
    {
      self->private->viewerwin = pitivi_viewerwindow_new(self, project);
      //gtk_widget_show_all (GTK_WIDGET (self->private->viewerwin) );
      gtk_window_move (GTK_WINDOW (self->private->viewerwin), (tmp_w + BORDER), 0);
      gtk_signal_connect (GTK_OBJECT (self->private->viewerwin), "destroy"\
			  , GTK_SIGNAL_FUNC (pitivi_mainapp_callb_viewer), self);
    }

  /* Effect Window */

  if (self->private->effectswin == NULL) {
    pitivi_mainapp_activate_effectswindow(self, TRUE);
    gtk_window_get_size (GTK_WINDOW (self->private->effectswin), &tmp1_w, &tmp1_h);
    gtk_window_resize (GTK_WINDOW (self->private->effectswin), tmp1_w, 420);
    gtk_window_move (GTK_WINDOW (self->private->effectswin), 
		     (width - (tmp1_w + BORDER)), 
		     (height - (420 + BORDER + BOTTOM))
		     );
  }

  /* Timeline Window */
  
  if (!GTK_IS_WIDGET (self->private->timelinewin))
    {
      self->private->timelinewin = pitivi_timelinewindow_new(self);
      gtk_widget_show_all (GTK_WIDGET (self->private->timelinewin));
      gtk_window_get_size (GTK_WINDOW (self->private->timelinewin), &tmp_w, &tmp_h);
      gtk_window_move (GTK_WINDOW (self->private->timelinewin), 0, (height - (tmp_h + BORDER + BOTTOM)));
      gtk_window_resize (GTK_WINDOW (self->private->timelinewin), (width - (tmp1_w + (2 * BORDER))), (tmp_h));
      gtk_signal_connect (GTK_OBJECT (self->private->timelinewin), "destroy"\
			  , GTK_SIGNAL_FUNC (pitivi_mainapp_callb_timelinewin), self);
    }

  gtk_window_get_size (GTK_WINDOW (self->private->tbxwin), &tmp1_w, &tmp1_h);
  gtk_window_move (GTK_WINDOW (self->private->tbxwin), 0, (height - (tmp1_h + (4 * BORDER) + tmp_h + BOTTOM2)));
}

/*
  pitivi_mainapp_add_project

  Adds a PitiviProject to the list of projects handled by the application

  Returns TRUE if it was added properly
*/

gboolean
pitivi_mainapp_add_project(PitiviMainApp *self, PitiviProject *project)
{
  if (project == NULL)
    return FALSE;

  self->projects = g_list_append(self->projects, project);
  return TRUE;
}

PitiviMainApp *
pitivi_mainapp_new (void)
{
  PitiviMainApp *mainapp;
  
  mainapp = (PitiviMainApp *) g_object_new (PITIVI_MAINAPP_TYPE, NULL);
  g_assert (mainapp != NULL);

  return mainapp;
}

static GObject *
pitivi_mainapp_constructor (GType type,
			    guint n_construct_properties,
			    GObjectConstructParam * construct_properties)
{
  PitiviMainApp	*self;
  gchar		*settingsfile;
  GObject	*obj;
  {
    /* Invoke parent constructor. */
    PitiviMainAppClass *klass;
    GObjectClass *parent_class;
    klass = PITIVI_MAINAPP_CLASS (g_type_class_peek (PITIVI_MAINAPP_TYPE));
    parent_class = G_OBJECT_CLASS (g_type_class_peek_parent (klass));
    obj = parent_class->constructor (type, n_construct_properties,
				     construct_properties);
  }

  /* do stuff. */
  self = (PitiviMainApp *) obj;

  /* Lancement du splash screen */
  self->private->splash_screen = pitivi_splashscreenwindow_new();
  usleep (10);

  /* Enregistrement des Icones */
  pitivi_splashscreenwindow_set_both (self->private->splash_screen, 
				      0.0, "Loading Register Stockicons");
  pitivi_stockicons_register ();
  pitivi_splashscreenwindow_set_both (self->private->splash_screen, 
				      0.2, "Loading Default Settings");
  /*   self->private->project_settings = pitivi_projectsettings_list_make(); */

  /* Creation des settings globaux */
  pitivi_splashscreenwindow_set_both (self->private->splash_screen, 
				      0.4, "Loading Global Settings");
  settingsfile = g_strdup_printf("%s/.pitivi", g_get_home_dir());
  if ( g_file_test(settingsfile, G_FILE_TEST_EXISTS) )
    self->private->global_settings = pitivi_settings_load_from_file(settingsfile);
  else
    self->private->global_settings = pitivi_settings_new();
  g_free(settingsfile);

  /* Creation de la toolboxwindow */
  pitivi_splashscreenwindow_set_both (self->private->splash_screen, 
				      0.6, "Loading Toolbox");
  
  self->private->tbxwin = pitivi_toolboxwindow_new(self);
  
  /* Connection des Signaux */
  pitivi_splashscreenwindow_set_both (self->private->splash_screen, 
				      0.8, "Loading Signals");
  g_signal_connect(G_OBJECT(self->private->tbxwin), "delete_event",
		   G_CALLBACK(pitivi_mainapp_destroy), NULL);
  gtk_widget_show_all (GTK_WIDGET (self->private->tbxwin));
  /* finish */
  pitivi_splashscreenwindow_set_both (self->private->splash_screen, 
  				      1.0, "Loading Finished");
  
  return obj;
}

static void
pitivi_mainapp_instance_init (GTypeInstance * instance, gpointer g_class)
{
  PitiviMainApp			*self = (PitiviMainApp *) instance;
  PitiviSourceListWindow	*sourcelist;

  self->private = g_new0 (PitiviMainAppPrivate, 1);

  /* initialize all public and private members to reasonable default values. */

  self->private->dispose_has_run = FALSE;

  /* If you need specific consruction properties to complete initialization, 
   * delay initialization completion until the property is set. 
   */
  self->projects = NULL;
}

static void
pitivi_mainapp_dispose (GObject * object)
{
  PitiviMainApp *self = PITIVI_MAINAPP (object);

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
pitivi_mainapp_finalize (GObject * object)
{
  PitiviMainApp *self = PITIVI_MAINAPP (object);

  /* 
   * Here, complete object destruction. 
   * You might not need to do much... 
   */
  
  g_object_unref (self->private->tbxwin);
  g_object_unref (self->private->win_new_project);
  g_free (self->private);
}

static void
pitivi_mainapp_set_property (GObject * object,
			     guint property_id,
			     const GValue * value, GParamSpec * pspec)
{
  PitiviMainApp *self = (PitiviMainApp *) object;

  switch (property_id)
    {
      /*   case PITIVI_MAINAPP_PROPERTY: { */
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
pitivi_mainapp_get_property (GObject * object,
			     guint property_id,
			     GValue * value, GParamSpec * pspec)
{
  PitiviMainApp *self = (PitiviMainApp *) object;

  switch (property_id)
    {
      /*  case PITIVI_MAINAPP_PROPERTY: { */
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
pitivi_mainapp_class_init (gpointer g_class, gpointer g_class_data)
{
  GObjectClass *gobject_class = G_OBJECT_CLASS (g_class);
  PitiviMainAppClass *klass = PITIVI_MAINAPP_CLASS (g_class);

  gobject_class->constructor = pitivi_mainapp_constructor;
  gobject_class->dispose = pitivi_mainapp_dispose;
  gobject_class->finalize = pitivi_mainapp_finalize;

  gobject_class->set_property = pitivi_mainapp_set_property;
  gobject_class->get_property = pitivi_mainapp_get_property;

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
pitivi_mainapp_get_type (void)
{
  static GType type = 0;

  if (type == 0)
    {
      static const GTypeInfo info = {
	sizeof (PitiviMainAppClass),
	NULL,				/* base_init */
	NULL,				/* base_finalize */
	pitivi_mainapp_class_init,	/* class_init */
	NULL,				/* class_finalize */
	NULL,				/* class_data */
	sizeof (PitiviMainApp),
	0,				/* n_preallocs */
	pitivi_mainapp_instance_init	/* instance_init */
      };
      type = g_type_register_static (G_TYPE_OBJECT,
				     "PitiviMainAppType", &info, 0);
    }

  return type;
}
